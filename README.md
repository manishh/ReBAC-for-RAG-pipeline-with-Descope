# Securing RAG Pipelines with Descope ReBAC

This demo shows how to add Relationship-Based Access Control (ReBAC) to a Retrieval-Augmented Generation (RAG) pipeline using Descope's Fine-Grained Authorization (FGA).

## 📋 Overview

The demo consists of two main components:

1. **Descope Setup** (`setup_descope.py`) - Configures ReBAC schema and relationships
2. **RAG Pipeline** (`rag_pipeline.py`) - Demonstrates both unsecured and secured approaches.

    > How documents are loaded in ChromaDB (RAG pipeline)?
    > Read [here](./document-loading-in-ChromaDB.md).

## 🎯 What You'll Learn

- How to integrate Descope ReBAC with a RAG pipeline
- Post-retrieval filtering based on relationship-based permissions
- The difference between unsecured and secured RAG pipelines
- How to implement team-based, ownership, and shared document access

## 📁 Project Structure
```
project/
├── documents/              # Sample enterprise documents
│   ├── team_notes.txt
│   ├── board_minutes.pdf
│   ├── quarterly_report.pdf
│   ├── eng_specs.md
│   ├── hr_handbook.pdf
│   └── salary_data.xlsx
├── chroma_db/             # ChromaDB persistent storage (auto-created)
├── rag_pipeline.py        # Main demo (unsecured + secured)
├── setup_descope.py       # Descope ReBAC configuration
├── requirements.txt       # Python dependencies
├── .env                   # API keys (create from .env.example)
└── README.md              # This file
```

## 🚀 Setup Instructions

### Step 1: Prerequisites

