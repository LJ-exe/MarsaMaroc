import fitz

pdf_path = "pdf/Evaluation stage.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
h_page = page.rect.height

words = page.get_text("words")

# Group words by Y coordinate
for w in words:
    # Look at header lines Y: 140 to 250
    if 140 <= w[1] <= 250:
        rl_y_bottom = h_page - w[3]
        print(f"Word: {w[4]!r:25} | X: [{w[0]:.2f}, {w[2]:.2f}] | Y: [{w[1]:.2f}, {w[3]:.2f}] (RL bottom: {rl_y_bottom:.2f})")
