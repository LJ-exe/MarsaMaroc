import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pdfrw import PdfReader, PdfWriter, PageMerge
import fitz

def test_attestation_v3():
    template_path = "pdf/Attestation de stage .pdf"
    output_pdf = "generated_pdfs/test_attestation_v3.pdf"
    output_png = "generated_pdfs/test_attestation_v3.png"
    
    os.makedirs("generated_pdfs", exist_ok=True)
    
    # Portrait page size
    c = canvas.Canvas("temp_att_v3.pdf", pagesize=(595.32, 841.92))
    
    brand_color = HexColor('#001a4d')
    c.setFillColor(brand_color)
    
    def draw_text(c, txt, x, y, max_width=120, font_size=9.0, font_name='Helvetica-Bold'):
        txt = str(txt).strip()
        size = font_size
        c.setFont(font_name, size)
        c.setFillColor(brand_color)
        while size > 6.0 and c.stringWidth(txt, font_name, size) > max_width:
            size -= 0.5
        c.setFont(font_name, size)
        c.drawString(x, y, txt)
        print(f"Attestation V3 - Drew: {txt!r} at ({x}, {y}) with size={size}")

    # 1. DRH Name (baseline Y = 626, starting at X = 195, max_width = 68)
    drh_name = "AHMED BENANI"
    draw_text(c, drh_name, 195, 626, max_width=68, font_size=9.0)
    
    # 2. Intern Name (baseline Y = 556, starting at X = 135, max_width = 72)
    intern_name = "RAYAN FARIS"
    draw_text(c, intern_name.upper(), 135, 556, max_width=72, font_size=9.0)
    
    # 3. Period / Dates (baseline Y = 528, starting at X = 135, max_width = 250)
    period = "01/06/2026 - 10/07/2026"
    period_formatted = period.replace(' - ', ' au ').replace('-', ' au ').strip()
    draw_text(c, period_formatted, 135, 528, max_width=250, font_size=9.0)
    
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_att_v3.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_pdf, trailer=template).write()
    os.remove("temp_att_v3.pdf")
    print(f"Generated test PDF: {output_pdf}")
    
    # Convert to PNG
    doc = fitz.open(output_pdf)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    pix.save(output_png)
    doc.close()
    print("Generated PNG:", output_png)

if __name__ == "__main__":
    test_attestation_v3()
