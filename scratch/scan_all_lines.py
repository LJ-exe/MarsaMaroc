"""
Scan all lines in the PDF to find where text is actually located.
This will help identify the exact Y coordinates of the lines containing
"Je soussigné,", "Monsieur", and "à compter du".
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

def scan_horizontal_line(img, y_pixel, x_start=50, x_end=750, threshold=200):
    """Scan a horizontal line and find text segments (dark pixels)."""
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

# Scan multiple lines to find where text is located
draw = ImageDraw.Draw(original_img)

# Scan a range of Y values to find lines with text
lines_with_text = []

for y in range(200, 600, 5):  # Scan from Y=200 to Y=600 in steps of 5
    segments = scan_horizontal_line(original_img, y)
    if segments:
        total_text_width = sum(seg[1] - seg[0] for seg in segments)
        if total_text_width > 50:  # Only consider lines with significant text
            lines_with_text.append((y, segments, total_text_width))
            # Mark the line
            draw.line([50, y, 750, y], fill='lightgray', width=1)

print(f"Found {len(lines_with_text)} lines with text")

# Find the lines that are most likely to contain the phrases we're looking for
# "Je soussigné," should be in the upper part of the document
# "Monsieur" should be in the middle
# "à compter du" should be in the lower middle

# Sort lines by Y and analyze
lines_with_text.sort(key=lambda x: x[0])

print("\nLines with text (sorted by Y):")
for i, (y, segments, width) in enumerate(lines_with_text[:20]):  # Show first 20 lines
    print(f"Line {i}: Y={y}, Width={width}, Segments={len(segments)}")

# Based on the output, I can identify the likely Y positions
# Let me mark the most likely positions

# Typically:
# "Je soussigné," should be around Y=270-290 in image coordinates
# "Monsieur" should be around Y=410-430 in image coordinates
# "à compter du" should be around Y=460-480 in image coordinates

# Let me scan these specific ranges more precisely
directeur_lines = [(y, segs, w) for y, segs, w in lines_with_text if 260 <= y <= 300]
stagiaire_lines = [(y, segs, w) for y, segs, w in lines_with_text if 400 <= y <= 440]
date_lines = [(y, segs, w) for y, segs, w in lines_with_text if 450 <= y <= 490]

print(f"\nDirecteur RH lines (Y=260-300): {len(directeur_lines)}")
for y, segs, w in directeur_lines:
    print(f"  Y={y}, Width={w}, Segments={segs}")

print(f"\nStagiaire lines (Y=400-440): {len(stagiaire_lines)}")
for y, segs, w in stagiaire_lines:
    print(f"  Y={y}, Width={w}, Segments={segs}")

print(f"\nDate lines (Y=450-490): {len(date_lines)}")
for y, segs, w in date_lines:
    print(f"  Y={y}, Width={w}, Segments={segs}")

# Select the most likely lines (the ones with the most text)
if directeur_lines:
    directeur_line = max(directeur_lines, key=lambda x: x[2])
    print(f"\nSelected Directeur RH line: Y={directeur_line[0]}")
    y_directeur = directeur_line[0]
    segments_directeur = directeur_line[1]
    if segments_directeur:
        last_seg = segments_directeur[-1]
        blank_x_directeur = last_seg[1] + 25
        pdf_x_directeur, pdf_y_directeur = img_to_pdf(blank_x_directeur, y_directeur)
        print(f"Directeur RH blank space: Image X={blank_x_directeur}, Y={y_directeur} -> PDF X={pdf_x_directeur:.1f}, Y={pdf_y_directeur:.1f}")
        
        img_x_directeur, img_y_directeur = pdf_to_img(pdf_x_directeur, pdf_y_directeur)
        draw.line([img_x_directeur-15, img_y_directeur, img_x_directeur+15, img_y_directeur], fill='red', width=3)
        draw.line([img_x_directeur, img_y_directeur-15, img_x_directeur, img_y_directeur+15], fill='red', width=3)
        draw.text((img_x_directeur+20, img_y_directeur-10), f"Directeur RH\n({pdf_x_directeur:.1f},{pdf_y_directeur:.1f})", fill='red', font=ImageFont.load_default())

if stagiaire_lines:
    stagiaire_line = max(stagiaire_lines, key=lambda x: x[2])
    print(f"\nSelected Stagiaire line: Y={stagiaire_line[0]}")
    y_stagiaire = stagiaire_line[0]
    segments_stagiaire = stagiaire_line[1]
    if segments_stagiaire:
        last_seg = segments_stagiaire[-1]
        blank_x_stagiaire = last_seg[1] + 25
        pdf_x_stagiaire, pdf_y_stagiaire = img_to_pdf(blank_x_stagiaire, y_stagiaire)
        print(f"Stagiaire blank space: Image X={blank_x_stagiaire}, Y={y_stagiaire} -> PDF X={pdf_x_stagiaire:.1f}, Y={pdf_y_stagiaire:.1f}")
        
        img_x_stagiaire, img_y_stagiaire = pdf_to_img(pdf_x_stagiaire, pdf_y_stagiaire)
        draw.line([img_x_stagiaire-15, img_y_stagiaire, img_x_stagiaire+15, img_y_stagiaire], fill='green', width=3)
        draw.line([img_x_stagiaire, img_y_stagiaire-15, img_x_stagiaire, img_y_stagiaire+15], fill='green', width=3)
        draw.text((img_x_stagiaire+20, img_y_stagiaire-10), f"Stagiaire\n({pdf_x_stagiaire:.1f},{pdf_y_stagiaire:.1f})", fill='green', font=ImageFont.load_default())

if date_lines:
    date_line = max(date_lines, key=lambda x: x[2])
    print(f"\nSelected Date line: Y={date_line[0]}")
    y_date = date_line[0]
    segments_date = date_line[1]
    if segments_date:
        last_seg = segments_date[-1]
        blank_x_date = last_seg[1] + 25
        pdf_x_date, pdf_y_date = img_to_pdf(blank_x_date, y_date)
        print(f"Date blank space: Image X={blank_x_date}, Y={y_date} -> PDF X={pdf_x_date:.1f}, Y={pdf_y_date:.1f}")
        
        img_x_date, img_y_date = pdf_to_img(pdf_x_date, pdf_y_date)
        draw.line([img_x_date-15, img_y_date, img_x_date+15, img_y_date], fill='blue', width=3)
        draw.line([img_x_date, img_y_date-15, img_x_date, img_y_date+15], fill='blue', width=3)
        draw.text((img_x_date+20, img_y_date-10), f"Date\n({pdf_x_date:.1f},{pdf_y_date:.1f})", fill='blue', font=ImageFont.load_default())

original_img.save("generated_pdfs/scan_all_lines.png")
print("\nSaved scan results to: generated_pdfs/scan_all_lines.png")
