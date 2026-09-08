"""
Analyze the PDF text layout to find exact positions of blank spaces.
Based on the user's text: "Je soussigné, ............ Directeur des Ressources Humaines..."
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size
print(f"Image size: {w}x{h}")

def img_to_pdf(img_x, img_y):
    pdf_x = img_x * 612 / w
    pdf_y = 792 - img_y * 792 / h
    return pdf_x, pdf_y

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

# Convert to grayscale for analysis
gray_img = img.convert('L')
gray_array = np.array(gray_img)

def find_text_regions(img_array, y_start, y_end, x_start, x_end, threshold=200):
    """Find dark text regions in a horizontal band."""
    regions = []
    in_text = False
    region_start = None
    
    for y in range(y_start, y_end):
        row_dark = False
        for x in range(x_start, x_end):
            if img_array[y, x] < threshold:
                row_dark = True
                break
        
        if row_dark and not in_text:
            region_start = y
            in_text = True
        elif not row_dark and in_text:
            regions.append((region_start, y - 1))
            in_text = False
    
    if in_text:
        regions.append((region_start, y_end - 1))
    
    return regions

# Based on the text structure provided by the user:
# "Je soussigné, ............ Directeur des Ressources Humaines au port de Casablanca..."
# "atteste par la présente que Monsieur ............ a effectué un stage..."
# "et ce à compter du ............ Cette attestation..."

# Let's search for these specific text patterns by scanning the image

print("\n=== ANALYZING PDF TEXT LAYOUT ===")

# Search for "Je soussigné" line (should be near top)
print("\nSearching for 'Je soussigné' line...")
je_sousigne_y = None
for y in range(100, 300):
    # Check if this row has text
    row_has_text = np.any(gray_array[y, 50:400] < 200)
    if row_has_text:
        # This might be the line - let's check the pattern
        # "Je soussigné," should be followed by a gap then "Directeur"
        row_pixels = gray_array[y, :]
        # Find transitions
        transitions = []
        for x in range(50, 750):
            if x > 50:
                prev_dark = row_pixels[x-1] < 200
                curr_dark = row_pixels[x] < 200
                if prev_dark and not curr_dark:
                    transitions.append(('end', x))
                elif not prev_dark and curr_dark:
                    transitions.append(('start', x))
        
        # Look for pattern: text, gap, text (Je soussigné, gap, Directeur)
        if len(transitions) >= 4:
            # Check if there's a significant gap
            for i in range(0, len(transitions)-2, 2):
                if transitions[i][0] == 'end' and transitions[i+1][0] == 'start':
                    gap_size = transitions[i+1][1] - transitions[i][1]
                    if gap_size > 30:  # Significant gap
                        je_sousigne_y = y
                        pdf_y = img_to_pdf(0, y)[1]
                        print(f"  Found at y={y} (pdf_y={pdf_y:.1f}), gap size={gap_size}px")
                        print(f"  Gap from img_x={transitions[i][1]} to {transitions[i+1][1]}")
                        gap_pdf_x1 = img_to_pdf(transitions[i][1], 0)[0]
                        gap_pdf_x2 = img_to_pdf(transitions[i+1][1], 0)[0]
                        print(f"  Gap in PDF: X={gap_pdf_x1:.1f} to {gap_pdf_x2:.1f}")
                        break
        if je_sousigne_y:
            break

# Search for "Monsieur" line
print("\nSearching for 'Monsieur' line...")
monsieur_y = None
for y in range(300, 500):
    row_has_text = np.any(gray_array[y, 50:400] < 200)
    if row_has_text:
        row_pixels = gray_array[y, :]
        transitions = []
        for x in range(50, 750):
            if x > 50:
                prev_dark = row_pixels[x-1] < 200
                curr_dark = row_pixels[x] < 200
                if prev_dark and not curr_dark:
                    transitions.append(('end', x))
                elif not prev_dark and curr_dark:
                    transitions.append(('start', x))
        
        if len(transitions) >= 2:
            for i in range(0, len(transitions)-1, 2):
                if transitions[i][0] == 'end' and transitions[i+1][0] == 'start':
                    gap_size = transitions[i+1][1] - transitions[i][1]
                    if gap_size > 40:  # Large gap for name
                        monsieur_y = y
                        pdf_y = img_to_pdf(0, y)[1]
                        print(f"  Found at y={y} (pdf_y={pdf_y:.1f}), gap size={gap_size}px")
                        print(f"  Gap from img_x={transitions[i][1]} to {transitions[i+1][1]}")
                        gap_pdf_x1 = img_to_pdf(transitions[i][1], 0)[0]
                        gap_pdf_x2 = img_to_pdf(transitions[i+1][1], 0)[0]
                        print(f"  Gap in PDF: X={gap_pdf_x1:.1f} to {gap_pdf_x2:.1f}")
                        break
        if monsieur_y:
            break

# Search for "à compter du" line
print("\nSearching for 'à compter du' line...")
compter_y = None
for y in range(200, 400):
    row_has_text = np.any(gray_array[y, 50:500] < 200)
    if row_has_text:
        row_pixels = gray_array[y, :]
        transitions = []
        for x in range(50, 750):
            if x > 50:
                prev_dark = row_pixels[x-1] < 200
                curr_dark = row_pixels[x] < 200
                if prev_dark and not curr_dark:
                    transitions.append(('end', x))
                elif not prev_dark and curr_dark:
                    transitions.append(('start', x))
        
        if len(transitions) >= 2:
            for i in range(0, len(transitions)-1, 2):
                if transitions[i][0] == 'end' and transitions[i+1][0] == 'start':
                    gap_size = transitions[i+1][1] - transitions[i][1]
                    if 30 < gap_size < 100:  # Medium gap for date
                        compter_y = y
                        pdf_y = img_to_pdf(0, y)[1]
                        print(f"  Found at y={y} (pdf_y={pdf_y:.1f}), gap size={gap_size}px")
                        print(f"  Gap from img_x={transitions[i][1]} to {transitions[i+1][1]}")
                        gap_pdf_x1 = img_to_pdf(transitions[i][1], 0)[0]
                        gap_pdf_x2 = img_to_pdf(transitions[i+1][1], 0)[0]
                        print(f"  Gap in PDF: X={gap_pdf_x1:.1f} to {gap_pdf_x2:.1f}")
                        break
        if compter_y:
            break

# Draw markers on the image
draw = ImageDraw.Draw(img)

if je_sousigne_y:
    img_x, img_y = pdf_to_img(180, img_to_pdf(0, je_sousigne_y)[1])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill='red', width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill='red', width=3)
    draw.text((img_x+20, img_y-10), "Directeur RH", fill='red', font=ImageFont.load_default())

if monsieur_y:
    img_x, img_y = pdf_to_img(220, img_to_pdf(0, monsieur_y)[1])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill='green', width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill='green', width=3)
    draw.text((img_x+20, img_y-10), "Nom stagiaire", fill='green', font=ImageFont.load_default())

if compter_y:
    img_x, img_y = pdf_to_img(300, img_to_pdf(0, compter_y)[1])
    draw.line([img_x-15, img_y, img_x+15, img_y], fill='blue', width=3)
    draw.line([img_x, img_y-15, img_x, img_y+15], fill='blue', width=3)
    draw.text((img_x+20, img_y-10), "Date début", fill='blue', font=ImageFont.load_default())

img.save("generated_pdfs/attestation_analyzed_layout.png")
print("\nSaved analyzed layout to: generated_pdfs/attestation_analyzed_layout.png")
print("\n=== RECOMMENDED COORDINATES ===")
if je_sousigne_y:
    print(f"Directeur RH: X=180, Y={img_to_pdf(0, je_sousigne_y)[1]:.1f}")
if monsieur_y:
    print(f"Nom stagiaire: X=220, Y={img_to_pdf(0, monsieur_y)[1]:.1f}")
if compter_y:
    print(f"Date début: X=300, Y={img_to_pdf(0, compter_y)[1]:.1f}")
