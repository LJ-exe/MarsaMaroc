-- Table pour gérer les encadrants (mentors)
-- Cette table permet d'avoir une liste centralisée des encadrants
-- avec possibilité de recherche et ajout dynamique

CREATE TABLE IF NOT EXISTS encadrants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nom TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Désactiver RLS pour permettre l'insertion depuis l'application
ALTER TABLE encadrants DISABLE ROW LEVEL SECURITY;

-- Index pour optimiser la recherche par nom
CREATE INDEX IF NOT EXISTS idx_encadrants_nom ON encadrants(nom);

-- Commentaire sur la table
COMMENT ON TABLE encadrants IS 'Liste des encadrants/mentors pour les stagiaires';
COMMENT ON COLUMN encadrants.id IS 'Identifiant unique de l''encadrant';
COMMENT ON COLUMN encadrants.nom IS 'Nom complet de l''encadrant';
COMMENT ON COLUMN encadrants.created_at IS 'Date de création de l''encadrant';

-- Ajouter la colonne encadrant_id à la table applications
-- Cette colonne stocke l'ID de l'encadrant sélectionné depuis la table encadrants
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'applications' 
        AND column_name = 'encadrant_id'
    ) THEN
        ALTER TABLE applications ADD COLUMN encadrant_id UUID REFERENCES encadrants(id) ON DELETE SET NULL;
        
        COMMENT ON COLUMN applications.encadrant_id IS 'Référence vers l''encadrant sélectionné dans la table encadrants';
        
        RAISE NOTICE 'Colonne encadrant_id ajoutée à la table applications';
    ELSE
        RAISE NOTICE 'La colonne encadrant_id existe déjà dans la table applications';
    END IF;
END $$;
