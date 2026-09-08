"""
Precise probe with finer crops to find exact gap X positions in pixel coordinates.
"""
from PIL import Image, ImageDraw

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

def img_to_pdf(img_x, img_y):
    pdf_x = img_x * 612 / w
    pdf_y = 792 - img_y * 792 / h
    return pdf_x, pdf_y

# Let's zoom into specific regions.
# We know:
# GAP1: "Je soussigné," ends somewhere, then blank, then "Directeur" begins
# Looking at row y=280 (approx pixel)
# GAP2: "Monsieur" ends somewhere, then blank
# Looking at row y=415 (approx pixel)  
# GAP3: "et ce à compter du" ends somewhere, then blank
# Looking at row y=455 (approx pixel)

# Crop single pixel rows to find where text is vs white
from PIL import ImageChops

def find_text_bounds_in_row(img, y_pixel, x_start, x_end, threshold=200):
    """Scan a horizontal row to find bounds of dark pixels (text)."""
    row_pixels = []
    for x in range(x_start, x_end):
        pixel = img.getpixel((x, y_pixel))
        # In RGB: dark = text, light = white
        brightness = (pixel[0] + pixel[1] + pixel[2]) / 3
        row_pixels.append((x, brightness))
    
    # Find segments of dark pixels (text)
    in_text = False
    segments = []
    seg_start = None
    
    for x, brightness in row_pixels:
        is_dark = brightness < threshold
        if is_dark and not in_text:
            seg_start = x
            in_text = True
        elif not is_dark and in_text:
            segments.append((seg_start, x - 1))
            in_text = False
    if in_text:
        segments.append((seg_start, row_pixels[-1][0]))
    
    return segments

# GAP 1: Row around y_pixel=280, looking for text and gap between them
# "Je soussigné," is at start, then blank, then "Directeur..."
print("=== GAP 1: Je soussigné, [GAP] Directeur ===")
for y_px in [275, 278, 281, 284]:
    segs = find_text_bounds_in_row(img, y_px, 100, 750)
    pdf_y = img_to_pdf(0, y_px)[1]
    print(f"  y_pixel={y_px} (pdf_y≈{pdf_y:.1f}): {segs}")

# GAP 2: "Monsieur [GAP]" and name goes here
print("\n=== GAP 2: Monsieur [GAP] ===")
for y_px in [408, 412, 416, 420]:
    segs = find_text_bounds_in_row(img, y_px, 100, 700)
    pdf_y = img_to_pdf(0, y_px)[1]
    print(f"  y_pixel={y_px} (pdf_y≈{pdf_y:.1f}): {segs}")

# GAP 3: "et ce à compter du [GAP]"
print("\n=== GAP 3: et ce à compter du [GAP] ===")
for y_px in [450, 455, 460, 465]:
    segs = find_text_bounds_in_row(img, y_px, 100, 750)
    pdf_y = img_to_pdf(0, y_px)[1]
    print(f"  y_pixel={y_px} (pdf_y≈{pdf_y:.1f}): {segs}")
