import json
import os
from pathlib import Path
from typing import List, Dict, Set
import chromadb
from descope import DescopeClient, AuthException
from openai import OpenAI
from dotenv import load_dotenv
import PyPDF2
import openpyxl

# Load environment variables
load_dotenv()

# Initialize clients
chroma_client = chromadb.PersistentClient(path="./chroma_db")
descope_client = DescopeClient(
    project_id=os.getenv("DESCOPE_PROJECT_ID"),
    management_key=os.getenv("DESCOPE_MANAGEMENT_KEY")
)
# Feel free to use any other LLM with a suitable model
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm_model = "gpt-4o-mini"

# Document metadata mapping
DOCUMENT_METADATA: Dict[str, Dict[str, str]] = {
    "team_notes.txt": {
        "doc_id": "team_notes_001",
        "title": "Team A Sprint 23 Notes",
    },
    "board_minutes.pdf": {
        "doc_id": "board_minutes_001",
        "title": "Board of Directors Meeting Minutes",
    },
    "quarterly_report.pdf": {
        "doc_id": "quarterly_report_q4_2025",
        "title": "Q4 2025 Quarterly Financial Report",
    },
    "eng_specs.md": {
        "doc_id": "eng_specs_auth_001",
        "title": "API Authentication Service - Technical Specifications",
    },
    "hr_handbook.pdf": {
        "doc_id": "hr_handbook_2026",
        "title": "Employee Handbook 2026",
    },
    "salary_data.xlsx": {
        "doc_id": "salary_data_2026",
        "title": "2026 Employee Compensation Data",
    }
}

def extract_text_from_file(filepath: Path) -> str:
    """Extract text from different file types"""
    file_ext = filepath.suffix.lower()
    
    if file_ext == '.txt' or file_ext == '.md':
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    elif file_ext == '.pdf':
        text = ""
        with open(filepath, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    elif file_ext == '.xlsx':
        wb = openpyxl.load_workbook(filepath)
        text = ""
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = " ".join([str(cell) for cell in row if cell is not None])
                text += row_text + "\n"
        return text
    
    return ""

def chunk_text(text: str, chunk_size: int = 2000) -> List[str]:
    """Simple text chunking by character count"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        if current_length > chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def load_documents_to_chroma() -> None:
    """Load all documents into ChromaDB with metadata"""

    os.makedirs("chroma_db", exist_ok=True) # Create directory if it doesn't exist
    collection = chroma_client.get_or_create_collection(name="enterprise_docs") 
    
    # Clear existing data (for demo purposes)
    try:
        chroma_client.delete_collection(name="enterprise_docs")
        collection = chroma_client.create_collection(name="enterprise_docs")
    except:
        pass
    
    documents_dir = Path("./documents")
    
    for filename, metadata in DOCUMENT_METADATA.items():
        filepath = documents_dir / filename
        if not filepath.exists():
            print(f"Warning: {filename} not found, skipping...")
            continue
        
        print(f"Loading {filename}...")
        text = extract_text_from_file(filepath)
        chunks = chunk_text(text)
        
        # Prepare data for ChromaDB
        chunk_ids = [f"{metadata['doc_id']}_chunk_{i}" for i in range(len(chunks))]
        chunk_metadata = [metadata.copy() for _ in chunks]
        
        # Add to collection
        collection.add(
            documents=chunks,
            metadatas=chunk_metadata,
            ids=chunk_ids
        )
        
        print(f"  Added {len(chunks)} chunks from {filename}")
    
    print(f"\nTotal documents in collection: {collection.count()}")

def query_rag(question: str, user_email: str) -> str:
    """
    Query the RAG pipeline (UNSECURED - no filtering)
    
    Args:
        question: User's question
        user_email: User identifier
    
    Returns:
        Generated answer from the LLM
    """
    collection = chroma_client.get_collection(name="enterprise_docs")
    
    # Retrieve relevant chunks (NO FILTERING - this is the unsecured baseline)
    results = collection.query(
        query_texts=[question],
        n_results=5
    )
    
    # Extract retrieved documents
    # print(f"-------->>>RAG Search Results: {json.dumps(results, indent=4)}")
    retrieved_docs = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    
    print(f"\n{'_'*80}")
    print(f"Question: {question}")
    print(f"User: {user_email or 'Anonymous'}")
    # print(f"{'_'*80}")
    # print(f"\nRetrieved {len(retrieved_docs)} chunks from:")
    # for meta in retrieved_metadata:
    #     print(f"  - {meta['title']} (Access Level: {meta['access_level']})")
    
    # Combine retrieved chunks into context
    context = "\n\n".join(retrieved_docs)
    
    # Generate answer using OpenAI LLM
    response = llm_client.chat.completions.create(
        model=llm_model,
        messages=[
            {
                "role": "system",
                "content": f"""You are a helpful assistant that answers questions based on the provided context. 
Only use information from the context to answer. If the context doesn't contain relevant information, say so.

Context:
{context}"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        temperature=0.7,
        max_tokens=750
    )
    
    answer = response.choices[0].message.content
    
    # print(f"\nAnswer:\n{answer}")
    # print(f"\n{'_' * 80}\n")
    
    return answer

