import os
import re
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, red
from pdfrw import PdfReader, PdfWriter, PageMerge
import fitz

def test_generate_pdf(type_stage, output_filename, draw_red_border=True):
    try:
        output_dir = 'generated_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        
        template_path = 'pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf'
        if not os.path.exists(template_path):
            print(f"Template not found: {template_path}")
            return
            
        temp_overlay_path = os.path.join(output_dir, f"temp_{output_filename}")
        c = canvas.Canvas(temp_overlay_path, pagesize=(595.32, 841.92))
        
        brand_color = HexColor('#001a4d')
        c.setFillColor(brand_color)
        
        # 1. Dynamically detect checkbox positions from the template PDF
        detected_boxes = []
        try:
            doc_temp = fitz.open(template_path)
            page_temp = doc_temp[0]
            h_page_temp = page_temp.rect.height
            
            # Find the Y position of the "Type de Stage" section by locating the word "Passage"
            words = page_temp.get_text("words")
            type_stage_y = None
            for w in words:
                if "passage" in w[4].lower() or "altern" in w[4].lower():
                    type_stage_y = w[1] # top coordinate of the text
                    break
            if type_stage_y is None:
                type_stage_y = 324.87
                
            # Get drawings and filter vertical lines near this Y
            drawings_temp = page_temp.get_drawings()
            v_lines = []
            for d in drawings_temp:
                r = d['rect']
                if abs(r.y0 - type_stage_y) < 15 and 8 <= r.height <= 15 and r.width < 1.5:
                    if 50 <= r.x0 <= 550:
                        v_lines.append(r)
            
            # Sort vertical lines by X coordinate
            v_lines.sort(key=lambda r: r.x0)
            
            # Group into pairs to form boxes
            i = 0
            while i < len(v_lines) - 1:
                l1 = v_lines[i]
                l2 = v_lines[i+1]
                dist = l2.x0 - l1.x0
                if 15 <= dist <= 40:
                    x = l1.x0
                    y = min(l1.y0, l2.y0)
                    width = dist
                    height = max(l1.height, l2.height)
                    
                    # Convert to ReportLab bottom-up coordinates
                    rl_x = x
                    rl_y = h_page_temp - (y + height)
                    
                    detected_boxes.append({
                        'x': rl_x,
                        'y': rl_y,
                        'width': width,
                        'height': height
                    })
                    i += 2
                else:
                    i += 1
            doc_temp.close()
        except Exception as e:
            print(f"[PDF] Checkbox detection error: {e}")

        # Fallback coordinates if detection failed
        fallback_centers = [
            (242.33, 511.27),
            (344.41, 511.27),
            (505.84, 511.27)
        ]
        
        box_centers = []
        if len(detected_boxes) >= 3:
            for idx, box in enumerate(detected_boxes[:3]):
                cx = box['x'] + box['width'] / 2
                cy = box['y'] + box['height'] / 2
                box_centers.append((cx, cy))
                
                # Draw a temporary red border around all detected boxes if requested
                if draw_red_border:
                    c.saveState()
                    c.setStrokeColor(red)
                    c.setLineWidth(1.0)
                    c.rect(box['x'], box['y'], box['width'], box['height'], stroke=1, fill=0)
                    c.restoreState()
            print(f"[PDF] Dynamically detected centers: {box_centers}")
        else:
            box_centers = fallback_centers
            print(f"[PDF] Using fallback centers: {box_centers}")
            
        # Helper to draw a cross (X) in a checkbox
        def draw_checkbox_cross(c, x, y, size=8):
            c.saveState()
            c.setStrokeColor(brand_color)
            c.setLineWidth(2.0)
            offset = size / 2
            c.line(x - offset, y - offset, x + offset, y + offset)
            c.line(x + offset, y - offset, x - offset, y + offset)
            c.restoreState()
            print(f"[CHECKBOX] Drew cross at X={x}, Y={y}, size={size}")

        # Determine index based on selected stage type
        type_lower = type_stage.lower() if type_stage else ''
        selected_idx = 0
        if 'altern' in type_lower:
            selected_idx = 1
        elif 'pfa' in type_lower or 'fin' in type_lower or 'projet' in type_lower:
            selected_idx = 2
            
        target_center_x, target_center_y = box_centers[selected_idx]
        draw_checkbox_cross(c, target_center_x, target_center_y, size=8)
        
        c.save()
        
        # Merge overlay onto template
        template_pdf = PdfReader(template_path)
        overlay_pdf = PdfReader(temp_overlay_path)
        PageMerge(template_pdf.pages[0]).add(overlay_pdf.pages[0]).render()
        
        output_path = os.path.join(output_dir, output_filename)
        PdfWriter(output_path, trailer=template_pdf).write()
        
        try:
            os.remove(temp_overlay_path)
        except Exception:
            pass
            
        print(f"Generated test PDF at: {output_path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generate_pdf("Passage", "test_fiche_passage.pdf")
    test_generate_pdf("Alterné", "test_fiche_alterne.pdf")
    test_generate_pdf("Projet de fin d'étude", "test_fiche_projet.pdf")
