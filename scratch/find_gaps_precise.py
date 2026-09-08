"""
Find precise positions of the 3 blank spaces in the attestation PDF.
Analyzes the extracted image to determine exact coordinates for text placement.
"""
from PIL import Image, ImageDraw, ImageFont

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size
print(f"Image size: {w}x{h}")

# Image is 801x823, PDF is 612x792
def img_to_pdf(img_x, img_y):
    pdf_x = img_x * 612 / w
    pdf_y = 792 - img_y * 792 / h
    return pdf_x, pdf_y

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

def find_blank_gap(img, y_start, y_end, x_start, x_end, threshold=200):
    """Find the blank gap (white space) in a horizontal region."""
    for y in range(y_start, y_end):
        row_pixels = []
        for x in range(x_start, x_end):
            pixel = img.getpixel((x, y))
            brightness = (pixel[0] + pixel[1] + pixel[2]) / 3
            is_dark = brightness < threshold
            row_pixels.append(is_dark)
        
        # Find transitions from dark to light (end of text) and light to dark (start of next text)
        transitions = []
        for i in range(1, len(row_pixels)):
            if row_pixels[i-1] and not row_pixels[i]:  # dark to light
                transitions.append(('end', i))
            elif not row_pixels[i-1] and row_pixels[i]:  # light to dark
                transitions.append(('start', i))
        
        if len(transitions) >= 2:
            # Find the largest gap between end and start
            max_gap = 0
            gap_start = 0
            gap_end = 0
            for i in range(0, len(transitions)-1, 2):
                if transitions[i][0] == 'end' and transitions[i+1][0] == 'start':
                    gap_size = transitions[i+1][1] - transitions[i][1]
                    if gap_size > max_gap:
                        max_gap = gap_size
                        gap_start = transitions[i][1]
                        gap_end = transitions[i+1][1]
            
            if max_gap > 20:  # Only consider significant gaps
                pdf_y = img_to_pdf(0, y)[1]
                pdf_x_start = img_to_pdf(gap_start, 0)[0]
                pdf_x_end = img_to_pdf(gap_end, 0)[0]
                return pdf_x_start, pdf_x_end, pdf_y, y
    
    return None

# Based on the text structure, let's search for the 3 gaps in specific regions

# GAP 1: After "Je soussigné," - before "Directeur des Ressources Humaines"
# This should be near the top of the document
print("\n=== Searching for GAP 1 (Directeur RH) ===")
# Search in region where "Je soussigné" should be (top of document)
gap1 = find_blank_gap(img, 100, 200, 150, 400)
if gap1:
    print(f"GAP 1 found: PDF X={gap1[0]:.1f}-{gap1[1]:.1f}, PDF Y={gap1[2]:.1f} (img_y={gap1[3]})")
else:
    print("GAP 1 not found in automatic search, using manual estimation")
    # Manual estimation based on typical layout
    gap1_x1, gap1_y1 = pdf_to_img(165, 535)
    gap1_x2, gap1_y2 = pdf_to_img(380, 515)
    print(f"Manual GAP 1: PDF X=165-380, PDF Y=515-535")

# GAP 2: After "Monsieur" - intern name
# This should be in the middle of the document
print("\n=== Searching for GAP 2 (Nom stagiaire) ===")
gap2 = find_blank_gap(img, 350, 450, 180, 500)
if gap2:
    print(f"GAP 2 found: PDF X={gap2[0]:.1f}-{gap2[1]:.1f}, PDF Y={gap2[2]:.1f} (img_y={gap2[3]})")
else:
    print("GAP 2 not found in automatic search, using manual estimation")
    gap2_x1, gap2_y1 = pdf_to_img(200, 400)
    gap2_x2, gap2_y2 = pdf_to_img(450, 380)
    print(f"Manual GAP 2: PDF X=200-450, PDF Y=380-400")

# GAP 3: After "à compter du" - start date
# This should be below the middle
print("\n=== Searching for GAP 3 (Date début) ===")
gap3 = find_blank_gap(img, 250, 350, 250, 500)
if gap3:
    print(f"GAP 3 found: PDF X={gap3[0]:.1f}-{gap3[1]:.1f}, PDF Y={gap3[2]:.1f} (img_y={gap3[3]})")
else:
    print("GAP 3 not found in automatic search, using manual estimation")
    gap3_x1, gap3_y1 = pdf_to_img(280, 350)
    gap3_x2, gap3_y2 = pdf_to_img(450, 330)
    print(f"Manual GAP 3: PDF X=280-450, PDF Y=330-350")

# Create a visual analysis with the estimated positions
draw = ImageDraw.Draw(img)

# Use the positions from the probe_gaps.py script which seemed more accurate
# GAP 1: After "Je soussigné," - before "Directeur des Ressources Humaines"
gx1, gy1 = pdf_to_img(165, 535)
gx2, gy2 = pdf_to_img(380, 515)
draw.rectangle([gx1, gy1, gx2, gy2], outline='red', width=3)
draw.text((gx1, gy1-15), "GAP 1: Directeur RH", fill='red')

# GAP 2: After "Monsieur" - intern name
gx1, gy1 = pdf_to_img(200, 400)
gx2, gy2 = pdf_to_img(450, 380)
draw.rectangle([gx1, gy1, gx2, gy2], outline='green', width=3)
draw.text((gx1, gy1-15), "GAP 2: Nom stagiaire", fill='green')

# GAP 3: After "à compter du" - start date
gx1, gy1 = pdf_to_img(280, 350)
gx2, gy2 = pdf_to_img(450, 330)
draw.rectangle([gx1, gy1, gx2, gy2], outline='blue', width=3)
draw.text((gx1, gy1-15), "GAP 3: Date début", fill='blue')

img.save("generated_pdfs/attestation_gaps_analysis.png")
print("\nSaved analysis image to: generated_pdfs/attestation_gaps_analysis.png")

# Print recommended coordinates for the generer_attestation_pdf function
print("\n=== RECOMMENDED COORDINATES FOR generer_attestation_pdf ===")
print("GAP 1 (Directeur RH):")
print("  X start: 165")
print("  Y baseline: 525")
print("  Max width: 215")
print()
print("GAP 2 (Nom stagiaire):")
print("  X start: 200")  
print("  Y baseline: 390")
print("  Max width: 250")
print()
print("GAP 3 (Date début):")
print("  X start: 280")
print("  Y baseline: 340")
print("  Max width: 170")
