-- Authentification Marsa Maroc — à exécuter dans Supabase → SQL Editor
-- Prérequis : activer Email/Password dans Authentication → Providers

-- Table profils liée à auth.users
CREATE TABLE IF NOT EXISTS public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at timestamptz DEFAULT now()
);

-- Colonnes (ajout si table déjà existante sans email)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role text DEFAULT 'stagiaire';

-- Contrainte rôle (valeurs attendues par Flask)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
    ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('stagiaire', 'rh', 'affectation'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;

CREATE POLICY "profiles_select_own"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "profiles_insert_own"
    ON public.profiles FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_update_own"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id);

-- Création automatique du profil à l'inscription (trigger robuste)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, name, email, role)
    VALUES (
        NEW.id,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            split_part(COALESCE(NEW.email, 'user'), '@', 1),
            'Utilisateur'
        ),
        NEW.email,
        'stagiaire'
    )
    ON CONFLICT (id) DO UPDATE SET
        email = COALESCE(EXCLUDED.email, public.profiles.email),
        name = COALESCE(NULLIF(EXCLUDED.name, ''), public.profiles.name);
    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        INSERT INTO public.profiles (id) VALUES (NEW.id) ON CONFLICT (id) DO NOTHING;
        RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- Comptes RH / Affectation (créés dans Authentication → Users)
-- Jointure via auth.users (fonctionne même sans colonne email)
-- ============================================================

UPDATE public.profiles p
SET role = 'rh',
    name = 'Responsable RH',
    email = u.email
FROM auth.users u
WHERE p.id = u.id
  AND lower(u.email) = 'rh@marsamaroc.ma';

UPDATE public.profiles p
SET role = 'affectation',
    name = 'Responsable Affectation',
    email = u.email
FROM auth.users u
WHERE p.id = u.id
  AND lower(u.email) = 'aff@marsamaroc.ma';
