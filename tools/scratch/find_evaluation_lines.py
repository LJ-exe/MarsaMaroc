import fitz

pdf_path = "pdf/Evaluation stage.pdf"
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
    # w is (x0, y0, x1, y1, "word", block_no, line_no, word_no)
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
    print(f"Text: {text!r:45} | Rect: ({x0:.2f}, {y0:.2f}, {x1:.2f}, {y1:.2f})")

# Find horizontal lines / drawings
print("\n--- Drawings (lines/rectangles) in Y range [300, 500] ---")
drawings = page.get_drawings()
for idx, d in enumerate(drawings):
    r = d['rect']
    # Horizontal line: width > 50, height < 2
    if r.height < 2 and r.width > 30:
        y_bot_up = h_page - r.y1
        print(f"Line #{idx}: X=[{r.x0:.2f}, {r.x1:.2f}], Y={r.y0:.2f} (bottom-up: {y_bot_up:.2f}) | width={r.width:.2f}, height={r.height:.2f}")
