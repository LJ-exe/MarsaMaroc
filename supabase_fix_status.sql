-- Corrige la contrainte de statut sur applications
-- Exécuter dans Supabase → SQL Editor si l'insertion échoue avec applications_status_check

-- 1) Voir la contrainte actuelle :
-- SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'applications_status_check';

-- 2) Remplacer par des valeurs compatibles avec l'application (anglais)
ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_status_check;

ALTER TABLE applications ADD CONSTRAINT applications_status_check
    CHECK (status IN (
        'pending',
        'approved',
        'rejected',
        'action_required',
        'awaiting_assignment'
    ));

ALTER TABLE applications ALTER COLUMN status SET DEFAULT 'pending';
