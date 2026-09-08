"""
Precisely find the gap positions by scanning each line.
GAP1: Between "Je soussigne," and "Directeur" on the same line - find the gap end and start
GAP2: After "Monsieur" - find what comes right after
GAP3: After "et ce a compter du" - find the gap start
"""
from PIL import Image

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size

def img_to_pdf_x(img_x):
    return img_x * 612 / w

def img_to_pdf_y(img_y):
    return 792 - img_y * 792 / h

def find_gap_bounds(img, y_pixel, x_start, x_end, threshold=200, min_gap_px=15):
    """Find gaps (white space) between text segments."""
    brightness_row = []
    for x in range(x_start, x_end):
        pixel = img.getpixel((x, y_pixel))
        brightness = (pixel[0] + pixel[1] + pixel[2]) / 3
        brightness_row.append((x, brightness < threshold))  # True = dark = text

    # Find text segments
    segments = []
    in_seg = False
    seg_start = None
    for x, is_dark in brightness_row:
        if is_dark and not in_seg:
            seg_start = x
            in_seg = True
        elif not is_dark and in_seg:
            segments.append((seg_start, x - 1))
            in_seg = False
    if in_seg:
        segments.append((seg_start, brightness_row[-1][0]))

    # Merge nearby segments (within 5px)
    merged = []
    for seg in segments:
        if merged and seg[0] - merged[-1][1] <= 5:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(list(seg))

    # Find gaps between segments that are > min_gap_px
    gaps = []
    for i in range(len(merged) - 1):
        gap_start = merged[i][1] + 1
        gap_end = merged[i + 1][0] - 1
        if gap_end - gap_start >= min_gap_px:
            gaps.append((gap_start, gap_end, gap_end - gap_start))

    return merged, gaps

print("=== GAP 1: Line containing 'Je soussigne, [GAP] Directeur' ===")
print("Scanning y_pixel=281 (pdf_y~521.6):")
segs, gaps = find_gap_bounds(img, 281, 100, 750, threshold=180, min_gap_px=20)
for seg in segs:
    print(f"  Text segment: pixel {seg[0]}-{seg[1]} -> pdf_x {img_to_pdf_x(seg[0]):.1f}-{img_to_pdf_x(seg[1]):.1f}")
for gap in gaps:
    print(f"  GAP: pixel {gap[0]}-{gap[1]} ({gap[2]}px wide) -> pdf_x {img_to_pdf_x(gap[0]):.1f}-{img_to_pdf_x(gap[1]):.1f}")

print("\n=== GAP 2: Line containing 'Monsieur [GAP]' ===")
print("Scanning y_pixel=408 (pdf_y~399.4):")
segs, gaps = find_gap_bounds(img, 408, 100, 720, threshold=180, min_gap_px=20)
for seg in segs:
    print(f"  Text segment: pixel {seg[0]}-{seg[1]} -> pdf_x {img_to_pdf_x(seg[0]):.1f}-{img_to_pdf_x(seg[1]):.1f}")
for gap in gaps:
    print(f"  GAP: pixel {gap[0]}-{gap[1]} ({gap[2]}px wide) -> pdf_x {img_to_pdf_x(gap[0]):.1f}-{img_to_pdf_x(gap[1]):.1f}")

print("\n=== GAP 3: Line containing 'et ce a compter du [GAP]' ===")
print("Scanning y_pixel=455 (pdf_y~354.1):")
segs, gaps = find_gap_bounds(img, 455, 100, 720, threshold=180, min_gap_px=50)
for seg in segs:
    print(f"  Text segment: pixel {seg[0]}-{seg[1]} -> pdf_x {img_to_pdf_x(seg[0]):.1f}-{img_to_pdf_x(seg[1]):.1f}")
for gap in gaps:
    print(f"  GAP: pixel {gap[0]}-{gap[1]} ({gap[2]}px wide) -> pdf_x {img_to_pdf_x(gap[0]):.1f}-{img_to_pdf_x(gap[1]):.1f}")

print("\nAlso scanning adjacent rows for gap3:")
for y_px in [445, 448, 452, 456, 460, 464]:
    segs, gaps = find_gap_bounds(img, y_px, 100, 720, threshold=180, min_gap_px=80)
    pdf_y = img_to_pdf_y(y_px)
    if gaps:
        for gap in gaps:
            print(f"  y_pixel={y_px} (pdf_y={pdf_y:.1f}): GAP pixel {gap[0]}-{gap[1]} -> pdf_x {img_to_pdf_x(gap[0]):.1f}-{img_to_pdf_x(gap[1]):.1f}")
