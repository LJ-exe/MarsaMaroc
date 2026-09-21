"""
Measure exact text positions from the user's attestation image.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Load the original PDF image
original_img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = original_img.size
print(f"Original image size: {w}x{h}")

def img_to_pdf(img_x, img_y):
    pdf_x = img_x * 612 / w
    pdf_y = 792 - img_y * 792 / h
    return pdf_x, pdf_y

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

# Based on the user's image, I need to find where the text is actually placed
# Let me create a grid to help identify positions

draw = ImageDraw.Draw(original_img)

# Draw a grid with 50px spacing
for x in range(0, w, 50):
    draw.line([x, 0, x, h], fill='lightgray', width=1)
    draw.text((x+5, 10), str(x), fill='gray', font=ImageFont.load_default())

for y in range(0, h, 50):
    draw.line([0, y, w, y], fill='lightgray', width=1)
    draw.text((5, y), str(y), fill='gray', font=ImageFont.load_default())

# Mark the current positions from the code
current_positions = {
    "Directeur RH": {"x": 170, "y": 530},
    "Nom stagiaire": {"x": 210, "y": 395},
    "Date début": {"x": 290, "y": 345}
}

for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill='red', width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill='red', width=3)
    draw.text((img_x+20, img_y-10), f"{label}\n({pos['x']},{pos['y']})", fill='red', font=ImageFont.load_default())

original_img.save("generated_pdfs/attestation_with_grid.png")
print("Saved grid image to: generated_pdfs/attestation_with_grid.png")
print("\nPlease examine the grid image and tell me the exact coordinates")
print("where the text should be placed in the attestation.")
print("\nCurrent positions (red markers):")
for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{label}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")
