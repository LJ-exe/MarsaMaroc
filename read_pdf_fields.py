# -*- coding: utf-8 -*-
# Script pour lire les champs du formulaire PDF template

from pdfrw import PdfReader

template_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"

try:
    template_pdf = PdfReader(template_path)
    
    print("=== Champs du formulaire PDF ===")
    
    if template_pdf.Root.AcroForm:
        for field in template_pdf.Root.AcroForm.Fields:
            field_name = field.T if hasattr(field, 'T') else "Sans nom"
            print(f"Champ: {field_name}")
    else:
        print("Aucun formulaire AcroForm trouvé dans le PDF.")
        print("Le PDF n'a pas de champs de formulaire remplissables.")
        print("Il faut utiliser une autre méthode (ajout de texte aux coordonnées).")
        
except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
