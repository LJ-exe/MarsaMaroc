"""
Analyze the user's attestation image to find exact text positions.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# The user uploaded an image - I need to analyze it
# Since I can't directly access the uploaded image, I'll create a script
# that can be used to analyze any attestation image

def analyze_attestation_image(image_path):
    """Analyze an attestation image to find blank space positions."""
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return
    
    img = Image.open(image_path)
    w, h = img.size
    print(f"Image size: {w}x{h}")
    
    # The PDF is 612x792, so we need to convert image coordinates to PDF coordinates
    def img_to_pdf(img_x, img_y):
        pdf_x = img_x * 612 / w
        pdf_y = 792 - img_y * 792 / h
        return pdf_x, pdf_y
    
    # Based on the text structure:
    # "Je soussigné, ............ Directeur des Ressources Humaines..."
    # "Monsieur ............"
    # "à compter du ............"
    
    # I'll create a visual guide with estimated positions
    draw = ImageDraw.Draw(img)
    
    # These are estimated positions - they need to be adjusted based on the actual image
    estimated_positions = {
        "Directeur RH": {"img_x": w*0.3, "img_y": h*0.35},
        "Nom stagiaire": {"img_x": w*0.35, "img_y": h*0.5},
        "Date début": {"img_x": w*0.45, "img_y": h*0.6}
    }
    
    for label, pos in estimated_positions.items():
        pdf_x, pdf_y = img_to_pdf(pos["img_x"], pos["img_y"])
        print(f"{label}: Image X={pos['img_x']:.0f}, Y={pos['img_y']:.0f} -> PDF X={pdf_x:.1f}, Y={pdf_y:.1f}")
        
        # Draw marker
        draw.line([pos["img_x"]-20, pos["img_y"], pos["img_x"]+20, pos["img_y"]], fill='red', width=3)
        draw.line([pos["img_x"], pos["img_y"]-20, pos["img_x"], pos["img_y"]+20], fill='red', width=3)
        draw.text((pos["img_x"]+25, pos["img_y"]-10), label, fill='red')
    
    img.save("analyzed_attestation.png")
    print("Saved analyzed image to: analyzed_attestation.png")

# If the user uploaded an image, it would be in a temporary location
# For now, I'll use the extracted PDF image
analyze_attestation_image("generated_pdfs/extracted_img_0.png")
