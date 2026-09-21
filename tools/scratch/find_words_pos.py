import fitz

pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

# Extract characters/words with position
words = page.get_text("words") # list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)

print("--- Words in Y-range [320, 350] ---")
for w in words:
    if 310 <= w[1] <= 350:
        print(f"Word: {w[4]!r:30} | Rect: ({w[0]:.2f}, {w[1]:.2f}, {w[2]:.2f}, {w[3]:.2f})")
