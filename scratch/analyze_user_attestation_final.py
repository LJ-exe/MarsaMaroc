"""
Analyze the user's attestation image to find exact text positions.
The user provided an image showing the attestation with filled text.
I need to find where the text is currently placed and adjust coordinates.
"""
from PIL import Image, ImageDraw, ImageFont

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

# Current positions in the code
current_positions = {
    "Directeur RH": {"x": 190, "y": 528},
    "Nom stagiaire": {"x": 230, "y": 392},
    "Date début": {"x": 310, "y": 342}
}

print("\n=== CURRENT POSITIONS IN CODE ===")
for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{label}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

# Based on the user's feedback that the text is not aligned correctly,
# I need to find the exact positions where the text should be placed
# Looking at the attestation layout:
# "Je soussigné, [DIRECTEUR NAME] Directeur des Ressources Humaines..."
# The blank space after "Je soussigné," should be around X=175-185, Y=520-530

# "Monsieur [STAGIAIRE NAME] a effectué un stage..."
# The blank space after "Monsieur" should be around X=215-225, Y=385-395

# "à compter du [START DATE]..."
# The blank space after "à compter du" should be around X=295-305, Y=340-350

draw = ImageDraw.Draw(original_img)

# Mark current positions in red
for label, pos in current_positions.items():
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill='red', width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill='red', width=3)
    draw.text((img_x+20, img_y-10), f"{label}\n({pos['x']},{pos['y']})", fill='red', font=ImageFont.load_default())

# Try new positions based on better alignment
# These are adjusted based on typical document layout
new_positions = [
    {"label": "New - Directeur RH", "x": 175, "y": 522, "color": "blue"},
    {"label": "New - Nom stagiaire", "x": 215, "y": 388, "color": "blue"},
    {"label": "New - Date début", "x": 295, "y": 338, "color": "blue"},
]

for pos in new_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill=pos["color"], width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill=pos["color"], width=3)
    draw.text((img_x+20, img_y+10), f"{pos['label']}\n({pos['x']},{pos['y']})", fill=pos["color"], font=ImageFont.load_default())

original_img.save("generated_pdfs/final_position_analysis.png")
print("\nSaved final position analysis to: generated_pdfs/final_position_analysis.png")
print("\nNew positions to try:")
for pos in new_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{pos['label']}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")
