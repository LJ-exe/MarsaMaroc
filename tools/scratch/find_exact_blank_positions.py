"""
Find exact positions of blank spaces in the original PDF.
This script analyzes the PDF image to find the exact coordinates
where text should be placed after specific phrases.
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

# Based on visual inspection of the PDF, I need to find the exact positions
# where the blank spaces are located after specific phrases

# "Je soussigné," is at the top of the document
# The blank space should be immediately after the comma

# "Monsieur" is in the middle of the document
# The blank space should be immediately after this word

# "à compter du" is in the middle of the document
# The blank space should be immediately after this phrase

# Let me try to find these positions by scanning the image
# I'll create a visual guide with estimated positions based on the text structure

draw = ImageDraw.Draw(original_img)

# Based on typical document layout and the text structure:
# The PDF is 612x792 points (letter size)

# "Je soussigné," is typically around Y=520-530 in PDF coordinates
# The blank space after "Je soussigné," should be around X=175-185, Y=522-528

# "Monsieur" is typically around Y=385-395 in PDF coordinates
# The blank space after "Monsieur" should be around X=215-225, Y=388-392

# "à compter du" is typically around Y=335-345 in PDF coordinates
# The blank space after "à compter du" should be around X=295-305, Y=338-342

# Let me mark these estimated positions
estimated_positions = [
    {"label": "Directeur RH (after 'Je soussigné,')", "x": 180, "y": 525, "color": "red"},
    {"label": "Nom stagiaire (after 'Monsieur')", "x": 220, "y": 390, "color": "green"},
    {"label": "Date début (after 'à compter du')", "x": 300, "y": 340, "color": "blue"},
]

for pos in estimated_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    draw.line([img_x-20, img_y, img_x+20, img_y], fill=pos["color"], width=3)
    draw.line([img_x, img_y-20, img_x, img_y+20], fill=pos["color"], width=3)
    draw.text((img_x+25, img_y-10), f"{pos['label']}\n({pos['x']},{pos['y']})", fill=pos["color"], font=ImageFont.load_default())

original_img.save("generated_pdfs/estimated_blank_positions.png")
print("Saved estimated blank positions to: generated_pdfs/estimated_blank_positions.png")
print("\nEstimated positions:")
for pos in estimated_positions:
    img_x, img_y = pdf_to_img(pos["x"], pos["y"])
    print(f"{pos['label']}: PDF X={pos['x']}, Y={pos['y']} -> Image X={img_x}, Y={img_y}")

print("\nPlease examine the image and tell me if these positions are correct.")
print("If not, please provide the exact coordinates where the text should be placed.")
