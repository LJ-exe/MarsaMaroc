import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, blue
from pdfrw import PdfReader, PdfWriter, PageMerge

def draw_grid_on_pdf(template_path, output_filename, pagesize):
    # pagesize is a tuple: (width, height)
    width, height = pagesize
    temp_overlay = "temp_grid_overlay.pdf"
    
    c = canvas.Canvas(temp_overlay, pagesize=pagesize)
    c.setFont("Helvetica", 8)
    
    # Draw horizontal lines every 50 points
    c.setStrokeColor(red)
    c.setLineWidth(0.5)
    for y in range(0, int(height), 50):
        c.line(0, y, width, y)
        c.drawString(5, y + 2, f"Y={y}")
        
    # Draw vertical lines every 50 points
    c.setStrokeColor(blue)
    for x in range(0, int(width), 50):
        c.line(x, 0, x, height)
        c.drawString(x + 2, 5, f"X={x}")
        
    c.save()
    
    # Merge overlay with template
    template_pdf = PdfReader(template_path)
    overlay_pdf = PdfReader(temp_overlay)
    
    PageMerge(template_pdf.pages[0]).add(overlay_pdf.pages[0]).render()
    
    os.makedirs("generated_pdfs", exist_ok=True)
    out_path = os.path.join("generated_pdfs", output_filename)
    PdfWriter(out_path, trailer=template_pdf).write()
    
    try:
        os.remove(temp_overlay)
    except Exception:
        pass
    print(f"Grid PDF written to {out_path}")

if __name__ == "__main__":
    draw_grid_on_pdf("pdf/Evaluation stage.pdf", "grid_eval.pdf", (841.92, 595.32))
    draw_grid_on_pdf("pdf/Attestation de stage .pdf", "grid_attestation.pdf", (612, 792))
