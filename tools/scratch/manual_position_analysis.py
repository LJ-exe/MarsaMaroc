"""
Manual position analysis based on user's attestation image.
The user provided an image showing the attestation with filled text.
I need to find the exact positions where the text should be placed.
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

# Based on the user's feedback that the attestation is good but not aligned,
# I need to find the exact positions where the text should be placed

# Looking at the typical attestation layout:
# "Je soussigné, [DIRECTEUR NAME] Directeur des Ressources Humaines..."
# The blank space after "Je soussigné," is typically around X=180-200, Y=520-530

# "Monsieur [STAGIAIRE NAME] a effectué un stage..."
# The blank space after "Monsieur" is typically around X=220-240, Y=380-400

# "à compter du [START DATE]..."
# The blank space after "à compter du" is typically around X=300-320, Y=340-360

# Let me try positions based on visual inspection of the PDF
# The user said the attestation is good but not aligned, so I need to adjust

# Based on typical document layout and the text structure:
draw = ImageDraw.Draw(original_img)

# Let me try positions that might be better aligned
# These are educated guesses based on the text structure
test_positions = [
    {"label": "Test 1 - Directeur RH", "x": 185, "y": 525, "color": "blue"},
    {"label": "Test 1 - Nom stagiaire", "x": 225, "y": 390, "color": "blue"},
    {"label": "Test 1 - Date début", "x": 305, "y": 340, "color": "blue"},
]

for pos in test_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill=pos["color"], width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill=pos["color"], width=3)
    draw.text((img_x+20, img_y-10), f"{pos['label']}\n({pos['x']},{pos['y']})", fill=pos["color"], font=ImageFont.load_default())

original_img.save("generated_pdfs/test_positions.png")
print("Saved test positions to: generated_pdfs/test_positions.png")
print("\nTest positions:")
for pos in test_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{pos['label']}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

print("\nPlease examine the test positions image and tell me if these are correct.")
print("If not, please provide the exact coordinates where the text should be placed.")
