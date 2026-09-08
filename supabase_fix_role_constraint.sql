-- Corrige : violates check constraint "profiles_role_check"
-- Exécuter AVANT supabase_fix_login_definitif.sql

-- 1) Supprimer l'ancienne contrainte (valeurs RH / Stagiaire / etc.)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;

-- 2) Normaliser les rôles existants vers le format de l'app Flask
UPDATE public.profiles
SET role = 'stagiaire'
WHERE role IS NULL
   OR trim(role) = ''
   OR lower(trim(role)) IN ('stagiaire', 'stagiare', 'candidat', 'user', 'intern');

UPDATE public.profiles
SET role = 'rh'
WHERE lower(trim(role)) IN ('rh', 'hr', 'responsable rh', 'responsable_rh');

UPDATE public.profiles
SET role = 'affectation'
WHERE lower(trim(role)) IN (
    'affectation', 'aff', 'responsable affectation', 'responsable_affectation'
);

-- Toute valeur inconnue → stagiaire
UPDATE public.profiles
SET role = 'stagiaire'
WHERE role IS NULL
   OR lower(trim(role)) NOT IN ('stagiaire', 'rh', 'affectation');

-- 3) Nouvelle contrainte (identique à auth_helpers.py)
ALTER TABLE public.profiles
    ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('stagiaire', 'rh', 'affectation'));

-- 4) Vérification
SELECT id, email, name, role FROM public.profiles ORDER BY role;
