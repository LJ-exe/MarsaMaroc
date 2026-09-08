"""Vérification .env + Supabase + routes Flask."""
import os
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
load_dotenv()

checks = []

def ok(msg):
    checks.append(("OK", msg))
    print(f"  [OK] {msg}")

def fail(msg):
    checks.append(("FAIL", msg))
    print(f"  [FAIL] {msg}")

print("=== 1. Variables .env ===")
for key in ("SECRET_KEY", "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_TABLE", "SUPABASE_STATUS_INITIAL", "APP_URL"):
    val = os.getenv(key)
    if val:
        display = val[:40] + "..." if key == "SUPABASE_KEY" and len(val) > 40 else val
        ok(f"{key}={display}")
    else:
        fail(f"{key} manquant")

print("\n=== 2. Connexion Supabase (table applications) ===")
try:
    from db_config import creer_client_supabase

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = creer_client_supabase(url, key)
    table = os.getenv("SUPABASE_TABLE", "applications")
    r = client.table(table).select("id").limit(1).execute()
    ok(f"Lecture table '{table}' — {len(r.data or [])} ligne(s) retournée(s)")
except Exception as e:
    fail(f"Supabase: {e}")

print("\n=== 3. app.py charge les variables ===")
try:
    import app as flask_app

    if flask_app.SUPABASE_URL and flask_app.SUPABASE_KEY:
        ok("app.SUPABASE_URL et app.SUPABASE_KEY définis")
    else:
        fail("Client Supabase non initialisé dans app.py")
    if flask_app.supabase:
        ok("Client supabase créé")
    else:
        fail("supabase est None")
except Exception as e:
    fail(f"Import app: {e}")

print("\n=== Résumé ===")
fails = [c for c in checks if c[0] == "FAIL"]
print(f"  {len(checks) - len(fails)}/{len(checks)} OK")
sys.exit(1 if fails else 0)
