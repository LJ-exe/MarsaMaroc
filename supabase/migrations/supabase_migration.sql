-- Table utilisée par l'application : public.applications
-- Exécuter dans Supabase → SQL Editor

ALTER TABLE applications ADD COLUMN IF NOT EXISTS first_name text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS last_name text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS phone text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS school text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS specialty text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS level text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS type text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS period text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS zone text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS department text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS project text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS mentor text;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS status text DEFAULT 'pending';
ALTER TABLE applications ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

-- Parcours stagiaire (dashboard, envoi RH) — voir aussi supabase/migrations/supabase_stagiaire_dashboard.sql
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS dossier_submitted boolean DEFAULT false;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS submitted_to_rh_at timestamptz;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS requested_doc_type text;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS rh_status_hint text;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS remark text;

-- Politiques RLS : autoriser l'app (clé anon/publishable) à lire et écrire
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "applications_select_public" ON applications;
DROP POLICY IF EXISTS "applications_insert_public" ON applications;
DROP POLICY IF EXISTS "applications_update_public" ON applications;

CREATE POLICY "applications_select_public"
    ON applications FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "applications_insert_public"
    ON applications FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "applications_update_public"
    ON applications FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);
