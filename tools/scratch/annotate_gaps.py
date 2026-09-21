"""
Pinpoint the 3 exact gap positions with visual annotated crops.
"""
from PIL import Image, ImageDraw

img = Image.open("generated_pdfs/extracted_img_0.png").convert("RGB")
w, h = img.size

def img_to_pdf_x(img_x): return img_x * 612 / w
def img_to_pdf_y(img_y): return 792 - img_y * 792 / h
def pdf_to_img_x(pdf_x): return int(pdf_x * w / 612)
def pdf_to_img_y(pdf_y): return int((792 - pdf_y) * h / 792)

draw = ImageDraw.Draw(img)

# GAP 1: After "Je soussigne," before "Directeur" at pdf_y~521.6, gap is pdf_x 167-311
# The gap center is around pdf_x=168
# The line is at PDF Y=521, so we draw at Y=521
g1_x = pdf_to_img_x(168)
g1_y = pdf_to_img_y(521)
# Draw a red vertical line where we'd insert text
draw.line([(g1_x, g1_y-12), (g1_x, g1_y+2)], fill="red", width=2)
draw.text((g1_x, g1_y-25), f"GAP1 x={g1_x}px pdf_x={img_to_pdf_x(g1_x):.0f} pdf_y={img_to_pdf_y(g1_y):.0f}", fill="red")

# GAP 2: After "Monsieur" at pdf_y~399.4
# We need to find where "Monsieur" ends exactly
# From gap2, the first segment ends at pixel 267 (pdf_x=204.0)
# But that seems to be dots. Let's look at pixel 244 which is just before dots
# Actually looking at the image: "Monsieur" is at far left indented
# Let's check the line y=408 more carefully
# Looking at gap2 result: text at 246-267 means the dots/word at "Monsieur" 
# The word "Monsieur" alone spans from x~130 to x~200 in image pixels
# Wait - the 408 row is actually showing "a effectué un stage d'un mois" not "Monsieur"
# The "Monsieur" row must be higher. Let's find it.

# Looking at the original image: "Monsieur" appears on a line just before "a effectué un stage"
# That line with "a effectué un stage" is at y_pixel~427
# The "Monsieur" line must be around y_pixel~385-395

# GAP 3: "et ce à compter du" ends at pixel 339 (pdf_x=259.0) at y_pixel=455 (pdf_y=354)
# The gap starts right after x=339
g3_x = pdf_to_img_x(260)
g3_y = pdf_to_img_y(354)
draw.line([(g3_x, g3_y-12), (g3_x, g3_y+2)], fill="blue", width=2)
draw.text((g3_x, g3_y+4), f"GAP3 start pdf_x={img_to_pdf_x(g3_x):.0f} pdf_y={img_to_pdf_y(g3_y):.0f}", fill="blue")

img.save("generated_pdfs/annotated_gaps.png")
print("Saved annotated_gaps.png")

# Now let's scan for the "Monsieur" line 
print("\nSearching for the 'Monsieur' line (should have indented text then large gap):")
for y_px in range(370, 430, 2):
    from PIL import Image as PILImage
    img2 = PILImage.open("generated_pdfs/extracted_img_0.png")
    
    # Count dark pixels in this row
    dark_count = 0
    first_dark = None
    last_dark = None
    for x in range(100, 700):
        pixel = img2.getpixel((x, y_px))
        brightness = (pixel[0] + pixel[1] + pixel[2]) / 3
        if brightness < 180:
            dark_count += 1
            if first_dark is None:
                first_dark = x
            last_dark = x
    
    if dark_count > 5:
        pdf_y = img_to_pdf_y(y_px)
        print(f"  y_pixel={y_px} (pdf_y={pdf_y:.1f}): {dark_count} dark pixels, first={first_dark}(pdf_x={img_to_pdf_x(first_dark):.0f}), last={last_dark}(pdf_x={img_to_pdf_x(last_dark):.0f})")
