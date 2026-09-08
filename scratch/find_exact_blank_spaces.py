"""
Find exact positions of blank spaces after specific phrases.
This script focuses on the left part of the page where the main text is located.
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

def scan_horizontal_line(img, y_pixel, x_start=50, x_end=450, threshold=200):
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

# Based on visual inspection of the PDF, the main text is in the left part
# "Je soussigné," is around Y=275-285 in image coordinates
# "Monsieur" is around Y=405-415 in image coordinates
# "à compter du" is around Y=460-470 in image coordinates

draw = ImageDraw.Draw(original_img)

# Scan for "Je soussigné," line (Y=275-285)
best_directeur_line = None
best_directeur_width = 0
for y in range(275, 286):
    segments = scan_horizontal_line(original_img, y, x_start=50, x_end=350)
    total_width = sum(seg[1] - seg[0] for seg in segments)
    if total_width > best_directeur_width:
        best_directeur_width = total_width
        best_directeur_line = (y, segments)

if best_directeur_line:
    y_directeur, segments_directeur = best_directeur_line
    print(f"Directeur RH line: Y={y_directeur}, Width={best_directeur_width}, Segments={len(segments_directeur)}")
    
    # Find the blank space after the text
    if segments_directeur:
        last_seg = segments_directeur[-1]
        blank_x_directeur = last_seg[1] + 15  # Add padding after the text
        pdf_x_directeur, pdf_y_directeur = img_to_pdf(blank_x_directeur, y_directeur)
        print(f"Directeur RH blank space: Image X={blank_x_directeur}, Y={y_directeur} -> PDF X={pdf_x_directeur:.1f}, Y={pdf_y_directeur:.1f}")
        
        img_x_directeur, img_y_directeur = pdf_to_img(pdf_x_directeur, pdf_y_directeur)
        draw.line([img_x_directeur-15, img_y_directeur, img_x_directeur+15, img_y_directeur], fill='red', width=3)
        draw.line([img_x_directeur, img_y_directeur-15, img_x_directeur, img_y_directeur+15], fill='red', width=3)
        draw.text((img_x_directeur+20, img_y_directeur-10), f"Directeur RH\n({pdf_x_directeur:.1f},{pdf_y_directeur:.1f})", fill='red', font=ImageFont.load_default())

# Scan for "Monsieur" line (Y=405-415)
best_stagiaire_line = None
best_stagiaire_width = 0
for y in range(405, 416):
    segments = scan_horizontal_line(original_img, y, x_start=50, x_end=350)
    total_width = sum(seg[1] - seg[0] for seg in segments)
    if total_width > best_stagiaire_width:
        best_stagiaire_width = total_width
        best_stagiaire_line = (y, segments)

if best_stagiaire_line:
    y_stagiaire, segments_stagiaire = best_stagiaire_line
    print(f"Stagiaire line: Y={y_stagiaire}, Width={best_stagiaire_width}, Segments={len(segments_stagiaire)}")
    
    # Find the blank space after the text
    if segments_stagiaire:
        last_seg = segments_stagiaire[-1]
        blank_x_stagiaire = last_seg[1] + 15  # Add padding after the text
        pdf_x_stagiaire, pdf_y_stagiaire = img_to_pdf(blank_x_stagiaire, y_stagiaire)
        print(f"Stagiaire blank space: Image X={blank_x_stagiaire}, Y={y_stagiaire} -> PDF X={pdf_x_stagiaire:.1f}, Y={pdf_y_stagiaire:.1f}")
        
        img_x_stagiaire, img_y_stagiaire = pdf_to_img(pdf_x_stagiaire, pdf_y_stagiaire)
        draw.line([img_x_stagiaire-15, img_y_stagiaire, img_x_stagiaire+15, img_y_stagiaire], fill='green', width=3)
        draw.line([img_x_stagiaire, img_y_stagiaire-15, img_x_stagiaire, img_y_stagiaire+15], fill='green', width=3)
        draw.text((img_x_stagiaire+20, img_y_stagiaire-10), f"Stagiaire\n({pdf_x_stagiaire:.1f},{pdf_y_stagiaire:.1f})", fill='green', font=ImageFont.load_default())

# Scan for "à compter du" line (Y=460-470)
best_date_line = None
best_date_width = 0
for y in range(460, 471):
    segments = scan_horizontal_line(original_img, y, x_start=50, x_end=350)
    total_width = sum(seg[1] - seg[0] for seg in segments)
    if total_width > best_date_width:
        best_date_width = total_width
        best_date_line = (y, segments)

if best_date_line:
    y_date, segments_date = best_date_line
    print(f"Date line: Y={y_date}, Width={best_date_width}, Segments={len(segments_date)}")
    
    # Find the blank space after the text
    if segments_date:
        last_seg = segments_date[-1]
        blank_x_date = last_seg[1] + 15  # Add padding after the text
        pdf_x_date, pdf_y_date = img_to_pdf(blank_x_date, y_date)
        print(f"Date blank space: Image X={blank_x_date}, Y={y_date} -> PDF X={pdf_x_date:.1f}, Y={pdf_y_date:.1f}")
        
        img_x_date, img_y_date = pdf_to_img(pdf_x_date, pdf_y_date)
        draw.line([img_x_date-15, img_y_date, img_x_date+15, img_y_date], fill='blue', width=3)
        draw.line([img_x_date, img_y_date-15, img_x_date, img_y_date+15], fill='blue', width=3)
        draw.text((img_x_date+20, img_y_date-10), f"Date\n({pdf_x_date:.1f},{pdf_y_date:.1f})", fill='blue', font=ImageFont.load_default())

original_img.save("generated_pdfs/exact_blank_spaces.png")
print("\nSaved exact blank spaces to: generated_pdfs/exact_blank_spaces.png")
