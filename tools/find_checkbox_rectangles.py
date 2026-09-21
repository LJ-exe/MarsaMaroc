"""
Find exact checkbox rectangle coordinates for Type de Stage in Fiche d'accueil PDF
"""
import os
from pdfrw import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red
from pdfrw import PdfReader, PdfWriter, PageMerge

pdf_path = 'pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf'
pdf = PdfReader(pdf_path)
page = pdf.pages[0]

print(f"Page size: {page.MediaBox}")
print(f"Width: {float(page.MediaBox[2])}, Height: {float(page.MediaBox[3])}")

# Create a test PDF with visual markers to identify checkbox positions
output_dir = 'generated_pdfs'
os.makedirs(output_dir, exist_ok=True)

# Based on the existing code, the Type de stage field is around Y=507.77
# We need to find the exact checkbox positions by visual inspection
# Let's create a test PDF with markers at different positions

temp_overlay = os.path.join(output_dir, 'checkbox_test_overlay.pdf')
c = canvas.Canvas(temp_overlay, pagesize=(595.32, 841.92))

# Draw red markers at estimated positions to help identify exact checkbox locations
c.setFillColor(red)
c.setStrokeColor(red)
c.setLineWidth(0.5)

# Draw a grid of markers around Y=507.77 to find the checkboxes
y_base = 507.77
for x in range(170, 400, 20):
    # Draw a small red circle at each position
    c.circle(x, y_base, 2, fill=1)
    # Draw coordinates text
    c.setFont('Helvetica', 6)
    c.drawString(x, y_base - 10, f"{x}")

# Also draw markers at different Y positions around the expected area
for y in range(490, 530, 10):
    c.circle(180, y, 2, fill=1)
    c.setFont('Helvetica', 6)
    c.drawString(190, y, f"Y={y}")

c.save()

# Merge with template
template_pdf = PdfReader(pdf_path)
overlay_pdf = PdfReader(temp_overlay)
PageMerge(template_pdf.pages[0]).add(overlay_pdf.pages[0]).render()

test_output = os.path.join(output_dir, 'checkbox_position_test.pdf')
PdfWriter(test_output, trailer=template_pdf).write()

print(f"\nTest PDF generated: {test_output}")
print("Open this PDF and identify the exact checkbox positions.")
print("Look for the red markers that align with the checkbox squares.")
print("Then provide the exact x_left, x_right, y_top, y_bottom for each checkbox.")
