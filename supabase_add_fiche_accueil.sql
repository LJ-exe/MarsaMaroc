-- -*- coding: utf-8 -*-
-- ============================================================
-- إضافة عمود ورقة الاستقبال - نظام إدارة المتدربين Marsa Maroc
-- ============================================================
--
-- هذا الملف يحتوي على إضافة عمود fiche_accueil_pdf
-- لتخزين مسار ملف PDF لورقة الاستقبال.
--
-- AJOUT DE LA COLONNE FICHE D'ACCUEIL PDF
-- Exécuter dans Supabase → SQL Editor

-- Ajouter la colonne fiche_accueil_pdf
ALTER TABLE public.applications ADD COLUMN IF NOT EXISTS fiche_accueil_pdf text;