def check_document_access(user_email: str, doc_ids: List[str]) -> Set[str]:
    """
    Check which documents the user can access using Descope ReBAC
    
    Args:
        user_email: User's email address
        doc_ids: List of document IDs to check
    
    Returns:
        Set of document IDs the user is authorized to view
    """
    if not doc_ids:
        return set()
    
    # Prepare batch check for all documents
    relations_to_check = [
        {
            "resource": doc_id,
            "resourceType": "doc",
            "relation": "can_view",
            "target": user_email,
            "targetType": "user"
        }
        for doc_id in doc_ids
    ]
    
    try:
        # Batch check all permissions
        check_results = descope_client.mgmt.fga.check(relations_to_check)
        
        # Filter to only authorized document IDs
        authorized_docs = {
            doc_ids[i] for i, result in enumerate(check_results)
            if result.get("allowed", False)
        }
        
        return authorized_docs
    except Exception as e:
        print(f"Error checking document permissions: {e}")
        return set()

def query_rag_secured(question: str, user_email: str) -> str:
    """
    Query the RAG pipeline WITH ReBAC authorization
    
    Args:
        question: User's question
        user_email: User identifier for authorization check
    
    Returns:
        Generated answer from the LLM (or access denied message)
    """
    collection = chroma_client.get_collection(name="enterprise_docs")
    
    # Step 1: Retrieve relevant chunks (NO FILTERING YET)
    results = collection.query(
        query_texts=[question],
        n_results=3
    )
    
    retrieved_docs = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    
    print(f"\n{'_' * 80}")
    print(f"Question: {question}")
    print(f"User: {user_email}")
    # print(f"{'_' * 80}")
    # print(f"\nRetrieved {len(retrieved_docs)} chunks from ChromaDB:")
    # for meta in retrieved_metadata:
    #     print(f"  - {meta['title']} (doc_id: {meta['doc_id']})")
    
    # Step 2: Extract unique document IDs
    doc_ids = list(set(meta['doc_id'] for meta in retrieved_metadata))
    
    # Step 3: Check authorization with Descope
    print(f"\nChecking authorization with Descope...")
    authorized_doc_ids = check_document_access(user_email, doc_ids)
    
    print(f"Authorized documents: {len(authorized_doc_ids)}/{len(doc_ids)}")
    for doc_id in authorized_doc_ids:
        doc_title = next((m['title'] for m in retrieved_metadata if m['doc_id'] == doc_id), doc_id)
        print(f"  ✓ {doc_title}")
    
    # Step 4: Filter chunks to only authorized documents
    filtered_chunks = [
        chunk for chunk, meta in zip(retrieved_docs, retrieved_metadata)
        if meta['doc_id'] in authorized_doc_ids
    ]
    
    # Step 5: Handle insufficient access (even single chunk might suffice for the answer)
    if len(filtered_chunks) == 0:
        # print(f"\n❌ Access Denied: Insufficient authorized content to answer this question.")
        # print(f"{'_' * 80}\n")
        return "❌ I don't have access to sufficient information to answer this question. You may not have permission to view the relevant documents."
    
    # Step 6: Generate answer using authorized chunks only
    context = "\n\n".join(filtered_chunks)
    
    response = llm_client.chat.completions.create(
        model=llm_model,
        messages=[
            {
                "role": "system",
                "content": f"""You are a helpful assistant that answers questions based on the provided context. 
Only use information from the context to answer. If the context doesn't contain relevant information, say so.

Context:
{context}"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    answer = response.choices[0].message.content
    
    # print(f"\nAnswer:\n{answer}")
    # print(f"\n{'_' * 80}\n")
    
    return answer


def test_unsecured_rag_pipeline() -> None:    
    # Test 1: Regular employee asking about team projects
    answer = query_rag(
        "What are the current team projects and their progress?",
        user_email="alice@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")
    
    # Test 2: Regular employee asking about executive compensation
    answer = query_rag(
        "What is the CEO's total compensation?",
        user_email="john@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")
    
    # Test 3: Asking about quarterly performance
    answer = query_rag(
        "What were the company's Q4 2025 financial results?",
        user_email="jane@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")
    
    print("\n⚠️  SECURITY ISSUE: All users can access ALL documents!")

def test_secured_rag_pipeline() -> None:
    # Test 1: Alice (Team A member) asking about team projects
    print("\n--- Test 1: Alice (engineer) asks about team projects ---")
    answer = query_rag_secured(
        "What are the current team projects and their progress?",
        user_email="alice@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")
    
    # Test 2: John (regular employee) trying to access salary data
    print("\n--- Test 2: John (regular employee) asks about CEO salary ---")
    answer = query_rag_secured(
        "What is the CEO's total compensation?",
        user_email="john@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")
    
    # Test 3: Sarah (CEO) asking about financials
    print("\n--- Test 3: Sarah (CEO) asks about Q4 financials ---")
    answer = query_rag_secured(
        "What were the company's Q4 2025 financial results?",
        user_email="sarah@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")
    
    # Test 4: Everyone can access HR handbook
    print("\n--- Test 4: John asks about HR policies ---")
    answer = query_rag_secured(
        "What is the company's remote work policy?",
        user_email="john@company.com"
    )
    print(f"\nAnswer:\n{answer}")
    print(f"{'_' * 80}\n")

    print("\n✅ Security enforced: Users only see documents they're authorized to access!")    
  

def run_selected_tests() -> None:
    print("="*80)
    print("RAG Pipeline with Descope ReBAC Demo")
    print("="*80)

    print("\nWhat would you like to run?\n")
    print("1. Unsecured RAG Pipeline (shows the security problem)")
    print("2. Secured RAG Pipeline with Descope (shows the solution)")
    print("3. Both (side-by-side comparison)")
    print("4. Exit")
    print()

    while True:
        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            # Test Unsecured Pipeline
            print("=" * 80)
            print("Testing UNSECURED RAG Pipeline...")
            print("=" * 80)            
            test_unsecured_rag_pipeline()
            print("\n\n")
            break
        if choice == "2":            
            # Test Secured Pipeline
            print("=" * 80)
            print("Running SECURED RAG Pipeline with Descope...")
            print("=" * 80)       
            test_secured_rag_pipeline()
            print("\n\n")
            break            
        elif choice == "3":
            # Test BOTH Pipelines
            print("Running BOTH Pipelines for Comparison...")
            
            # Test Unsecured Pipeline
            print("=" * 80)
            print("\n### PART 1: UNSECURED BASELINE ###\n")
            print("=" * 80)
            test_unsecured_rag_pipeline()
            print("\n\n")
    
            # Test Secured Pipeline
            print("=" * 80)
            print("### PART 2: SECURED WITH DESCOPE ###")
            print("=" * 80)       
            test_secured_rag_pipeline()
            print("\n\n")
            break                        
        elif choice == "4":
            print("\nExiting...")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.\n")


# Main execution
if __name__ == "__main__":   

    print("*" * 80)
    print("\tRAG Pipeline Demo - With & Without Descope ReBAC")
    print("*" * 80)
    
    # Load documents (comment out after first run to avoid re-loading)
    print("\nLoading documents into ChromaDB...")
    load_documents_to_chroma()
    print("\n\n")

    # Run selected RAG tests
    run_selected_tests()



    

    
    
