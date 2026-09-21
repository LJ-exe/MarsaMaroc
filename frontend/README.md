# Frontend actuel

Ce dossier contient les templates Jinja et les assets servis par Flask.

- `templates/` : pages HTML avec variables et logique Jinja.
- `static/` : CSS, logo et fichiers statiques publics.

Ce frontend n'est pas encore un frontend React/Vite autonome pour Netlify. Les templates Jinja nécessitent le backend Flask. La migration vers React/Vite pourra utiliser ce dossier comme base fonctionnelle, mais devra remplacer les appels relatifs `/api/...` par l'URL publique du backend.
