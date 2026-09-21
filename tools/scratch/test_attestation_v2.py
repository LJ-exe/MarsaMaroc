import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pdfrw import PdfReader, PdfWriter, PageMerge
import fitz

def test_attestation_v2():
    template_path = "pdf/Attestation de stage .pdf"
    output_pdf = "generated_pdfs/test_attestation_v2.pdf"
    output_png = "generated_pdfs/test_attestation_v2.png"
    
    os.makedirs("generated_pdfs", exist_ok=True)
    
    # Portrait page size
    c = canvas.Canvas("temp_att_v2.pdf", pagesize=(595.32, 841.92))
    
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    def draw_text(c, txt, x, y, font_size=11, font_name='Helvetica-Bold'):
        c.setFont(font_name, font_size)
        c.drawString(x, y, txt)
        print(f"Attestation V2 - Drew: {txt!r} at ({x}, {y})")

    # 1. DRH Name (baseline Y = 626, starting at X = 160)
    drh_name = "MOHAMMED EL KANTOURI"
    draw_text(c, drh_name, 160, 626, font_size=11)
    
    # 2. Intern Name (baseline Y = 556, starting at X = 80)
    intern_name = "RAYAN FARIS"
    draw_text(c, intern_name.upper(), 80, 556, font_size=11)
    
    # 3. Period / Dates (baseline Y = 528, starting at X = 80)
    period = "01/06/2026 - 10/07/2026"
    period_formatted = period.replace(' - ', ' au ').replace('-', ' au ').strip()
    draw_text(c, period_formatted, 80, 528, font_size=11)
    
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_att_v2.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_pdf, trailer=template).write()
    os.remove("temp_att_v2.pdf")
    print(f"Generated test PDF: {output_pdf}")
    
    # Convert to PNG
    doc = fitz.open(output_pdf)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    pix.save(output_png)
    doc.close()
    print(f"Generated PNG: {output_png}")

if __name__ == "__main__":
    test_attestation_v2()
