"""
Find the Monsieur line precisely by looking at lines with only "Monsieur" text (indented).
Also verify: the Monsieur line likely has:
  - "Monsieur" text at some x position (indented)
  - then a large blank gap
  - the line should be sparse (not wall-to-wall text)
"""
from PIL import Image

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size

def img_to_pdf_x(img_x): return img_x * 612 / w
def img_to_pdf_y(img_y): return 792 - img_y * 792 / h

def scan_row(img, y_pixel, x_start=80, x_end=730, threshold=160):
    in_text = False
    seg_start = None
    segments = []
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
    
    merged = []
    for seg in segments:
        if merged and seg[0] - merged[-1][1] <= 8:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(list(seg))
    return merged

# The full attestation body is between:
# "atteste par la presente que Monsieur" line (around y_pixel=370-380)
# "a effectue un stage" line (around y_pixel=398-408)
# "d'Information, et ce a compter du" line (around y_pixel=450-460)

# Let's look at the region 382-396 more carefully - what is there?
print("=== Scanning 380-430 for Monsieur line ===")
for y_px in range(380, 430):
    segs = scan_row(img, y_px)
    if segs:
        pdf_y = img_to_pdf_y(y_px)
        # Only print rows with 1-3 segments AND large gap (Monsieur + gap)
        if len(segs) >= 1:
            total_dark = sum(s[1]-s[0] for s in segs)
            if total_dark < 200:  # Sparse line = only "Monsieur" or few words
                segs_str = [(f"px{s[0]}-{s[1]} (pdf_x{img_to_pdf_x(s[0]):.0f}-{img_to_pdf_x(s[1]):.0f})") for s in segs]
                print(f"  y={y_px}(pdf_y={pdf_y:.0f}) [{total_dark}px dark]: {segs_str}")

# Also let's look at what happens at y_pixel 404-412 - dots from 'Monsieur'?
print("\n=== Scanning 402-415 detailed ===")
for y_px in range(402, 415):
    segs = scan_row(img, y_px)
    if segs:
        pdf_y = img_to_pdf_y(y_px)
        segs_str = [(f"px{s[0]}-{s[1]} (pdf_x{img_to_pdf_x(s[0]):.0f}-{img_to_pdf_x(s[1]):.0f})") for s in segs]
        print(f"  y={y_px}(pdf_y={pdf_y:.0f}): {segs_str}")
