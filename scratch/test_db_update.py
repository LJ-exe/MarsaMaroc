import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from db_config import creer_client_supabase

supabase = creer_client_supabase(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Retrieve a candidate from the table
res = supabase.table("applications").select("*").limit(1).execute()
if not res.data:
    print("No candidates found")
    sys.exit(0)

candidate = res.data[0]
candidate_id = candidate["id"]
print("Testing update for candidate id:", candidate_id, "name:", candidate["name"])

try:
    update_res = supabase.table("applications").update({
        "evaluation_pdf": "test.pdf",
        "evaluation_status": "En attente",
        "evaluation_submitted_at": "2026-06-03T15:00:00Z",
        "evaluation_data": {"mentor_function": "Test"},
        "mentor_function": "Test",
        "notifications": [{"id": "1", "text": "Test", "read": False}]
    }).eq("id", candidate_id).execute()
    print("Update result success:", len(update_res.data) > 0)
except Exception as e:
    print("Update failed with exception:", e)
