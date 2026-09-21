-- ============================================================
-- MIGRATION : AJOUT DE LA COLONNE REMARK
-- Supabase → SQL Editor → Paste & Run
-- ============================================================

-- 1) Ajouter la colonne remark si elle n'existe pas
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS remark text;

-- 2) Mettre à jour la contrainte de statut si nécessaire pour supporter 'pending' et les autres statuts
ALTER TABLE public.applications DROP CONSTRAINT IF EXISTS applications_status_check;
ALTER TABLE public.applications ADD CONSTRAINT applications_status_check
    CHECK (status IN (
        'pending',
        'approved',
        'rejected',
        'action_required',
        'awaiting_assignment'
    ));

-- 3) Synchroniser les politiques de sécurité (RLS)
-- S'assurer que le rôle anon et authenticated peuvent modifier la colonne remark
GRANT SELECT, INSERT, UPDATE ON public.applications TO anon, authenticated, service_role;
