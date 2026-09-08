import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

# Page size
print(f"Page rect: {page.rect}")
print(f"Page rotation: {page.rotation}")

# Get all drawings
drawings = page.get_drawings()
print(f"Total drawings: {len(drawings)}")

# Let's filter drawings that are small squares/rectangles
# Checkboxes are usually small squares, e.g. width and height around 8-15, and width == height
for idx, draw in enumerate(drawings):
    # draw is a dictionary describing a path
    # e.g., {'type': 'el', 'rect': Rect(...), 'fill': ..., 'stroke': ...}
    t = draw.get("type")
    rect = draw.get("rect")
    fill = draw.get("fill")
    stroke = draw.get("stroke")
    items = draw.get("items", [])
    
    # Let's print all small rectangles/squares or lines that might make up a square
    w = rect.width
    h = rect.height
    
    # Print elements that look like checkboxes (small, roughly square)
    # or print all paths to see what's there
    if w > 0 and h > 0:
        print(f"Drawing #{idx}: type={t}, rect={rect} (w={w:.2f}, h={h:.2f}), stroke={stroke}, fill={fill}, items_len={len(items)}")

# Also look for texts in the page
print("\n--- Texts and their positions ---")
text_page = page.get_text("blocks")
for block in text_page:
    # block is (x0, y0, x1, y1, "text", block_no, block_type)
    print(f"Text block: {block[4].strip()!r} at rect: ({block[0]:.2f}, {block[1]:.2f}, {block[2]:.2f}, {block[3]:.2f})")
