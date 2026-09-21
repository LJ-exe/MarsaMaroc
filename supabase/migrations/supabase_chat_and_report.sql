-- =====================================================
-- Migration: Chat and Intern Report Workflow
-- Run this in the Supabase SQL Editor
-- =====================================================

-- 1. Add chat messages column (JSONB array of messages)
ALTER TABLE applications ADD COLUMN IF NOT EXISTS chat_messages JSONB DEFAULT '[]'::jsonb;

-- 2. Add intern report file path column
ALTER TABLE applications ADD COLUMN IF NOT EXISTS intern_report_path TEXT DEFAULT NULL;

-- Done!
SELECT 'Chat and Report workflow columns added successfully' AS result;
