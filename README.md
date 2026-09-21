# Marsa Maroc Internship Management

Application Flask de gestion des stages, avec Supabase pour l'authentification et la base de donnees.

## Structure

- `backend/` : application Flask, modules Python, templates PDF et stockage runtime.
- `frontend/` : templates Jinja et assets statiques servis par Flask.
- `supabase/migrations/` : migrations SQL Supabase.
- `tools/` : scripts de diagnostic et ancienne implementation Node.

## Lancement local

Depuis la racine :

```powershell
pip install -r backend/requirements.txt
flask --app wsgi:app run
```

Copier `.env.example` vers l'environnement local et renseigner les variables Supabase. Ne jamais publier `SUPABASE_SERVICE_ROLE_KEY` dans le frontend.

## Deploiement

Consulter [DEPLOYMENT.md](DEPLOYMENT.md). Le backend Flask doit etre deploye sur un hebergeur Python. Netlify pourra heberger un frontend React/Vite apres migration des templates Jinja.
