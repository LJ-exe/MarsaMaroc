"""
Verify exact positions of blank spaces in the attestation PDF.
Create a test PDF to check alignment.
"""
from PIL import Image, ImageDraw, ImageFont
import os

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size
print(f"Image size: {w}x{h}")

def img_to_pdf(img_x, img_y):
    pdf_x = img_x * 612 / w
    pdf_y = 792 - img_y * 792 / h
    return pdf_x, pdf_y

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

# Current positions in the code
current_positions = {
    "Directeur RH": {"x": 165, "y": 525},
    "Nom stagiaire": {"x": 200, "y": 390},
    "Date début": {"x": 280, "y": 340}
}

print("\n=== CURRENT POSITIONS IN CODE ===")
for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{label}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

# Draw markers at current positions
draw = ImageDraw.Draw(img)

for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    # Draw a small cross at the position
    draw.line([img_x-10, img_y, img_x+10, img_y], fill='red', width=2)
    draw.line([img_x, img_y-10, img_x, img_y+10], fill='red', width=2)
    # Draw label
    draw.text((img_x+15, img_y-10), label, fill='red')

img.save("generated_pdfs/attestation_current_positions.png")
print("\nSaved image with current position markers to: generated_pdfs/attestation_current_positions.png")
print("Please check if the red markers align with the blank spaces in the PDF.")
