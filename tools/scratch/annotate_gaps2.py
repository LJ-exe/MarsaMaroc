"""
Generate a zoomed annotated image showing the 3 gaps with red rectangles.
This will help us confirm positions visually.
"""
from PIL import Image, ImageDraw

img = Image.open("generated_pdfs/extracted_img_0.png").convert("RGB")
w, h = img.size

def pdf_to_img_x(pdf_x): return int(pdf_x * w / 612)
def pdf_to_img_y(pdf_y): return int((792 - pdf_y) * h / 792)
def img_to_pdf_x(img_x): return img_x * 612 / w
def img_to_pdf_y(img_y): return 792 - img_y * 792 / h

draw = ImageDraw.Draw(img)

# Based on findings:
# GAP 1 (Directeur name): Line at pdf_y=521, gap is pdf_x 167-311
# "Je soussigné," text ends at pdf_x~167, "Directeur" starts at pdf_x~312
# Name should be placed at: X=168 (right after "Je soussigné,"), Y=521

# GAP 2 (Stagiaire name): Line at pdf_y=400-406, text is very sparse (only dots from dots line)
# Looking at the image: "Monsieur" is on the same line as the end of previous paragraph
# The scan shows y=406-409 has very sparse dots (this is the "Monsieur" space)
# Actually from the image: "Monsieur" word appears at about the last word of the paragraph
# before "a effectué un stage". The line containing "...atteste par la présente que Monsieur"
# is the y=376 range (dense text line), and "Monsieur" is at far right
# The next line (y~406) shows just dots which ARE the dots placeholder

# Wait - looking at y=406-409: dots at pdf_x 189, 202, 311, 367, 410, 468
# These are likely the underline dots on the "Monsieur _______" line!
# The "Monsieur" word is on the previous full line (y~376) and the blank
# underneath might be an underline row.
# Name should go right after "Monsieur" on the same line ~pdf_y=378, pdf_x~220+

# Actually from the image, I can see:
# "...atteste par la présente que Monsieur" and then next line "   a effectué un stage..."
# The name goes on the SAME line as "Monsieur", starting right after it
# From dense line y=376-380: last text segment at pdf_x 404 (right edge "Monsieur")
# So name starts at pdf_x ~260 (indented area on the Monsieur line)

# Let me draw rectangles showing where we'd place each field:

# GAP 1 - Directeur name: Between "Je soussigné," and "Directeur"
# From scan: gap at pdf_x 167-311, center at pdf_y 521
gap1_x1 = pdf_to_img_x(168)
gap1_x2 = pdf_to_img_x(310)
gap1_y1 = pdf_to_img_y(526)
gap1_y2 = pdf_to_img_y(514)
draw.rectangle([(gap1_x1, gap1_y1), (gap1_x2, gap1_y2)], outline="red", width=3)
draw.text((gap1_x1, gap1_y1-15), "GAP1: Directeur", fill="red")

# GAP 2 - Stagiaire name: After "Monsieur" on y=406-409 (sparse/dots row)
# OR on the "Monsieur" text line. Let's show both options.
# Option A: on same line as Monsieur word (pdf_y~378, after pdf_x~205)
gap2a_x1 = pdf_to_img_x(220)
gap2a_x2 = pdf_to_img_x(540)
gap2a_y1 = pdf_to_img_y(382)
gap2a_y2 = pdf_to_img_y(370)
draw.rectangle([(gap2a_x1, gap2a_y1), (gap2a_x2, gap2a_y2)], outline="green", width=3)
draw.text((gap2a_x1, gap2a_y1-15), "GAP2A: Name on Monsieur line", fill="green")

# Option B: Below Monsieur (separate line with dots)
gap2b_x1 = pdf_to_img_x(100)
gap2b_x2 = pdf_to_img_x(540)
gap2b_y1 = pdf_to_img_y(404)
gap2b_y2 = pdf_to_img_y(396)
draw.rectangle([(gap2b_x1, gap2b_y1), (gap2b_x2, gap2b_y2)], outline="orange", width=3)
draw.text((gap2b_x1, gap2b_y1-15), "GAP2B: Below Monsieur (dots)", fill="orange")

# GAP 3 - Date: After "et ce à compter du" at pdf_y=354-359
# From scan: text ends at pdf_x=259 at y=455 (pdf_y=354)
gap3_x1 = pdf_to_img_x(261)
gap3_x2 = pdf_to_img_x(520)
gap3_y1 = pdf_to_img_y(362)
gap3_y2 = pdf_to_img_y(348)
draw.rectangle([(gap3_x1, gap3_y1), (gap3_x2, gap3_y2)], outline="blue", width=3)
draw.text((gap3_x1, gap3_y2+2), "GAP3: Date", fill="blue")

img.save("generated_pdfs/gaps_annotated2.png")
print("Saved gaps_annotated2.png")
