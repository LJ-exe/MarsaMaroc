"""
Analyze the user's attestation image to find exact text positions.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# The user provided an image showing the attestation with filled text
# I need to analyze this image to find where the text is actually placed

# Since I can't directly access the uploaded image, I'll create a script
# that can be used to analyze any attestation image

# For now, let me use the original PDF image and mark the positions
# based on typical attestation layout

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

# Based on the user's feedback that the attestation is good but not aligned,
# I need to find the exact positions where the text should be placed

# Let me try different positions based on typical attestation layout
# "Je soussigné, [DIRECTEUR NAME] Directeur des Ressources Humaines..."
# The blank space after "Je soussigné," is typically around X=180-200, Y=520-530

# "Monsieur [STAGIAIRE NAME] a effectué un stage..."
# The blank space after "Monsieur" is typically around X=220-240, Y=380-400

# "à compter du [START DATE]..."
# The blank space after "à compter du" is typically around X=300-320, Y=340-360

# Let me create a visual guide with these estimated positions
draw = ImageDraw.Draw(original_img)

# Try position 1 (current)
positions_to_try = [
    {"label": "Current - Directeur RH", "x": 170, "y": 530, "color": "red"},
    {"label": "Current - Nom stagiaire", "x": 210, "y": 395, "color": "red"},
    {"label": "Current - Date début", "x": 290, "y": 345, "color": "red"},
    {"label": "Try 1 - Directeur RH", "x": 185, "y": 525, "color": "blue"},
    {"label": "Try 1 - Nom stagiaire", "x": 225, "y": 390, "color": "blue"},
    {"label": "Try 1 - Date début", "x": 305, "y": 340, "color": "blue"},
    {"label": "Try 2 - Directeur RH", "x": 190, "y": 520, "color": "green"},
    {"label": "Try 2 - Nom stagiaire", "x": 230, "y": 385, "color": "green"},
    {"label": "Try 2 - Date début", "x": 310, "y": 335, "color": "green"},
]

for pos in positions_to_try:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-10, img_y, img_x+10, img_y], fill=pos["color"], width=2)
    draw.line([img_x, img_y-10, img_x, img_y+10], fill=pos["color"], width=2)
    draw.text((img_x+15, img_y-10), f"{pos['label']}\n({pos['x']},{pos['y']})", fill=pos["color"], font=ImageFont.load_default())

original_img.save("generated_pdfs/position_comparison_all.png")
print("Saved position comparison to: generated_pdfs/position_comparison_all.png")
print("\nPlease examine the image and tell me which positions are correct.")
print("\nPositions tried:")
for pos in positions_to_try:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{pos['label']}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")
