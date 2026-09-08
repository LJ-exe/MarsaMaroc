-- =====================================================
-- Migration: Evaluation & Attestation Workflow
-- Run this in the Supabase SQL Editor
-- =====================================================

-- 1. Add evaluation columns to applications table
ALTER TABLE applications ADD COLUMN IF NOT EXISTS evaluation_pdf TEXT;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS evaluation_status TEXT DEFAULT NULL;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS evaluation_submitted_at TIMESTAMPTZ;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS evaluation_data JSONB;

-- 2. Add attestation columns
ALTER TABLE applications ADD COLUMN IF NOT EXISTS attestation_pdf TEXT;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS attestation_status TEXT DEFAULT NULL;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS attestation_generated_at TIMESTAMPTZ;

-- 3. Add mentor function column
ALTER TABLE applications ADD COLUMN IF NOT EXISTS mentor_function TEXT;

-- 4. Add notifications column
ALTER TABLE applications ADD COLUMN IF NOT EXISTS notifications JSONB DEFAULT '[]'::jsonb;

-- Done!
SELECT 'Evaluation workflow columns added successfully' AS result;
