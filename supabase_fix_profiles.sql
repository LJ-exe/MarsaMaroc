-- Corrige la table profiles (colonne email manquante)
-- Exécuter dans Supabase → SQL Editor

-- 1) Ajouter les colonnes manquantes si besoin
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role text DEFAULT 'stagiaire';

-- 2) Remplir email / name depuis auth.users
UPDATE public.profiles p
SET
    email = COALESCE(p.email, u.email),
    name = COALESCE(
        NULLIF(TRIM(p.name), ''),
        u.raw_user_meta_data->>'full_name',
        split_part(u.email, '@', 1)
    ),
    role = COALESCE(NULLIF(TRIM(p.role), ''), 'stagiaire')
FROM auth.users u
WHERE p.id = u.id;

-- 3) Attribuer les rôles RH et Affectation (via auth.users, pas via profiles.email)
UPDATE public.profiles p
SET role = 'rh',
    name = 'Responsable RH'
FROM auth.users u
WHERE p.id = u.id
  AND lower(u.email) = 'rh@marsamaroc.ma';

UPDATE public.profiles p
SET role = 'affectation',
    name = 'Responsable Affectation'
FROM auth.users u
WHERE p.id = u.id
  AND lower(u.email) = 'aff@marsamaroc.ma';

-- 4) Vérification
SELECT p.id, p.name, p.email, p.role, u.email AS auth_email
FROM public.profiles p
JOIN auth.users u ON u.id = p.id
ORDER BY p.role;
