import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def draw_on_template_image(image_path, output_path):
    img = Image.open(image_path)
    # Convert to RGB to ensure we can draw colored text
    img = img.convert("RGB")
    w, h = img.size
    
    # Mapping functions: PDF points (612 x 792) to Pixels (w x h)
    def map_x(x_pdf):
        return int(x_pdf * w / 612)
        
    def map_y(y_pdf):
        return int((792 - y_pdf) * h / 792)

    draw = ImageDraw.Draw(img)
    
    # Try to load a clean sans-serif font or default
    try:
        # On Windows, Arial is always available
        font_regular = ImageFont.truetype("arial.ttf", int(9.5 * h / 792))
        font_bold = ImageFont.truetype("arialbd.ttf", int(9.5 * h / 792))
        font_title_bold = ImageFont.truetype("arialbd.ttf", int(10 * h / 792))
    except IOError:
        font_regular = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_title_bold = ImageFont.load_default()
        
    # Brand color
    brand_color = (0, 26, 77) # #001a4d
    
    # White masking helper
    def white_mask(x_pdf, y_pdf, w_pdf, h_pdf):
        px = map_x(x_pdf)
        py = map_y(y_pdf + h_pdf) # Y is inverted in pixels (top-left)
        pw = map_x(x_pdf + w_pdf) - px
        ph = map_y(y_pdf) - py
        draw.rectangle([px, py, px + pw, py + ph], fill="white")

    # 1. Signatory Name (Directeur RH) on Line 1
    # Y_pdf=520, X_pdf=175
    draw.text((map_x(175), map_y(520)), "Ahmed Benali,", fill=brand_color, font=font_title_bold)

    # 2. Cover the pre-printed specific text in Line 6 and Line 7
    # Line 6 is Y=385, Line 7 is Y=350 (pre-printed baselines)
    white_mask(75, 376, 470, 18)
    white_mask(75, 341, 470, 18)

    # 3. Line 6: Monsieur ADDY MOHAMMED, étudiant de l'établissement ENSAS (Spécialité : Génie Logiciel),
    cx = map_x(85)
    cy = map_y(385)
    
    draw.text((cx, cy), "Monsieur ", fill=brand_color, font=font_regular)
    cx += draw.textlength("Monsieur ", font=font_regular)
    
    draw.text((cx, cy), "ADDY MOHAMMED", fill=brand_color, font=font_bold)
    cx += draw.textlength("ADDY MOHAMMED", font=font_bold)
    
    draw.text((cx, cy), ", étudiant de l'établissement ", fill=brand_color, font=font_regular)
    cx += draw.textlength(", étudiant de l'établissement ", font=font_regular)
    
    draw.text((cx, cy), "ENSAS", fill=brand_color, font=font_bold)
    cx += draw.textlength("ENSAS", font=font_bold)
    
    draw.text((cx, cy), " (Spécialité : ", fill=brand_color, font=font_regular)
    cx += draw.textlength(" (Spécialité : ", font=font_regular)
    
    draw.text((cx, cy), "Génie Logiciel", fill=brand_color, font=font_bold)
    cx += draw.textlength("Génie Logiciel", font=font_bold)
    
    draw.text((cx, cy), "),", fill=brand_color, font=font_regular)

    # Line 6.5: a effectué un stage de deux mois au sein de la Division Systèmes d'Information,
    cx = map_x(85)
    cy = map_y(358)
    
    draw.text((cx, cy), "a effectué un stage ", fill=brand_color, font=font_regular)
    cx += draw.textlength("a effectué un stage ", font=font_regular)
    
    draw.text((cx, cy), "de deux mois", fill=brand_color, font=font_bold)
    cx += draw.textlength("de deux mois", font=font_bold)
    
    draw.text((cx, cy), " au sein de ", fill=brand_color, font=font_regular)
    cx += draw.textlength(" au sein de ", font=font_regular)
    
    draw.text((cx, cy), "la Division Systèmes d'Information", fill=brand_color, font=font_bold)
    cx += draw.textlength("la Division Systèmes d'Information", font=font_bold)
    
    draw.text((cx, cy), ",", fill=brand_color, font=font_regular)

    # Line 7: et ce du 01/06/2026 au 31/07/2026.
    cx = map_x(85)
    cy = map_y(330)
    
    draw.text((cx, cy), "et ce du ", fill=brand_color, font=font_regular)
    cx += draw.textlength("et ce du ", font=font_regular)
    
    draw.text((cx, cy), "01/06/2026 au 31/07/2026", fill=brand_color, font=font_bold)
    cx += draw.textlength("01/06/2026 au 31/07/2026", font=font_bold)
    
    draw.text((cx, cy), ".", fill=brand_color, font=font_regular)

    # 4. Town & Date above signatures
    current_date = datetime.now().strftime("%d/%m/%Y")
    draw.text((map_x(350), map_y(205)), f"Fait à Casablanca, le {current_date}", fill=brand_color, font=font_regular)

    # 5. Names of signatories
    draw.text((map_x(350), map_y(155)), "Ahmed Benali", fill=brand_color, font=font_bold)
    draw.text((map_x(80), map_y(155)), "Responsable Stage", fill=brand_color, font=font_bold)

    img.save(output_path)
    print(f"Filled image written to {output_path}")

if __name__ == "__main__":
    draw_on_template_image("generated_pdfs/extracted_img_0.png", "generated_pdfs/test_attestation_image_filled.png")
