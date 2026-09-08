-- =====================================================
-- Migration: Report Validation and Evaluation Rejection
-- Run this in the Supabase SQL Editor (SQL Editor -> New Query -> Paste & Run)
-- =====================================================

-- 1. Add intern report status column
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS intern_report_status TEXT DEFAULT NULL;

-- 2. Add evaluation reject reason column
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS evaluation_reject_reason TEXT DEFAULT NULL;

-- Done!
SELECT 'Report Validation columns added successfully' AS result;
