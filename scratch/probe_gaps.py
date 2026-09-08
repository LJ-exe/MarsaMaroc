"""
Probe the 3 blank gaps in the attestation template image to find exact pixel positions.
Uses a cropped view of each gap region with rulers.
"""
from PIL import Image, ImageDraw

def crop_with_ruler(img, x1, y1, x2, y2, label, output_path):
    """Crop a region and draw coordinate rulers on it."""
    crop = img.crop((x1, y1, x2, y2))
    # Draw horizontal ruler
    ruler = Image.new("RGB", (x2 - x1, 30), (220, 220, 220))
    draw = ImageDraw.Draw(ruler)
    for px in range(0, x2 - x1, 20):
        real_x = x1 + px
        draw.line([(px, 0), (px, 10)], fill="black")
        draw.text((px, 12), str(real_x), fill="black")
    
    # Stack: ruler + crop
    combined = Image.new("RGB", (x2 - x1, 30 + (y2 - y1)), "white")
    combined.paste(ruler, (0, 0))
    combined.paste(crop, (0, 30))
    
    # Left ruler (Y axis)
    y_ruler = Image.new("RGB", (60, y2 - y1), (220, 220, 220))
    draw_y = ImageDraw.Draw(y_ruler)
    for py in range(0, y2 - y1, 20):
        real_y = y1 + py
        draw_y.line([(0, py), (10, py)], fill="black")
        draw_y.text((12, py), str(real_y), fill="black")
    
    final = Image.new("RGB", (60 + (x2 - x1), 30 + (y2 - y1)), "white")
    final.paste(combined, (60, 0))
    final.paste(y_ruler, (0, 30))
    
    final.save(output_path)
    print(f"Saved: {output_path} (region: x={x1}-{x2}, y={y1}-{y2})")

img = Image.open("generated_pdfs/extracted_img_0.png")
w, h = img.size
print(f"Image size: {w}x{h}")

# Image is 801x823, PDF is 612x792
# Scale factor: img_x = pdf_x * 801/612, img_y = pdf_y * 823/792 (from top)
# img_y_from_top = (792 - pdf_y) * 823 / 792

def pdf_to_img(pdf_x, pdf_y):
    img_x = int(pdf_x * w / 612)
    img_y = int((792 - pdf_y) * h / 792)
    return img_x, img_y

# GAP 1: After "Je soussigné," - before "Directeur des Ressources Humaines"
# Visual inspection: line is around PDF Y=520
# "Je soussigné," ends at approx X=165, gap goes to X=365
gx1, gy1 = pdf_to_img(150, 535)
gx2, gy2 = pdf_to_img(430, 510)
crop_with_ruler(img, gx1, gy1, gx2, gy2, "GAP1_directeur", "generated_pdfs/gap1_directeur.png")

# GAP 2: After "Monsieur" - intern name
# Visual inspection: line is around PDF Y=385
# "Monsieur" ends at approx X=220, gap after that
gx1, gy1 = pdf_to_img(100, 400)
gx2, gy2 = pdf_to_img(400, 370)
crop_with_ruler(img, gx1, gy1, gx2, gy2, "GAP2_nom_stagiaire", "generated_pdfs/gap2_nom_stagiaire.png")

# GAP 3: After "et ce à compter du" - start date
# Visual inspection: line is around PDF Y=350
# "et ce à compter du" ends at approx X=295, gap after that
gx1, gy1 = pdf_to_img(100, 370)
gx2, gy2 = pdf_to_img(550, 340)
crop_with_ruler(img, gx1, gy1, gx2, gy2, "GAP3_date_debut", "generated_pdfs/gap3_date_debut.png")

print("Done. Check generated_pdfs/ for gap images.")
