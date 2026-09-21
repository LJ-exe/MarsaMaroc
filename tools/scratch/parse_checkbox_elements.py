import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
h_page = page.rect.height

drawings = page.get_drawings()
print(f"Total drawings: {len(drawings)}")

# Find drawings in the Y range [320, 345] in PyMuPDF top-down coordinates
y_min = 320
y_max = 345

print(f"\nDrawings in Y-range [{y_min}, {y_max}]:")
for idx, draw in enumerate(drawings):
    rect = draw.get("rect")
    if rect.y0 >= y_min and rect.y1 <= y_max:
        w = rect.width
        h = rect.height
        y_bot_up_min = h_page - rect.y1
        y_bot_up_max = h_page - rect.y0
        print(f"Drawing #{idx}: type={draw.get('type')}, rect=Rect({rect.x0:.3f}, {rect.y0:.3f}, {rect.x1:.3f}, {rect.y1:.3f}) (w={w:.3f}, h={h:.3f})")
        print(f"  Bottom-up (ReportLab) Y: [{y_bot_up_min:.3f}, {y_bot_up_max:.3f}]")
        print(f"  Items: {draw.get('items')}")
        print("-" * 50)
