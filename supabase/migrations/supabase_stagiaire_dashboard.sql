-- Colonnes pour le parcours stagiaire (dashboard lié au compte, envoi RH, hints visuels)
-- Exécuter dans Supabase → SQL Editor

ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS dossier_submitted boolean DEFAULT false;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS submitted_to_rh_at timestamptz;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS requested_doc_type text;
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS rh_status_hint text;

CREATE INDEX IF NOT EXISTS idx_applications_user_id ON public.applications (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_email ON public.applications (email);
