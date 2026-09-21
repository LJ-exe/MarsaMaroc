"""
Find exact positions of the 3 blank spaces in the attestation PDF.
Analyzes the extracted image to determine precise coordinates.
"""
from PIL import Image, ImageDraw, ImageFont

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size
print(f"Image size: {w}x{h}")

# Image is 801x823, PDF is 612x792
# Scale factor: img_x = pdf_x * 801/612, img_y = pdf_y * 823/792 (from top)
# img_y_from_top = (792 - pdf_y) * 823 / 792

def img_to_pdf(img_x, img_y):
    pdf_x = img_x * 612 / w
    pdf_y = 792 - img_y * 792 / h
    return pdf_x, pdf_y

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

# Based on the text provided:
# "Je soussigné, ............ Directeur des Ressources Humaines..."
# "Monsieur ............"
# "à compter du ............"

# Let's scan for these text patterns to find exact positions

def scan_horizontal_line(img, y_pixel, x_start=50, x_end=750, threshold=200):
    """Scan a horizontal line and find text segments."""
    segments = []
    in_text = False
    seg_start = None
    
    for x in range(x_start, x_end):
        pixel = img.getpixel((x, y_pixel))
        brightness = (pixel[0] + pixel[1] + pixel[2]) / 3
        is_dark = brightness < threshold
        
        if is_dark and not in_text:
            seg_start = x
            in_text = True
        elif not is_dark and in_text:
            segments.append((seg_start, x - 1))
            in_text = False
    
    if in_text:
        segments.append((seg_start, x_end - 1))
    
    return segments

# Scan for "Je soussigné" line (should be near top)
print("\n=== Scanning for 'Je soussigné' line ===")
for y_px in range(100, 200):
    segs = scan_horizontal_line(img, y_px)
    if segs:
        total_dark = sum(s[1] - s[0] for s in segs)
        if 100 < total_dark < 300:  # Likely a short line like "Je soussigné,"
            pdf_y = img_to_pdf(0, y_px)[1]
            print(f"y={y_px} (pdf_y={pdf_y:.1f}): {len(segs)} segments, total_dark={total_dark}px")
            for seg in segs:
                pdf_x1, pdf_y1 = img_to_pdf(seg[0], y_px)
                pdf_x2, pdf_y2 = img_to_pdf(seg[1], y_px)
                print(f"  Segment: img_x={seg[0]}-{seg[1]} (pdf_x={pdf_x1:.1f}-{pdf_x2:.1f})")

# Scan for "Monsieur" line (should be in middle)
print("\n=== Scanning for 'Monsieur' line ===")
for y_px in range(350, 450):
    segs = scan_horizontal_line(img, y_px)
    if segs:
        total_dark = sum(s[1] - s[0] for s in segs)
        if 50 < total_dark < 200:  # Likely "Monsieur" only
            pdf_y = img_to_pdf(0, y_px)[1]
            print(f"y={y_px} (pdf_y={pdf_y:.1f}): {len(segs)} segments, total_dark={total_dark}px")
            for seg in segs:
                pdf_x1, pdf_y1 = img_to_pdf(seg[0], y_px)
                pdf_x2, pdf_y2 = img_to_pdf(seg[1], y_px)
                print(f"  Segment: img_x={seg[0]}-{seg[1]} (pdf_x={pdf_x1:.1f}-{pdf_x2:.1f})")

# Scan for "à compter du" line (should be below)
print("\n=== Scanning for 'à compter du' line ===")
for y_px in range(250, 350):
    segs = scan_horizontal_line(img, y_px)
    if segs:
        total_dark = sum(s[1] - s[0] for s in segs)
        if 200 < total_dark < 400:  # Likely "à compter du"
            pdf_y = img_to_pdf(0, y_px)[1]
            print(f"y={y_px} (pdf_y={pdf_y:.1f}): {len(segs)} segments, total_dark={total_dark}px")
            for seg in segs:
                pdf_x1, pdf_y1 = img_to_pdf(seg[0], y_px)
                pdf_x2, pdf_y2 = img_to_pdf(seg[1], y_px)
                print(f"  Segment: img_x={seg[0]}-{seg[1]} (pdf_x={pdf_x1:.1f}-{pdf_x2:.1f})")

# Create visual markers for the 3 gaps
draw = ImageDraw.Draw(img)

# Based on visual inspection and the text structure, let's mark approximate positions
# These will be refined based on the scan results above

# GAP 1: After "Je soussigné," - before "Directeur des Ressources Humaines"
# Approximate position based on typical document layout
gap1_x1, gap1_y1 = pdf_to_img(165, 535)
gap1_x2, gap1_y2 = pdf_to_img(380, 515)
draw.rectangle([gap1_x1, gap1_y1, gap1_x2, gap1_y2], outline='red', width=2)

# GAP 2: After "Monsieur" - intern name
gap2_x1, gap2_y1 = pdf_to_img(200, 400)
gap2_x2, gap2_y2 = pdf_to_img(450, 380)
draw.rectangle([gap2_x1, gap2_y1, gap2_x2, gap2_y2], outline='green', width=2)

# GAP 3: After "à compter du" - start date
gap3_x1, gap3_y1 = pdf_to_img(280, 350)
gap3_x2, gap3_y2 = pdf_to_img(450, 330)
draw.rectangle([gap3_x1, gap3_y1, gap3_x2, gap3_y2], outline='blue', width=2)

img.save("generated_pdfs/attestation_with_markers.png")
print("\nSaved marked image to: generated_pdfs/attestation_with_markers.png")
print("Red box = Directeur RH gap")
print("Green box = Monsieur gap")  
print("Blue box = à compter du gap")
