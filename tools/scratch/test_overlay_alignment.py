import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, red, blue, green
from pdfrw import PdfReader, PdfWriter, PageMerge

def make_test_pdf():
    template_path = "pdf/Attestation de stage .pdf"
    output_path = "generated_pdfs/test_alignment.pdf"
    
    # 612 x 792
    c = canvas.Canvas("temp_align.pdf", pagesize=(612, 792))
    
    # Let's draw horizontal grid lines and markers between Y=250 and Y=650
    # Every 10 points, we draw a small line and a label
    c.setFont("Helvetica", 6)
    for y in range(200, 700, 10):
        # Draw a horizontal line from X=50 to X=550
        if y % 50 == 0:
            c.setStrokeColor(red)
            c.setLineWidth(0.5)
            c.drawString(60, y + 2, f"<--- Y={y} --->")
        else:
            c.setStrokeColor(blue)
            c.setLineWidth(0.2)
            c.drawString(80, y + 1, f"y={y}")
        c.line(50, y, 550, y)
        
    # Draw vertical grid lines to find horizontal alignment
    for x in range(50, 560, 50):
        c.setStrokeColor(green)
        c.setLineWidth(0.5)
        c.line(x, 200, x, 700)
        c.drawString(x + 2, 210, f"X={x}")
        
    c.save()
    
    # Merge
    template = PdfReader(template_path)
    overlay = PdfReader("temp_align.pdf")
    PageMerge(template.pages[0]).add(overlay.pages[0]).render()
    
    os.makedirs("generated_pdfs", exist_ok=True)
    PdfWriter(output_path, trailer=template).write()
    os.remove("temp_align.pdf")
    print(f"Alignment PDF written to {output_path}")

if __name__ == "__main__":
    make_test_pdf()
