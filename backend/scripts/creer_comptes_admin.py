"""
Crée les comptes RH et Affectation dans Supabase Auth + profiles.

Prérequis :
    1. Exécuter supabase/migrations/supabase_fix_role_constraint.sql puis supabase/migrations/supabase_fix_login_definitif.sql
  2. Ajouter dans .env la clé service_role (Supabase → Settings → API → service_role secret)

Usage :
  python scripts/creer_comptes_admin.py
"""

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
load_dotenv(os.path.join(ROOT, ".env.local"))
load_dotenv(os.path.join(ROOT, ".env"))

from backend.db_config import creer_client_supabase

URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

COMPTES = [
    {
        "email": "rh@marsamaroc.ma",
        "password": "12345678",
        "name": "Responsable RH",
        "role": "rh",
    },
    {
        "email": "aff@marsamaroc.ma",
        "password": "12345678",
        "name": "Responsable Affectation",
        "role": "affectation",
    },
]


def main():
    if not URL or not SERVICE_KEY:
        print("ERREUR : ajoutez SUPABASE_SERVICE_ROLE_KEY dans .env")
        print("  Supabase → Project Settings → API → service_role (secret)")
        sys.exit(1)

    if "publishable" in SERVICE_KEY:
        print("ERREUR : utilisez la clé secret (sb_secret_...), pas la clé publishable.")
        sys.exit(1)

    client = creer_client_supabase(URL, SERVICE_KEY)

    for compte in COMPTES:
        email = compte["email"]
        print(f"\n--- {email} ---")
        try:
            client.auth.admin.create_user(
                {
                    "email": email,
                    "password": compte["password"],
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": compte["name"],
                        "role": compte["role"],
                    },
                }
            )
            print("  Compte Auth créé.")
        except Exception as exc:
            msg = str(exc).lower()
            if "already been registered" in msg or "already exists" in msg:
                print("  Compte déjà existant, mise à jour du mot de passe...")
                try:
                    users = client.auth.admin.list_users()
                    user_list = getattr(users, "users", None) or users
                    uid = None
                    for u in user_list:
                        u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                        if u_email and u_email.lower() == email.lower():
                            uid = getattr(u, "id", None) or u.get("id")
                            break
                    if uid:
                        client.auth.admin.update_user_by_id(
                            uid,
                            {
                                "password": compte["password"],
                                "email_confirm": True,
                            },
                        )
                        print("  Mot de passe mis à jour.")
                except Exception as exc2:
                    print(f"  Attention mise à jour : {exc2}")
            else:
                print(f"  ERREUR Auth : {exc}")
                continue

        try:
            users = client.auth.admin.list_users()
            user_list = getattr(users, "users", None) or users
            uid = None
            for u in user_list:
                u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                if u_email and u_email.lower() == email.lower():
                    uid = getattr(u, "id", None) or u.get("id")
                    break
            if uid:
                client.table("profiles").upsert(
                    {
                        "id": uid,
                        "email": email,
                        "name": compte["name"],
                        "role": compte["role"],
                    }
                ).execute()
                print(f"  Profil synchronisé (role={compte['role']}).")
        except Exception as exc:
            print(f"  ERREUR profil : {exc}")

    print("\n=== Test connexion ===")
    anon = creer_client_supabase(URL, os.getenv("SUPABASE_KEY"))
    for compte in COMPTES:
        try:
            anon.auth.sign_in_with_password(
                {"email": compte["email"], "password": compte["password"]}
            )
            print(f"  OK login : {compte['email']}")
        except Exception as exc:
            print(f"  ECHEC login {compte['email']} : {exc}")

    print("\nTerminé. Connectez-vous sur http://127.0.0.1:5000/login")


if __name__ == "__main__":
    main()
