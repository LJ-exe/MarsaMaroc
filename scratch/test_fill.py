import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pdfrw import PdfReader, PdfWriter, PageMerge

def test_fill_evaluation():
    template_path = "pdf/Evaluation stage .pdf"
    output_path = "generated_pdfs/test_eval_filled.pdf"
    
    # Page size: 841.92 x 595.32 (Landscape)
    c = canvas.Canvas("temp_eval.pdf", pagesize=(841.92, 595.32))
    
    # Premium blue color for text
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    # 1. Fill Header info
    # Nom & prénom
    c.setFont("Helvetica-Bold", 10)
    c.drawString(245, 436, "JEAN DUPONT")
    
    # Spécialité & Ecole
    c.drawString(155, 409, "Génie Logiciel")
    c.drawString(470, 409, "ENSAS - Ecole Nationale des Sciences Appliquées")
    
    # Encadrant & Fonction
    c.drawString(260, 382, "Ahmed Alami")
    c.drawString(470, 382, "Chef de Projet IT")
    
    # Entité d'accueil & Période
    c.drawString(180, 355, "Direction des Systèmes d'Information (DSI)")
    c.drawString(520, 355, "01/03/2026 au 30/06/2026")
    
    # 2. Fill Criteria (Draw a checkmark or filled circle)
    # Midpoints: Faible=328, Moyen=458, Bon=581, Excellent=713
    # Rows: Assiduité=306.79, Valeur=292.15, Adaptation=274.61, Relations=252.41
    
    # Assiduité -> Excellent (713, 309)
    c.circle(713, 309, 4, fill=1, stroke=1)
    
    # Valeur professionnelle -> Bon (581, 295)
    c.circle(581, 295, 4, fill=1, stroke=1)
    
    # Capacité d'adaptation -> Moyen (458, 278)
    c.circle(458, 278, 4, fill=1, stroke=1)
    
    # Relations humaines -> Excellent (713, 255)
    c.circle(713, 255, 4, fill=1, stroke=1)
    
    # Appréciation globale & Observations (Y=199.73 & Y=162.17)
    c.drawString(265, 199, "Excellent stage, stagiaire très motivé et compétent.")
    c.drawString(265, 162, "Recommandé pour un recrutement futur.")
    
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_eval.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_path, trailer=template).write()
    os.remove("temp_eval.pdf")
    print(f"Filled eval written to {output_path}")

def test_fill_attestation():
    template_path = "pdf/ATTESTATION DE STAGE challal.pdf"
    output_path = "generated_pdfs/test_attestation_filled.pdf"
    
    # Page size: 612 x 792 (Portrait)
    c = canvas.Canvas("temp_att.pdf", pagesize=(612, 792))
    
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    # The subagent identified coordinates:
    # Nom du stagiaire: Y=400 to 415 (Baseline ~407), X=75 to 190.
    # Wait, let's write text at various coordinates to see.
    # Let's test the coordinates and see where they land.
    c.setFont("Helvetica-Bold", 11)
    
    # We will write coordinates on the page to verify them!
    # For instance:
    c.drawString(200, 470, "TEST ATTESTATION DE STAGE")
    
    # Intern Name (Nom du stagiaire)
    c.drawString(220, 520, "JEAN DUPONT")  # Let's test Y=520, X=220
    
    # Dates
    c.drawString(150, 480, "01/03/2026")
    c.drawString(270, 480, "30/06/2026")
    
    # Department
    c.drawString(300, 450, "Systèmes d'Information")
    
    # Signatures placeholder
    c.drawString(100, 150, "Chef de Département")
    c.drawString(400, 150, "Directeur des Ressources Humaines")
    
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_att.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_path, trailer=template).write()
    os.remove("temp_att.pdf")
    print(f"Filled attestation written to {output_path}")

if __name__ == "__main__":
    test_fill_evaluation()
    test_fill_attestation()
