import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, red, blue, green
from pdfrw import PdfReader, PdfWriter, PageMerge
import fitz

def test_grid():
    template_path = "pdf/Attestation de stage .pdf"
    output_pdf = "generated_pdfs/test_attestation_grid.pdf"
    output_png = "generated_pdfs/test_attestation_grid.png"
    
    os.makedirs("generated_pdfs", exist_ok=True)
    
    # Portrait page size
    c = canvas.Canvas("temp_grid.pdf", pagesize=(595.32, 841.92))
    
    # Draw horizontal lines every 10 points between Y=300 and Y=600
    for y in range(300, 620, 10):
        c.setStrokeColor(red if y % 50 == 0 else blue)
        c.setLineWidth(0.5)
        c.line(0, y, 595.32, y)
        
        c.setFont("Helvetica", 6)
        c.setFillColor(red if y % 50 == 0 else blue)
        c.drawString(10, y + 2, f"Y={y}")
        c.drawString(550, y + 2, f"Y={y}")
        
    # Draw vertical lines every 50 points
    for x in range(50, 550, 50):
        c.setStrokeColor(green)
        c.setLineWidth(0.5)
        c.line(x, 0, x, 841.92)
        c.setFont("Helvetica", 6)
        c.setFillColor(green)
        c.drawString(x + 2, 830, f"X={x}")
        c.drawString(x + 2, 20, f"X={x}")
        
    # Let's write some sample text to test placement
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor('#001a4d'))
    
    # 1. DRH Name (e.g. Y=521 or Y=518)
    c.drawString(170, 521, "[DRH NAME Y=521]")
    c.drawString(170, 510, "[DRH NAME Y=510]")
    
    # 2. Intern Name (e.g. Y=401 or Y=390)
    c.drawString(80, 436, "[INTERN NAME Y=436]")
    c.drawString(80, 420, "[INTERN NAME Y=420]")
    
    # 3. Dates/Period (e.g. Y=376 or Y=360)
    c.drawString(350, 395, "[DATE Y=395]")
    c.drawString(350, 380, "[DATE Y=380]")
    
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_grid.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    PdfWriter(output_pdf, trailer=template).write()
    os.remove("temp_grid.pdf")
    
    # Convert to PNG
    doc = fitz.open(output_pdf)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    pix.save(output_png)
    doc.close()
    print(f"Generated grid PNG at: {output_png}")

if __name__ == "__main__":
    test_grid()
