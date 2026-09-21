import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pdfrw import PdfReader, PdfWriter, PageMerge
import fitz

def test_fiche():
    template_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
    output_pdf = "generated_pdfs/test_fiche_new_alignment.pdf"
    
    os.makedirs("generated_pdfs", exist_ok=True)
    
    # Page size: 595.32 x 841.92 (Portrait)
    c = canvas.Canvas("temp_fiche_test.pdf", pagesize=(595.32, 841.92))
    
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    # Helper for grid text
    def draw_grid_text(c, text, start_x, pitch, y, font_size=10, max_chars=17):
        c.setFont("Helvetica-Bold", font_size)
        c.setFillColor(HexColor('#001a4d'))
        chars = [char for char in str(text).upper() if char.isalnum() or char in " -_"]
        chars = chars[:max_chars]
        for idx, char in enumerate(chars):
            x_pos = start_x + (idx * pitch) + (pitch / 2)
            c.drawCentredString(x_pos, y, char)

    # Helper for date digits
    def draw_date_digits(c, date_str, xs, y, font_size=10):
        digits = re.sub(r'\D', '', date_str) if date_str else ""
        digits = digits.ljust(8, ' ')[:8]
        c.setFont('Courier-Bold', font_size)
        c.setFillColor(brand_color)
        for idx, char in enumerate(digits):
            x_center = xs[idx]
            c.drawCentredString(x_center, y, char)

    # Helper for bounded text
    def draw_bounded_string(c, txt, x, y, max_width, initial_size=11.0, font_name='Helvetica-Bold'):
        txt = str(txt).strip()
        size = initial_size
        c.setFont(font_name, size)
        c.setFillColor(brand_color)
        while size > 5.5 and c.stringWidth(txt, font_name, size) > max_width:
            size -= 0.5
        c.setFont(font_name, size)
        c.drawString(x, y, txt)
        print(f"Fiche - Drew: {txt!r} at ({x}, {y}) with size={size}")

    # Fill grid texts (Nom, Prenom, Phone)
    draw_grid_text(c, "RAYAN", start_x=174.50, pitch=23.04, y=660.39, font_size=10, max_chars=17)
    draw_grid_text(c, "FARIS", start_x=174.50, pitch=23.04, y=628.04, font_size=10, max_chars=17)
    draw_grid_text(c, "0776654321", start_x=174.50, pitch=23.04, y=595.94, font_size=10, max_chars=17)

    # Etablissement: baseline 565.57, using 567.0, X starts after "Etablissement :" at 135
    draw_bounded_string(c, "ENSAS - ECOLE NATIONALE DES SCIENCES APPLIQUEES DE SAFI", x=135, y=567.0, max_width=390)

    # Profil et Niveau: baseline 541.57, using 543.0, X starts after "Profil et Niveau :" at 140
    draw_bounded_string(c, "DEVELOPPEMENT LOGICIEL - BAC +5", x=140, y=543.0, max_width=380)

    # Checkbox - Passage (center: 242.33, 511.27)
    c.setStrokeColor(brand_color)
    c.setLineWidth(2.0)
    c.line(242.33 - 4, 511.27 - 4, 242.33 + 4, 511.27 + 4)
    c.line(242.33 + 4, 511.27 - 4, 242.33 - 4, 511.27 + 4)

    # Division d'affectation: baseline 399.47, using 401.0, X starts after label at 172
    draw_bounded_string(c, "DSI - SYSTEMES D'INFORMATION", x=172, y=401.0, max_width=350)

    # Encadrant: baseline 379.19, using 380.7, X starts after label at 113
    draw_bounded_string(c, "MOHAMMED EL FARIS", x=113, y=380.7, max_width=410)

    # Thème: baseline 358.79, using 360.3, X starts after label at 142
    draw_bounded_string(c, "DEVELOPPEMENT ET INTEGRATION D'APPLICATIONS WEB", x=142, y=360.3, max_width=380)

    # Date digits
    import re
    start_date_xs = [209.09, 220.91, 251.09, 265.43, 294.17, 308.64, 323.11, 337.51]
    end_date_xs = [380.71, 395.11, 423.97, 438.39, 467.14, 481.54, 496.00, 510.46]
    draw_date_digits(c, "01/06/2026", start_date_xs, y=345.33, font_size=10)
    draw_date_digits(c, "10/07/2026", end_date_xs, y=345.33, font_size=10)

    c.save()

    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_fiche_test.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_pdf, trailer=template).write()
    os.remove("temp_fiche_test.pdf")
    print(f"Generated test PDF: {output_pdf}")

    # Convert to PNG
    doc = fitz.open(output_pdf)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    pix.save("generated_pdfs/test_fiche_new_alignment.png")
    doc.close()
    print("Generated PNG: generated_pdfs/test_fiche_new_alignment.png")

if __name__ == "__main__":
    test_fiche()
