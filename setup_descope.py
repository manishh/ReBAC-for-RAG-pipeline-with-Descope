"""
Descope ReBAC Setup Script
Populates users, documents, teams, and relationships for RAG demo
Run this ONCE to set up authorization data in Descope
"""

import os
from descope import DescopeClient, AuthException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Descope client
descope_client = DescopeClient(
    project_id=os.getenv("DESCOPE_PROJECT_ID"),
    management_key=os.getenv("DESCOPE_MANAGEMENT_KEY")
)

def create_users():
    """Create sample users in Descope"""
    users = [
        {
            "login_id": "alice@company.com",
            "email": "alice@company.com",
            "display_name": "Alice Chen",
            "role": "engineer"
        },
        {
            "login_id": "sarah@company.com",
            "email": "sarah@company.com",
            "display_name": "Sarah Johnson",
            "role": "ceo"
        },
        {
            "login_id": "john@company.com",
            "email": "john@company.com",
            "display_name": "John Doe",
            "role": "engineer"
        },
        {
            "login_id": "jane@company.com",
            "email": "jane@company.com",
            "display_name": "Jane Smith",
            "role": "finance_analyst"
        },
        {
            "login_id": "mike@company.com",
            "email": "mike@company.com",
            "display_name": "Mike Wilson",
            "role": "hr_manager"
        }
    ]
    
    print("Creating users...")
    for user_data in users:
        try:
            descope_client.mgmt.user.create(
                login_id=user_data["login_id"],
                email=user_data["email"],
                display_name=user_data["display_name"]
            )
            print(f"  ✓ Created user: {user_data['email']}")
        except AuthException as e:
            if "already exists" in str(e).lower():
                print(f"  → User already exists: {user_data['email']}")
            else:
                print(f"  ✗ Error creating {user_data['email']}: {e}")

def create_schema():
    """Define ReBAC schema in Descope using DSL format"""
    print("\nDefining ReBAC schema...")
    
    # Define schema in DSL format as per Descope docs
    schema = """model AuthZ 1.0

type user

type Team
  relation member: user

type doc
  relation owner: user
  relation shared_with: user
  relation team: Team
  permission can_view: owner | shared_with | team.member"""
    
    try:
        descope_client.mgmt.fga.save_schema(schema)
        print("  ✓ Schema defined successfully")
    except Exception as e:
        print(f"  → Schema error: {e}")

def create_relations():
    """Create relationships between users, teams, and documents"""
    print("\nCreating relationships...")
    
    # FGA relations format as per Descope docs
    relations = []
    
    # ALL users are members of all_employees (for company-wide documents)
    for user_email in ["alice@company.com", "sarah@company.com", "john@company.com", 
                       "jane@company.com", "mike@company.com"]:
        relations.append({
            "resource": "all_employees",
            "resourceType": "Team",
            "relation": "member",
            "target": user_email,
            "targetType": "user"
        })
    
    # Specific team memberships
    team_memberships = [
        ("engineering", "alice@company.com"),
        ("team_a", "alice@company.com"),
        ("executive", "sarah@company.com"),
        ("finance", "jane@company.com"),
        ("hr", "mike@company.com"),
    ]
    
    for team, user in team_memberships:
        relations.append({
            "resource": team,
            "resourceType": "Team",
            "relation": "member",
            "target": user,
            "targetType": "user"
        })
    
    # Document ownership
    doc_owners = [
        ("team_notes_001", "alice@company.com"),
        ("board_minutes_001", "sarah@company.com"),
        ("quarterly_report_q4_2025", "jane@company.com"),
        ("eng_specs_auth_001", "alice@company.com"),
        ("hr_handbook_2026", "mike@company.com"),
        ("salary_data_2026", "mike@company.com"),
    ]
    
    for doc, owner in doc_owners:
        relations.append({
            "resource": doc,
            "resourceType": "doc",
            "relation": "owner",
            "target": owner,
            "targetType": "user"
        })
    
    # Team access to documents - use 'team' relation instead of 'can_access'
    team_access = [
        ("hr_handbook_2026", "all_employees"),
        ("team_notes_001", "team_a"),
        ("eng_specs_auth_001", "engineering"),
        ("board_minutes_001", "executive"),
        ("quarterly_report_q4_2025", "executive"),
        ("salary_data_2026", "executive"),
        ("quarterly_report_q4_2025", "finance"),
        ("salary_data_2026", "hr"),
    ]
    
    for doc, team in team_access:
        relations.append({
            "resource": doc,
            "resourceType": "doc",
            "relation": "team",
            "target": team,
            "targetType": "Team"
        })
    
    # Create all relations in batch
    try:
        descope_client.mgmt.fga.create_relations(relations)
        print(f"  ✓ Created {len(relations)} relations successfully")
    except Exception as e:
        # If batch fails, try one by one to see which ones already exist
        print(f"  → Batch creation failed, creating individually...")
        for relation in relations:
            try:
                descope_client.mgmt.fga.create_relations([relation])
                print(f"  ✓ {relation['resource']} --{relation['relation']}--> {relation['target']}")
            except Exception as e2:
                if "already exists" in str(e2).lower() or "duplicate" in str(e2).lower():
                    print(f"  → Relation already exists: {relation['resource']} --> {relation['target']}")
                else:
                    print(f"  ✗ Error: {e2}")

