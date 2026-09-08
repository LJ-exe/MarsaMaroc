import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
h_page = page.rect.height

print(f"Page size: {page.rect}")

# We want to find rectangles / paths that represent small squares
drawings = page.get_drawings()
squares = []

for idx, draw in enumerate(drawings):
    rect = draw.get("rect")
    w = rect.width
    h = rect.height
    
    # Check if width and height are between 5 and 25
    if 5 <= w <= 25 and 5 <= h <= 25:
        # Also check if it is roughly square (e.g. within 20% aspect ratio) or if it consists of lines forming a square
        if abs(w - h) < 3:
            squares.append((idx, rect, draw))

print(f"Found {len(squares)} potential squares/rectangles in the drawings:")
for idx, rect, draw in squares:
    y_bot_up_min = h_page - rect.y1
    y_bot_up_max = h_page - rect.y0
    print(f"Square Drawing #{idx}:")
    print(f"  Top-down (PyMuPDF) rect: {rect} (w={rect.width:.2f}, h={rect.height:.2f})")
    print(f"  Bottom-up (ReportLab) Y: [{y_bot_up_min:.2f}, {y_bot_up_max:.2f}]")
    print(f"  Fill: {draw.get('fill')}, Stroke: {draw.get('stroke')}")
    print(f"  Items: {draw.get('items')}")
    print("-" * 50)
