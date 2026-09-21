"""
Test de mise à jour du champ remark dans Supabase.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

from backend.db_config import creer_client_supabase, TABLE_APPLICATIONS

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")

def main():
    client = creer_client_supabase(URL, KEY)
    try:
        # Tenter de lire une ligne
        r = client.table(TABLE_APPLICATIONS).select("id").limit(1).execute()
        if not r.data:
            print("Aucune candidature trouvée pour le test.")
            return
        
        cid = r.data[0]["id"]
        print(f"Tentative de mise à jour de la colonne 'remark' pour le candidat id={cid}...")
        
        # Essayer de mettre à jour le champ remark
        client.table(TABLE_APPLICATIONS).update({
            "remark": "Test de remark"
        }).eq("id", cid).execute()
        
        print("✅ REUSSITE : La colonne 'remark' existe et a pu être mise à jour avec succès !")
    except Exception as e:
        print("❌ ERREUR : La colonne 'remark' n'existe peut-être pas ou n'a pas pu être mise à jour.")
        print(f"Détail de l'erreur : {e}")
        print("\n👉 Exécutez le fichier 'supabase/migrations/supabase_add_remark.sql' dans l'éditeur SQL de Supabase pour créer la colonne !")

if __name__ == "__main__":
    main()