def test_permissions():
    """Test authorization checks"""
    print("\n" + "="*60)
    print("Testing Authorization Checks")
    print("="*60)
    
    test_cases = [
        ("alice@company.com", "team_notes_001", True),
        ("alice@company.com", "board_minutes_001", False),
        ("sarah@company.com", "board_minutes_001", True),
        ("sarah@company.com", "salary_data_2026", True),
        ("john@company.com", "salary_data_2026", False),
        ("john@company.com", "hr_handbook_2026", True),
        ("jane@company.com", "quarterly_report_q4_2025", True),
        ("mike@company.com", "salary_data_2026", True),
    ]
    
    for user, document, expected in test_cases:
        try:
            # Use the check function as per docs
            check_result = descope_client.mgmt.fga.check([{
                "resource": document,
                "resourceType": "doc",
                "relation": "can_view",
                "target": user,
                "targetType": "user"
            }])
            
            has_access = check_result[0]["allowed"] if check_result else False
            status = "✓" if has_access == expected else "✗"
            print(f"{status} {user} can_view {document}: {has_access} (expected: {expected})")
        except Exception as e:
            print(f"✗ Error checking {user} -> {document}: {e}")

def main():
    print("="*60)
    print("Descope ReBAC Setup for RAG Pipeline (One time)")
    print("="*60)
    
    # Step 1: Create users
    create_users()
    
    # Step 2: Define schema
    create_schema()
    
    # Step 3: Create relationships
    create_relations()
    
    # Step 4: Test permissions
    test_permissions()
    
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    # print("\nNext steps:")
    # print("1. Verify relationships in Descope console")
    # print("2. Run secured RAG pipeline: python rag_pipeline_secured.py")

"""
$ python setup_descope.py
============================================================
Descope ReBAC Setup for RAG Pipeline
============================================================
Creating users...
  ✓ Created user: alice@company.com
  ✓ Created user: sarah@company.com
  ✓ Created user: john@company.com
  ✓ Created user: jane@company.com
  ✓ Created user: mike@company.com

Defining ReBAC schema...
  ✓ Schema defined successfully

Creating relationships...
  ✓ Created 24 relations successfully

============================================================
Testing Authorization Checks
============================================================
✓ alice@company.com can_view team_notes_001: True (expected: True)
✓ alice@company.com can_view board_minutes_001: False (expected: False)
✓ sarah@company.com can_view board_minutes_001: True (expected: True)
✓ sarah@company.com can_view salary_data_2026: True (expected: True)
✓ john@company.com can_view salary_data_2026: False (expected: False)
✓ john@company.com can_view hr_handbook_2026: True (expected: True)
✓ jane@company.com can_view quarterly_report_q4_2025: True (expected: True)
✓ mike@company.com can_view salary_data_2026: True (expected: True)

============================================================
Setup Complete!
============================================================
"""    

if __name__ == "__main__":
    main()
