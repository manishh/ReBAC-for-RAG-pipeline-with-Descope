# How documents are loaded in ChromaDB (RAG pipeline)?

If you'd like to understand how this demo code stores documents in the vector database (Chroma DB) along with their chunking and associated _"collection"_ (classification or categorization), read on.

## Document Loading and Chunking

ChromaDB stores vector embeddings, not full documents. That means you first need to extract text from formats like PDF, Excel, plain text, and Markdown, then load it into the vector database.

Large documents also need to be split into smaller chunks. Embedding models have token limits, and smaller chunks improve retrieval accuracy by returning more precise context. For example, embedding a 50-page report as a single vector would match poorly against specific queries. This demo uses a simple character-based chunking strategy:

```python
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
```

2000 characters per chunk (~500 tokens) balances context and precision. Larger chunks provide more context but reduce retrieval accuracy. Smaller chunks are more precise but may lack enough context. With larger chunks, retrieving fewer results (n=3 instead of n=5+) keeps relevance high and LLM token costs low.

## Loading Documents into ChromaDB

When you add documents to ChromaDB, it converts them to vectors using its default embedding model. Here's how you load all documents with their metadata:

```python
def load_documents_to_chroma() -> None:
    """Load all documents into ChromaDB with metadata"""
    collection = chroma_client.get_or_create_collection(name="enterprise_docs")
    
    # Clear existing data for clean demo runs
    try:
        chroma_client.delete_collection(name="enterprise_docs")
        collection = chroma_client.create_collection(name="enterprise_docs")
    except:
        pass
    
    documents_dir = Path("./documents")
    
    for filename, metadata in DOCUMENT_METADATA.items():
        filepath = documents_dir / filename
        if not filepath.exists():
            continue
        
        text = extract_text_from_file(filepath)
        chunks = chunk_text(text)
        
        # Each chunk gets the same metadata
        chunk_ids = [f"{metadata['doc_id']}_chunk_{i}" for i in range(len(chunks))]
        chunk_metadata = [metadata.copy() for _ in chunks]
        
        collection.add(
            documents=chunks,
            metadatas=chunk_metadata,
            ids=chunk_ids
        )
```

The `DOCUMENT_METADATA` dictionary maps filenames to metadata like `doc_id` and title (you can add more metadata as well). This metadata is stored with each chunk, so you can trace it back to the original document later. This traceability is essential for authorization checks.

---

Author: Manish Hatwalne