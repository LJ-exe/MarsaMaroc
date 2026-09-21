"""
Final precise gap fill test — 3 fields only:
1. Directeur RH name: between "Je soussigne," and "Directeur" (pdf_y=521, gap pdf_x 168-310)
2. Intern name: on the line after "Monsieur" (the blank line before "a effectue", pdf_y=401, indented x~170)
3. Start date: after "et ce a compter du" (pdf_y=355, after pdf_x=262)
"""
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def fill_attestation_test(
    nom_directeur="Ahmed Benali",
    nom_stagiaire="Mohammed Addy",
    date_debut="01/06/2026"
):
    img = Image.open("generated_pdfs/extracted_img_0.png").convert("RGB")
    w, h = img.size

    def pdf_to_img_x(pdf_x): return int(pdf_x * w / 612)
    def pdf_to_img_y(pdf_y): return int((792 - pdf_y) * h / 792)

    draw = ImageDraw.Draw(img)

    # Font size: the template body text is ~11pt at 72dpi on 612pt page
    # Rendered at our resolution: scale = h/792
    scale = h / 792
    font_sz = int(11 * scale)

    try:
        font = ImageFont.truetype("arial.ttf", font_sz)
        font_bold = ImageFont.truetype("arialbd.ttf", font_sz)
    except IOError:
        font = ImageFont.load_default()
        font_bold = font

    # Document color: near-black (same as template text)
    text_color = (30, 30, 30)

    # -----------------------------------------------------------------
    # FIELD 1: Directeur RH name
    # Gap is between "Je soussigné," (ends ~pdf_x 167) and "Directeur" (starts ~pdf_x 312)
    # Center name in the gap. Gap width = 312-168 = 144 pdf_pts
    # Place at pdf_y = 521 (baseline of this line)
    # -----------------------------------------------------------------
    x1 = pdf_to_img_x(168)
    y1 = pdf_to_img_y(519)
    draw.text((x1 + 4, y1), nom_directeur, fill=text_color, font=font_bold)

    # -----------------------------------------------------------------
    # FIELD 2: Intern name
    # "Monsieur" is the last word of the line ending at ~pdf_y=376
    # The blank next line (where name goes) is at pdf_y~401
    # Looking at the image: there's a clear indent at the start of the next line
    # The name starts at an indented position around pdf_x=170-220
    # -----------------------------------------------------------------
    # Intern name: the blank indent line below Monsieur that reads "            a effectue..."
    # There is a visible blank centered-ish blank space in the row just ABOVE "a effectue"
    # From the image: that space is around pdf_y=438 at an indent of pdf_x=140
    x_name = pdf_to_img_x(140)
    y_name = pdf_to_img_y(438)
    draw.text((x_name, y_name), nom_stagiaire.upper(), fill=text_color, font=font_bold)

    # -----------------------------------------------------------------
    # FIELD 3: Start date
    # "et ce à compter du" ends at pdf_x=260, pdf_y=355
    # Date goes right after (pdf_x=263, pdf_y=355)
    # -----------------------------------------------------------------
    x_date = pdf_to_img_x(263)
    y_date = pdf_to_img_y(359)

    draw.text((x_date, y_date), date_debut, fill=text_color, font=font_bold)

    img.save("generated_pdfs/test_3fields_final.png")
    print("Saved test_3fields_final.png")

fill_attestation_test()
