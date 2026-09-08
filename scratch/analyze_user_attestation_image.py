"""
Analyze the user's attestation image to find exact text positions.
The user provided an image showing the attestation with filled text.
I need to find the exact positions where the text should be placed.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# The user provided an image - I need to analyze it
# Since the image was uploaded, I'll create a script that can be used
# to analyze any attestation image

# For now, let me use the original PDF image and mark positions
# based on the user's feedback that the attestation is good but not aligned

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

# Based on the user's feedback, I need to find the exact positions
# Let me try positions that might be better aligned

# Looking at the text structure:
# "Je soussigné, [DIRECTEUR NAME] Directeur des Ressources Humaines..."
# The blank space after "Je soussigné," should be around X=185-195, Y=525-535

# "Monsieur [STAGIAIRE NAME] a effectué un stage..."
# The blank space after "Monsieur" should be around X=225-235, Y=390-400

# "à compter du [START DATE]..."
# The blank space after "à compter du" should be around X=305-315, Y=340-350

draw = ImageDraw.Draw(original_img)

# Try positions based on better alignment
adjusted_positions = [
    {"label": "Adjusted - Directeur RH", "x": 190, "y": 528, "color": "green"},
    {"label": "Adjusted - Nom stagiaire", "x": 230, "y": 392, "color": "green"},
    {"label": "Adjusted - Date début", "x": 310, "y": 342, "color": "green"},
]

for pos in adjusted_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill=pos["color"], width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill=pos["color"], width=3)
    draw.text((img_x+20, img_y-10), f"{pos['label']}\n({pos['x']},{pos['y']})", fill=pos["color"], font=ImageFont.load_default())

original_img.save("generated_pdfs/adjusted_positions.png")
print("Saved adjusted positions to: generated_pdfs/adjusted_positions.png")
print("\nAdjusted positions:")
for pos in adjusted_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{pos['label']}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

print("\nPlease examine the adjusted positions image and tell me if these are correct.")
print("If not, please provide the exact coordinates where the text should be placed.")