- Python 3.10 or higher
- OpenAI API key ([get one here](https://platform.openai.com/api-keys) - Paid)
- Descope account ([sign up for a free trial](https://www.descope.com/))

### Step 2: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Clone the Repository
```bash
git clone https://github.com/manishh/ReBAC-for-RAG-pipeline-with-Descope
cd ReBAC-for-RAG-pipeline-with-Descope
```  

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

Rename `.env.example` file as `.env` file and add your credentials there:
```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Descope Credentials
DESCOPE_PROJECT_ID=your_descope_project_id
DESCOPE_MANAGEMENT_KEY=your_descope_management_key
```

**How to get Descope credentials:**
1. Go to [Descope Console](https://app.descope.com/)
2. Create a new project or select existing one
3. Project ID: Found in Project Settings
4. Management Key: Go to Settings → Company → Generate [Management Key](https://app.descope.com/settings/company/managementkeys) (allow project level access with `"Full Access"` role). 

## 📝 Running the Demo

### Step 1: Set Up Descope ReBAC

First, configure the authorization schema and relationships:
```bash
python setup_descope.py
```

**What happens:**
1. Creates 5 test users (Alice, Sarah, John, Jane, Mike)
2. Defines ReBAC schema with types: `user`, `Team`, `doc`
3. Establishes relationships:
   - User memberships (Alice → Team A, Sarah → Executive, etc.)
   - Document ownership (Alice owns team_notes, etc.)
   - Team access (Executive team can access salary_data, etc.)
4. Runs permission tests to verify setup

**Expected output:**
```
============================================================
Descope ReBAC Setup for RAG Pipeline
============================================================
Creating users...
  ✓ Created user: alice@company.com
  ✓ Created user: sarah@company.com
  ...

Defining ReBAC schema...
  ✓ Schema defined successfully

Creating relationships...
  ✓ Created 24 relations successfully

Testing Authorization Checks
============================================================
✓ alice@company.com can_view team_notes_001: True (expected: True)
✓ alice@company.com can_view board_minutes_001: False (expected: False)
✓ sarah@company.com can_view salary_data_2026: True (expected: True)
...

Setup Complete!
```

**Verify in Descope Console:**
1. Go to [Authorization → FGA](https://app.descope.com/authorization/fga)
2. Check "Relations" tab
3. You should see all user-team-document relationships

### Step 2: Run the RAG Pipeline Demo

Launch the interactive demo:
```bash
python rag_pipeline.py
```

**Interactive Menu:**
```
============================================================
RAG Pipeline with Descope ReBAC Demo
============================================================

What would you like to run?

1. Unsecured RAG Pipeline (shows the security problem)
2. Secured RAG Pipeline with Descope (shows the solution)
3. Both (side-by-side comparison)
4. Exit

Enter your choice (1-4):
```

### Option 1: Unsecured RAG Pipeline

**What it demonstrates:**
- Loads documents into ChromaDB
- Runs queries WITHOUT authorization checks
- Shows how any user can access any document ⚠️

**Example output:**
```
--- Test: John (regular employee) asks about CEO salary ---

Question: What is the CEO's total compensation?
User: john@company.com

Answer: The CEO's total compensation is $500,000...

⚠️  SECURITY ISSUE: Regular employee accessed executive salary data!
```

### Option 2: Secured RAG Pipeline

**What it demonstrates:**
- Same queries but WITH Descope authorization
- Post-retrieval filtering based on ReBAC
- Shows access granted/denied based on relationships

**Example output:**
```
--- Test: John (regular employee) asks about CEO salary ---

Question: What is the CEO's total compensation?
User: john@company.com

Checking authorization with Descope...
Authorized documents: 0/1

❌ I don't have access to sufficient information to answer this question.

✅ Authorization enforced successfully!
```

### Option 3: Both (Recommended for First Run)

Runs both pipelines sequentially to show the contrast:
1. First shows the unsecured baseline (the problem)
2. Then shows the secured version with Descope (the solution)

Perfect for understanding the before/after comparison.

## 👥 Test Users & Permissions

| User | Email | Teams | Can Access |
|------|-------|-------|------------|
| Alice | alice@company.com | Team A, Engineering, All Employees | team_notes, eng_specs, hr_handbook |
| Sarah | sarah@company.com | Executive, All Employees | board_minutes, quarterly_report, salary_data, hr_handbook |
| John | john@company.com | All Employees | hr_handbook only |
| Jane | jane@company.com | Finance, All Employees | quarterly_report, hr_handbook |
| Mike | mike@company.com | HR, All Employees | salary_data, hr_handbook |

## 🔍 Key Test Scenarios

### Scenario 1: Team-Based Access
- **Query:** "What are the current team projects?"
- **Alice (Team A member):**
  - ✅ Unsecured: Gets answer (but sees all docs)
  - ✅ Secured: Gets answer (only from team_notes and eng_specs)
- **John (regular employee):**
  - ✅ Unsecured: Gets answer (unauthorized!)
  - ❌ Secured: Access denied

### Scenario 2: Executive Access
- **Query:** "What were Q4 2025 financial results?"
- **Sarah (CEO):**
  - ✅ Unsecured: Gets answer
  - ✅ Secured: Gets answer (from quarterly_report and board_minutes)
- **John (regular employee):**
  - ✅ Unsecured: Gets answer (unauthorized!)
  - ❌ Secured: Access denied

### Scenario 3: Sensitive Data Protection
- **Query:** "What is the CEO's total compensation?"
- **Sarah (CEO):**
  - ✅ Unsecured: Gets answer
  - ✅ Secured: Gets answer (from salary_data)
- **John (regular employee):**
  - ✅ Unsecured: Gets answer (SECURITY BREACH!)
  - ❌ Secured: Access denied (PROTECTED!)

### Scenario 4: Company-Wide Access
- **Query:** "What is the remote work policy?"
- **Any user:**
  - ✅ Unsecured: Gets answer
  - ✅ Secured: Gets answer (hr_handbook accessible to all_employees team)

## 🔧 Customization

### Adjust Chunk Size

In `rag_pipeline.py`:
```python
def chunk_text(text: str, chunk_size: int = 2000) -> List[str]:
    # Change chunk_size: larger = fewer chunks, more context per chunk
```

### Change Number of Retrieved Results
```python
results = collection.query(
    query_texts=[question],
    n_results=3  # Adjust: 3-5 for large chunks, 5-10 for small chunks
)
```

## 🐛 Troubleshooting

### ChromaDB errors
```bash
# Delete and recreate database
rm -rf chroma_db/
python rag_pipeline.py  # Choose option 1 or 2 to check
```

### Descope schema errors
```bash
# Delete schema in Descope Console (Authorization → FGA → Delete button)
# Then re-run setup
python setup_descope.py
```

### "Insufficient authorized content" for all queries
- Verify relationships in Descope Console
- Check test user emails match exactly
- Ensure `setup_descope.py` completed successfully with all tests passing (critical)

### OpenAI API errors
- Verify API key in `.env`
- Check OpenAI account has credits
- Ensure no rate limits hit

## 📚 Learn More

- [Descope ReBAC Documentation](https://docs.descope.com/authorization/rebac)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI Developers' Guide](https://developers.openai.com/api/docs)

## 💡 Key Takeaways

1. **Clear Separation of Concerns:** ChromaDB handles semantic search, Descope handles authorization
2. **Dynamic Permissions:** Add a user to a team → instant access to all team documents
3. **Relationship-Based:** Access derived from relationships, not hardcoded metadata
4. **Auditability:** Clear explanation of why users have access via Descope (ownership, team membership, sharing)
5. **Scalability:** One relationship change updates access across all documents

## 📄 License

This demo is provided as-is for educational purposes for the accompanying tutorial: [Add ReBAC to Your RAG Pipeline With Descope]().

---

Author: Manish Hatwalne
