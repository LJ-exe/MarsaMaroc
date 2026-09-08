import os
from PIL import Image, ImageDraw, ImageFont

def slice_image(image_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    img = Image.open(image_path)
    w, h = img.size
    
    # We want to slice from Y=200 to Y=700 (in pixel coordinates)
    # The PDF height is 792, and the image height is 823.
    # So Y_pdf = 792 - (Y_pixel * 792 / 823)
    # Let's slice every 40 pixels of the image
    step = 40
    for y_start in range(150, 750, step):
        y_end = min(y_start + step, h)
        box = (0, y_start, w, y_end)
        crop_img = img.crop(box)
        
        # Add a label showing the pixel range and estimated PDF Y-coordinate
        # Y_pdf_start = 792 - (y_start * 792 / h)
        # Y_pdf_end = 792 - (y_end * 792 / h)
        # Let's draw this on the left of the cropped image
        draw_img = Image.new("RGB", (w + 120, step), "white")
        draw_img.paste(crop_img, (120, 0))
        
        draw = ImageDraw.Draw(draw_img)
        # Draw text
        pdf_y_mid = 792 - ((y_start + y_end)/2 * 792 / h)
        text = f"PX: {y_start}-{y_end}\nPDF Y: ~{pdf_y_mid:.1f}"
        draw.text((5, 5), text, fill="black")
        
        filename = f"slice_{y_start}_{y_end}.png"
        filepath = os.path.join(output_dir, filename)
        draw_img.save(filepath)
        print(f"Saved slice to {filepath}")

if __name__ == "__main__":
    slice_image("generated_pdfs/extracted_img_0.png", "generated_pdfs")
