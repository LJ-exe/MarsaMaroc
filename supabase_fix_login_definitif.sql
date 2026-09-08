-- ============================================================
-- CORRECTION DÉFINITIVE LOGIN — exécuter TOUT ce fichier
-- Supabase → SQL Editor → Run
-- ============================================================

-- 0) Corriger la contrainte role (stagiaire / rh / affectation)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;

UPDATE public.profiles SET role = 'stagiaire'
WHERE role IS NULL OR trim(role) = ''
   OR lower(trim(role)) NOT IN ('stagiaire', 'rh', 'affectation');

UPDATE public.profiles SET role = 'rh'
WHERE lower(trim(role)) IN ('rh', 'hr', 'responsable rh');

UPDATE public.profiles SET role = 'affectation'
WHERE lower(trim(role)) IN ('affectation', 'aff', 'responsable affectation');

ALTER TABLE public.profiles
    ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('stagiaire', 'rh', 'affectation'));

-- 1) Désactiver le trigger qui bloque la création des comptes
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- 2) Colonnes nécessaires sur profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role text DEFAULT 'stagiaire';

-- 3) Droits pour que l'app et les inserts fonctionnent
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON public.profiles TO anon, authenticated, service_role;

-- 4) Politiques RLS permissives (lecture/écriture profils)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_all" ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_all" ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_all" ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;

CREATE POLICY "profiles_select_all"
    ON public.profiles FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "profiles_insert_all"
    ON public.profiles FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "profiles_update_all"
    ON public.profiles FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- 5) Synchroniser TOUS les utilisateurs Auth → profiles
INSERT INTO public.profiles (id, name, email, role)
SELECT
    u.id,
    COALESCE(
        u.raw_user_meta_data->>'full_name',
        split_part(u.email, '@', 1),
        'Utilisateur'
    ),
    u.email,
    CASE
        WHEN lower(u.email) = 'rh@marsamaroc.ma' THEN 'rh'
        WHEN lower(u.email) = 'aff@marsamaroc.ma' THEN 'affectation'
        ELSE 'stagiaire'
    END
FROM auth.users u
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name,
    role = EXCLUDED.role;

-- 6) Vérification (doit afficher vos comptes)
SELECT u.email, u.email_confirmed_at IS NOT NULL AS confirme, p.role, p.name
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
ORDER BY u.created_at DESC;
