"""
Simple position check without numpy.
"""
from PIL import Image, ImageDraw, ImageFont

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

# Based on visual inspection of the PDF and the text provided by the user:
# "Je soussigné, ............ Directeur des Ressources Humaines..."
# "atteste par la présente que Monsieur ............ a effectué un stage..."
# "et ce à compter du ............ Cette attestation..."

# Let's use the positions from the probe_gaps.py script which seemed reasonable
# and adjust based on the user's feedback that alignment needs to be perfect

# Current positions in code
current_positions = {
    "Directeur RH": {"x": 165, "y": 525},
    "Nom stagiaire": {"x": 200, "y": 390},
    "Date début": {"x": 280, "y": 340}
}

print("\n=== CURRENT POSITIONS IN CODE ===")
for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{label}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

# Based on typical document layout and the text structure,
# let's try adjusted positions that might align better:
adjusted_positions = {
    "Directeur RH": {"x": 170, "y": 530},  # Slightly right and down
    "Nom stagiaire": {"x": 210, "y": 395},  # Slightly right and down
    "Date début": {"x": 290, "y": 345}     # Slightly right and down
}

print("\n=== ADJUSTED POSITIONS ===")
for label, pos in adjusted_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{label}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

# Draw both current and adjusted positions for comparison
draw = ImageDraw.Draw(img)

# Current positions in red
for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-10, img_y, img_x+10, img_y], fill='red', width=2)
    draw.line([img_x, img_y-10, img_x, img_y+10], fill='red', width=2)
    draw.text((img_x+15, img_y-10), f"{label} (current)", fill='red', font=ImageFont.load_default())

# Adjusted positions in blue
for label, pos in adjusted_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-10, img_y, img_x+10, img_y], fill='blue', width=2)
    draw.line([img_x, img_y-10, img_x, img_y+10], fill='blue', width=2)
    draw.text((img_x+15, img_y+10), f"{label} (adjusted)", fill='blue', font=ImageFont.load_default())

img.save("generated_pdfs/position_comparison.png")
print("\nSaved position comparison to: generated_pdfs/position_comparison.png")
print("Red = current positions, Blue = adjusted positions")
print("\n=== RECOMMENDED CODE CHANGES ===")
print("Update generer_attestation_pdf with these coordinates:")
for label, pos in adjusted_positions.items():
    print(f"  {label}: X={pos['x']}, Y={pos['y']}")
