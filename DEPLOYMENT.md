# Deployment architecture

## Etat actuel

L'application utilise des templates Jinja servis par Flask. Elle n'est donc pas encore un frontend statique deployable directement sur Netlify.

- Flask (`backend/app.py`) : pages, sessions, API, uploads et generation de PDF.
- Supabase : Auth, PostgreSQL et stockage possible des documents.
- `frontend/templates/` et `frontend/static/` : frontend actuel, servi par Flask.
- `backend/pdf/` et `backend/storage/` : modèles PDF et fichiers runtime du backend.
- `tools/legacy-node/` : ancienne implementation Express, non utilisée pour le déploiement Flask.

## Cible recommandee

1. **Un hebergement backend Python** execute Flask depuis `backend/`.
2. **Supabase** fournit Auth, PostgreSQL et Storage.
3. **Netlify** expose le frontend via le proxy `netlify/functions/backend-proxy.mjs`.
4. Netlify transmet les pages, les assets et les routes `/api/...` au backend avec `BACKEND_URL`.

Supabase ne remplace pas l'hebergement Flask : il ne peut pas executer les routes Python ni les traitements PDF/Outlook de ce projet.

## Organisation cible, apres migration du frontend

```text
project-root/
  frontend/                 # Templates Jinja et assets actuels
    templates/
    static/
  backend/                  # Flask deploye sur un hebergeur Python
    app.py
    auth_helpers.py
    db_config.py
    requirements.txt
    pdf/
    storage/
  tools/                    # Scripts de diagnostic et de test
  supabase/
    migrations/
```

Cette configuration est un proxy de transition : les templates Jinja restent rendus par Flask, mais le domaine public peut etre Netlify. Une migration React/Vite reste nécessaire si l'on veut un frontend Netlify autonome.

## Variables d'environnement

Copier `.env.example` vers l'environnement du backend. Dans Netlify, ajouter uniquement `BACKEND_URL=https://adresse-publique-du-backend`. Ne jamais publier `SUPABASE_SERVICE_ROLE_KEY` dans Netlify ou dans le navigateur.

## Publication Netlify

### 1. Supabase

1. Ouvrir le projet Supabase et le SQL Editor.
2. Executer les fichiers de `supabase/migrations/` dans l'ordre fonctionnel indique dans `WORKFLOW_DOCUMENTS_FINAUX.md`.
3. Verifier que les tables `profiles` et `applications` existent et que les politiques RLS sont actives.
4. Recuperer l'URL Supabase et la cle publique. Garder la `SUPABASE_SERVICE_ROLE_KEY` uniquement pour le backend.

### 2. Backend Flask sur Render

1. Pousser ce dossier sur GitHub, sans `.env.local` ni fichiers runtime.
2. Dans Render, choisir **New + Web Service**, puis connecter le depot.
3. Utiliser `render.yaml`, ou saisir manuellement :
  - Build command : `pip install -r backend/requirements.txt`
  - Start command : `gunicorn wsgi:app`
4. Ajouter dans Render les variables de `.env.example`, notamment `SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` et `SUPABASE_SERVICE_ROLE_KEY`.
5. Attendre une URL backend, puis tester `https://backend.example.com/`.

### 3. Frontend/proxy Netlify

1. Dans Netlify, choisir **Add new site > Import an existing project**.
2. Choisir le meme depot GitHub.
3. Laisser Netlify utiliser `netlify.toml`.
4. Ajouter la variable Netlify `BACKEND_URL` avec l'URL Render exacte, sans slash final.
5. Redéployer le site.
6. Tester `/`, `/login`, `/static/logo_marsa.png` et une route `/api/...`.

Le site Netlify actuel est un proxy de transition : les pages Jinja sont encore rendues par Flask. Il ne faut donc pas supprimer le backend après la publication Netlify.

## Lancement local

Depuis la racine du projet :

```powershell
pip install -r backend/requirements.txt
flask --app wsgi:app run
```

Pour un serveur WSGI de production :

```text
gunicorn wsgi:app
```

## Limites a traiter avant production

- Les fonctions Outlook (`win32com`) necessitent Windows et ne fonctionneront pas sur un serveur Linux classique.
- Les uploads et PDF actuellement ecrits sur le disque local doivent migrer vers Supabase Storage ou un stockage persistant.
- La session Flask doit utiliser un secret de production et une configuration HTTPS.
- Les migrations SQL doivent etre regroupees dans `supabase/migrations/` et executees dans l'ordre.
- Les fichiers `backend/storage/emails_sent/`, `backend/storage/generated_pdfs/` et `backend/storage/uploads/` sont des donnees runtime : ils ne doivent pas etre publies par Git ou Netlify.
