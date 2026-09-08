"""
Scan more precisely the visible blank area for intern name.
From the image, the blank area for Monsieur's name appears BETWEEN:
  - The line "...atteste par la presente que Monsieur" (y_pixel ~376)  
  - The line "                    a effectue un stage..." (y_pixel ~402)
That blank area is around y_pixel 380-394.
Let's scan precisely to find exactly which row in the image is blank between these two.
"""
from PIL import Image

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size

def img_to_pdf_x(x): return x * 612 / w
def img_to_pdf_y(y): return 792 - y * 792 / h

print("Scanning rows 377-400 for blank rows (no/very few dark pixels):")
for y in range(377, 402):
    dark_count = 0
    for x in range(80, 720):
        px = img.getpixel((x, y))
        brightness = (px[0] + px[1] + px[2]) / 3
        if brightness < 160:
            dark_count += 1
    pdf_y = img_to_pdf_y(y)
    if dark_count < 10:
        print(f"  BLANK row: y_pixel={y} (pdf_y={pdf_y:.0f}): {dark_count} dark pixels")
    else:
        print(f"  y_pixel={y} (pdf_y={pdf_y:.0f}): {dark_count} dark pixels")
