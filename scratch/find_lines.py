import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

drawings = page.get_drawings()
print("--- Vertical lines in Y range [324, 337] ---")
for idx, d in enumerate(drawings):
    r = d['rect']
    # Check if vertical line: height > 5 and width < 2
    if 323 <= r.y0 <= 326 and 335 <= r.y1 <= 338:
        if r.width < 2:
            print(f"Index: {idx:3d} | X: {r.x0:7.3f} to {r.x1:7.3f} | Y: {r.y0:7.3f} to {r.y1:7.3f} | Width: {r.width:5.3f} | Height: {r.height:5.3f}")

print("\n--- Horizontal lines in Y range [324, 337] ---")
for idx, d in enumerate(drawings):
    r = d['rect']
    # Check if horizontal line: width > 5 and height < 2
    if 323 <= r.y0 <= 338:
        if r.height < 2 and r.width > 5:
            print(f"Index: {idx:3d} | X: {r.x0:7.3f} to {r.x1:7.3f} | Y: {r.y0:7.3f} to {r.y1:7.3f} | Width: {r.width:5.3f} | Height: {r.height:5.3f}")
