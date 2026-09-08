import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pdfrw import PdfReader, PdfWriter, PageMerge
import fitz

def test_evaluation():
    template_path = "pdf/Evaluation stage.pdf"
    output_pdf = "generated_pdfs/test_eval_new_alignment.pdf"
    
    os.makedirs("generated_pdfs", exist_ok=True)
    
    # Page size: 841.92 x 595.32 (Landscape)
    c = canvas.Canvas("temp_eval_test.pdf", pagesize=(841.92, 595.32))
    
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    def draw_text(c, txt, x, y, max_width=400, font_size=11.5, font_name='Helvetica-Bold'):
        txt = str(txt).strip()
        size = font_size
        c.setFont(font_name, size)
        c.setFillColor(brand_color)
        while size > 6 and c.stringWidth(txt, font_name, size) > max_width:
            size -= 0.5
        c.setFont(font_name, size)
        c.drawString(x, y, txt)
        print(f"Drew: {txt!r} at ({x}, {y}) with size={size}")

    # Fill fields with our newly calculated coordinates and font sizes
    # Nom & Prénom: baseline 433.42, using 434.5
    draw_text(c, "RAYAN FARIS", 245, 434.5, max_width=530, font_size=12)
    
    # Spécialité: baseline 406.51, using 407.5
    draw_text(c, "DEVELOPPEMENT LOGICIEL", 138, 407.5, max_width=250, font_size=12)
    
    # Ecole: baseline 406.51, using 407.5, starts at 568
    draw_text(c, "ENSAS - ECOLE NATIONALE DES SCIENCES APPLIQUEES", 568, 407.5, max_width=210, font_size=12)
    
    # Encadrant: baseline 379.63, using 380.5, starts at 273
    draw_text(c, "MOHAMMED EL FARIS", 273, 380.5, max_width=230, font_size=12)
    
    # Fonction: baseline 379.63, using 380.5, starts at 565
    draw_text(c, "CHEF DE DEPARTEMENT IT", 565, 380.5, max_width=215, font_size=12)
    
    # Entité d'accueil: baseline 352.75, using 353.5, starts at 168
    draw_text(c, "DSI - SYSTEMES D'INFORMATION", 168, 353.5, max_width=245, font_size=12)
    
    # Période: baseline 352.75, using 353.5, starts at 603
    draw_text(c, "01/06/2026 AU 10/07/2026", 603, 353.5, max_width=180, font_size=12)
    
    # Appreciation globale: baseline 196.97, using 198.0
    draw_text(c, "Excellent stage, stagiaire très compétent et impliqué dans ses tâches.", 268, 198.0, max_width=535, font_size=11)
    
    # Observations: baseline 162.89, using 164.0
    draw_text(c, "Recommandé pour un poste futur de développeur au sein de la DSI.", 268, 164.0, max_width=533, font_size=11)
    
    # Criteria: Bon (581, 295), Assiduite: Excellent (713, 309), etc.
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(713, 307, '✓') # Assiduite -> Excellent
    c.drawCentredString(581, 293, '✓') # Valeur Prof -> Bon
    c.drawCentredString(713, 276, '✓') # Adaptation -> Excellent
    c.drawCentredString(713, 253, '✓') # Relations -> Excellent
    
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_eval_test.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_pdf, trailer=template).write()
    os.remove("temp_eval_test.pdf")
    print(f"Generated test PDF: {output_pdf}")
    
    # Convert to PNG
    doc = fitz.open(output_pdf)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    pix.save("generated_pdfs/test_eval_new_alignment.png")
    doc.close()
    print("Generated PNG: generated_pdfs/test_eval_new_alignment.png")

if __name__ == "__main__":
    test_evaluation()
