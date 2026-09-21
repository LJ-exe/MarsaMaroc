"""
Scan precisely to find each line's text content and gaps.
Focus on the 3 specific lines.
"""
from PIL import Image

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size

def img_to_pdf_x(img_x): return img_x * 612 / w
def img_to_pdf_y(img_y): return 792 - img_y * 792 / h

def scan_row_detailed(img, y_pixel, x_start=80, x_end=730, threshold=160):
    """Scan row and return text segments."""
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
    
    # Merge segments within 8px
    merged = []
    for seg in segments:
        if merged and seg[0] - merged[-1][1] <= 8:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(list(seg))
    return merged

print("=== LINE 1 (Je soussigne... [GAP] Directeur) ===")
print("Looking around pdf_y=521 -> img_y=280")
for y_px in range(276, 290):
    segs = scan_row_detailed(img, y_px)
    if segs:
        pdf_y = img_to_pdf_y(y_px)
        segs_str = [(f"px{s[0]}-{s[1]} pdf_x{img_to_pdf_x(s[0]):.0f}-{img_to_pdf_x(s[1]):.0f}") for s in segs]
        print(f"  y={y_px}(pdf_y={pdf_y:.0f}): {segs_str}")

print("\n=== LINE 2 (Monsieur [GAP]) ===")
print("Likely around pdf_y=385-395 -> img_y=425-435")
for y_px in range(405, 435):
    segs = scan_row_detailed(img, y_px)
    if segs and len(segs) <= 3:  # "Monsieur" line has few text segments
        pdf_y = img_to_pdf_y(y_px)
        segs_str = [(f"px{s[0]}-{s[1]} pdf_x{img_to_pdf_x(s[0]):.0f}-{img_to_pdf_x(s[1]):.0f} ({s[1]-s[0]}px)") for s in segs]
        print(f"  y={y_px}(pdf_y={pdf_y:.0f}): {segs_str}")

print("\n=== LINE 3 (et ce a compter du [GAP]) ===")
print("Looking around pdf_y=354 -> img_y=455")
for y_px in range(440, 470):
    segs = scan_row_detailed(img, y_px)
    if segs:
        pdf_y = img_to_pdf_y(y_px)
        # Find the last segment (after "et ce à compter du")
        if segs:
            last = segs[-1]
            # If last segment ends before x=400, there's a gap after
            if last[1] < 400:
                print(f"  y={y_px}(pdf_y={pdf_y:.0f}): last_text_ends at px{last[1]} pdf_x={img_to_pdf_x(last[1]):.0f}, GAP starts at pdf_x={img_to_pdf_x(last[1]+1):.0f}")
