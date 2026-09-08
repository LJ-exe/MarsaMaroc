import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pdfrw import PdfReader, PdfWriter, PageMerge

def test_fill_attestation():
    template_path = "pdf/Attestation de stage .pdf"
    output_path = "generated_pdfs/test_attestation_filled.pdf"
    
    # Page size: 612 x 792 (Portrait)
    c = canvas.Canvas("temp_att_filled.pdf", pagesize=(612, 792))
    
    # Premium deep blue color for text to match Marsa Maroc brand
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    # Helper to draw text
    def draw_text(c, txt, x, y, font_size=10, font_name='Helvetica-Bold'):
        c.setFont(font_name, font_size)
        c.drawString(x, y, txt)

    # Helper for white masking
    def white_mask(c, x, y, w, h):
        from reportlab.lib.colors import white
        c.setFillColor(white)
        c.rect(x, y, w, h, fill=1, stroke=0)
        c.setFillColor(brand_color) # restore

    # 1. Signatory Name (Directeur RH) on Line 1
    # Line 1 is Y=520. "Je soussigné," is from X=100 to X=170. Blank space is X=175 to X=360.
    # We write the name in bold.
    draw_text(c, "Ahmed Benali,", 175, 520, font_size=10, font_name='Helvetica-Bold')

    # 2. Cover the pre-printed specific text in Line 6 and Line 7
    # Line 6 is Y=385, Line 7 is Y=350
    white_mask(c, 75, 376, 470, 18)
    # Line 7: Y=350. Cover from X=75 to X=545 (covers "d'Information, et ce à compter du...")
    white_mask(c, 75, 341, 470, 18)

    # 3. Write our dynamic structured paragraph starting at Line 6 (Y=385), Line 6.5 (Y=358), and Line 7 (Y=330)
    # Line 6 (Y=385)
    # Monsieur ADDY MOHAMMED, étudiant de l'établissement ENSAS (Spécialité : Génie Logiciel)
    c.setFont('Helvetica', 9.5)
    c.drawString(85, 385, "Monsieur ")
    
    # Bold the name
    name_x = 85 + c.stringWidth("Monsieur ", 'Helvetica', 9.5)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(name_x, 385, "ADDY MOHAMMED")
    
    # Regular text for school and specialty
    school_x = name_x + c.stringWidth("ADDY MOHAMMED", 'Helvetica-Bold', 9.5)
    c.setFont('Helvetica', 9.5)
    c.drawString(school_x, 385, ", étudiant de l'établissement ")
    
    school_name_x = school_x + c.stringWidth(", étudiant de l'établissement ", 'Helvetica', 9.5)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(school_name_x, 385, "ENSAS")
    
    spec_x = school_name_x + c.stringWidth("ENSAS", 'Helvetica-Bold', 9.5)
    c.setFont('Helvetica', 9.5)
    c.drawString(spec_x, 385, " (Spécialité : ")
    
    spec_name_x = spec_x + c.stringWidth(" (Spécialité : ", 'Helvetica', 9.5)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(spec_name_x, 385, "Génie Logiciel")
    
    c.setFont('Helvetica', 9.5)
    c.drawString(spec_name_x + c.stringWidth("Génie Logiciel", 'Helvetica-Bold', 9.5), 385, "),")

    # Line 6.5 (Y=358)
    # a effectué un stage de deux mois au sein de la Division Systèmes d'Information,
    c.setFont('Helvetica', 9.5)
    c.drawString(85, 358, "a effectué un stage ")
    
    dur_x = 85 + c.stringWidth("a effectué un stage ", 'Helvetica', 9.5)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(dur_x, 358, "de deux mois")
    
    dept_label_x = dur_x + c.stringWidth("de deux mois", 'Helvetica-Bold', 9.5)
    c.setFont('Helvetica', 9.5)
    c.drawString(dept_label_x, 358, " au sein de ")
    
    dept_x = dept_label_x + c.stringWidth(" au sein de ", 'Helvetica', 9.5)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(dept_x, 358, "la Division Systèmes d'Information")
    
    c.setFont('Helvetica', 9.5)
    c.drawString(dept_x + c.stringWidth("la Division Systèmes d'Information", 'Helvetica-Bold', 9.5), 358, ",")

    # Line 7 (Y=330)
    # et ce du 01/06/2026 au 31/07/2026.
    c.setFont('Helvetica', 9.5)
    c.drawString(85, 330, "et ce du ")
    
    dates_x = 85 + c.stringWidth("et ce du ", 'Helvetica', 9.5)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(dates_x, 330, "01/06/2026 au 31/07/2026")
    
    c.setFont('Helvetica', 9.5)
    c.drawString(dates_x + c.stringWidth("01/06/2026 au 31/07/2026", 'Helvetica-Bold', 9.5), 330, ".")

    # 4. Town & Date above signatures
    current_date = datetime.now().strftime("%d/%m/%Y")
    draw_text(c, f"Fait à Casablanca, le {current_date}", 350, 205, font_size=10, font_name='Helvetica')

    # 5. Names of signatories
    draw_text(c, "Ahmed Benali", 350, 155, font_size=10, font_name='Helvetica-Bold')
    draw_text(c, "Responsable Stage", 80, 155, font_size=10, font_name='Helvetica-Bold')

    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_att_filled.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    
    os.makedirs("generated_pdfs", exist_ok=True)
    PdfWriter(output_path, trailer=template).write()
    os.remove("temp_att_filled.pdf")
    print(f"Filled test attestation written to {output_path}")

if __name__ == "__main__":
    test_fill_attestation()
