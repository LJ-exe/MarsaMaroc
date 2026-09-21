-- Corrige l'erreur "Database error saving new user" à la création de comptes
-- Exécuter dans Supabase → SQL Editor AVANT de créer les utilisateurs

-- Colonnes attendues (ajout si manquantes)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role text DEFAULT 'stagiaire';

-- Trigger robuste : n'échoue plus si une colonne manque
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
        -- Secours : au minimum lier l'id auth.users → profiles
        INSERT INTO public.profiles (id)
        VALUES (NEW.id)
        ON CONFLICT (id) DO NOTHING;
        RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Rôles RH / Affectation (après création des users dans Authentication)
UPDATE public.profiles p
SET role = 'rh', name = 'Responsable RH', email = u.email
FROM auth.users u
WHERE p.id = u.id AND lower(u.email) = 'rh@marsamaroc.ma';

UPDATE public.profiles p
SET role = 'affectation', name = 'Responsable Affectation', email = u.email
FROM auth.users u
WHERE p.id = u.id AND lower(u.email) = 'aff@marsamaroc.ma';
