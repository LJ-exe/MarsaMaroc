"""
Find exact positions of blank spaces in the original PDF by analyzing text regions.
This script scans the PDF image to find where specific phrases end and the blank spaces begin.
"""
from PIL import Image, ImageDraw, ImageFont
import os

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

# Function to scan a horizontal line and find text segments
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

# Based on the text structure, I need to find the Y coordinates of the lines
# containing "Je soussigné,", "Monsieur", and "à compter du"

# Typical Y positions in image coordinates (based on visual inspection):
# "Je soussigné," - around Y=275-285
# "Monsieur" - around Y=410-420
# "à compter du" - around Y=460-470

# Let me scan these regions to find the exact text segments
draw = ImageDraw.Draw(original_img)

# Scan for "Je soussigné," line
y_directeur = 280
segments_directeur = scan_horizontal_line(original_img, y_directeur)
print(f"Segments at Y={y_directeur} (Directeur RH line): {segments_directeur}")

# Scan for "Monsieur" line
y_stagiaire = 415
segments_stagiaire = scan_horizontal_line(original_img, y_stagiaire)
print(f"Segments at Y={y_stagiaire} (Stagiaire line): {segments_stagiaire}")

# Scan for "à compter du" line
y_date = 465
segments_date = scan_horizontal_line(original_img, y_date)
print(f"Segments at Y={y_date} (Date line): {segments_date}")

# Based on the segments, I can estimate where the blank spaces are
# The blank space is typically after the last text segment on each line

# Mark the estimated positions
if segments_directeur:
    last_seg = segments_directeur[-1]
    blank_x_directeur = last_seg[1] + 30  # Add some padding after the text
    pdf_x_directeur, pdf_y_directeur = img_to_pdf(blank_x_directeur, y_directeur)
    print(f"Directeur RH blank space: Image X={blank_x_directeur}, Y={y_directeur} -> PDF X={pdf_x_directeur:.1f}, Y={pdf_y_directeur:.1f}")
    
    img_x_directeur, img_y_directeur = pdf_to_img(pdf_x_directeur, pdf_y_directeur)
    draw.line([img_x_directeur-15, img_y_directeur, img_x_directeur+15, img_y_directeur], fill='red', width=3)
    draw.line([img_x_directeur, img_y_directeur-15, img_x_directeur, img_y_directeur+15], fill='red', width=3)
    draw.text((img_x_directeur+20, img_y_directeur-10), f"Directeur RH\n({pdf_x_directeur:.1f},{pdf_y_directeur:.1f})", fill='red', font=ImageFont.load_default())

if segments_stagiaire:
    last_seg = segments_stagiaire[-1]
    blank_x_stagiaire = last_seg[1] + 30  # Add some padding after the text
    pdf_x_stagiaire, pdf_y_stagiaire = img_to_pdf(blank_x_stagiaire, y_stagiaire)
    print(f"Stagiaire blank space: Image X={blank_x_stagiaire}, Y={y_stagiaire} -> PDF X={pdf_x_stagiaire:.1f}, Y={pdf_y_stagiaire:.1f}")
    
    img_x_stagiaire, img_y_stagiaire = pdf_to_img(pdf_x_stagiaire, pdf_y_stagiaire)
    draw.line([img_x_stagiaire-15, img_y_stagiaire, img_x_stagiaire+15, img_y_stagiaire], fill='green', width=3)
    draw.line([img_x_stagiaire, img_y_stagiaire-15, img_x_stagiaire, img_y_stagiaire+15], fill='green', width=3)
    draw.text((img_x_stagiaire+20, img_y_stagiaire-10), f"Stagiaire\n({pdf_x_stagiaire:.1f},{pdf_y_stagiaire:.1f})", fill='green', font=ImageFont.load_default())

if segments_date:
    last_seg = segments_date[-1]
    blank_x_date = last_seg[1] + 30  # Add some padding after the text
    pdf_x_date, pdf_y_date = img_to_pdf(blank_x_date, y_date)
    print(f"Date blank space: Image X={blank_x_date}, Y={y_date} -> PDF X={pdf_x_date:.1f}, Y={pdf_y_date:.1f}")
    
    img_x_date, img_y_date = pdf_to_img(pdf_x_date, pdf_y_date)
    draw.line([img_x_date-15, img_y_date, img_x_date+15, img_y_date], fill='blue', width=3)
    draw.line([img_x_date, img_y_date-15, img_x_date, img_y_date+15], fill='blue', width=3)
    draw.text((img_x_date+20, img_y_date-10), f"Date\n({pdf_x_date:.1f},{pdf_y_date:.1f})", fill='blue', font=ImageFont.load_default())

original_img.save("generated_pdfs/text_region_analysis.png")
print("\nSaved text region analysis to: generated_pdfs/text_region_analysis.png")
