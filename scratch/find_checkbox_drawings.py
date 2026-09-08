import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

# Page dimensions
h_page = page.rect.height
print(f"Page height: {h_page}")

drawings = page.get_drawings()
print(f"Total drawings: {len(drawings)}")

# Find drawings in the Y region of Type de Stage (Y between 310 and 370 in top-down coordinates)
# We also want to find their coordinates in both top-down (PyMuPDF) and bottom-up (ReportLab) coordinates.
count = 0
for idx, draw in enumerate(drawings):
    rect = draw.get("rect")
    # check if rect overlaps with Y range [310, 370]
    if rect.y1 >= 315 and rect.y0 <= 365:
        count += 1
        w = rect.width
        h = rect.height
        y_bot_up_min = h_page - rect.y1
        y_bot_up_max = h_page - rect.y0
        print(f"Drawing #{idx}: type={draw.get('type')}, rect={rect} (w={w:.2f}, h={h:.2f})")
        print(f"   Bottom-up (ReportLab) Y: [{y_bot_up_min:.2f}, {y_bot_up_max:.2f}]")
        print(f"   Items: {draw.get('items')}")
        print("-" * 40)

print(f"Found {count} drawings in the Y range [315, 365]")
