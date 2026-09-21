import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
h_page = page.rect.height

print(f"Page size: {page.rect}")

# Extract texts with positions
print("\n--- Texts ---")
words = page.get_text("words")
# Let's rebuild words into lines
lines = {}
for w in words:
    block_line = (w[5], w[6])
    if block_line not in lines:
        lines[block_line] = []
    lines[block_line].append(w)

for bl, w_list in sorted(lines.items()):
    w_list.sort(key=lambda w: w[2])
    text = " ".join(w[4] for w in w_list)
    x0 = min(w[0] for w in w_list)
    y0 = min(w[1] for w in w_list)
    x1 = max(w[2] for w in w_list)
    y1 = max(w[3] for w in w_list)
    print(f"Text: {text!r:50} | Rect: ({x0:.2f}, {y0:.2f}, {x1:.2f}, {y1:.2f}) (RL bottom-up Y baseline: {h_page - y1:.2f})")
