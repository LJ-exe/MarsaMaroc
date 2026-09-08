import os
import sys
import requests
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from db_config import creer_client_supabase

supabase = creer_client_supabase(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Retrieve a candidate
res = supabase.table("applications").select("*").limit(1).execute()
if not res.data:
    print("No candidates found")
    sys.exit(0)

candidate = res.data[0]
candidate_id = candidate["id"]
print("Using candidate ID:", candidate_id, "Name:", candidate["name"])

payload = {
    "id": candidate_id,
    "mentor_function": "Ingénieur Logiciel",
    "criteria": {
        "assiduite": "excellent",
        "valeur_professionnelle": "bon",
        "capacite_adaptation": "bon",
        "relations_humaines": "excellent"
    },
    "appreciation_globale": "Très bon stagiaire, sérieux et motivé.",
    "observations": "Poursuivre sur cette lancée.",
    "signatures": {
        "encadrant": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "chef_dept": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }
}

try:
    resp = requests.post("http://localhost:5000/api/candidates/evaluation", json=payload, timeout=10)
    print("Response Status Code:", resp.status_code)
    print("Response JSON:", resp.json())
except Exception as e:
    print("Request failed:", e)
