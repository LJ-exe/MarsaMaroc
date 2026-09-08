import fitz
import os

def detect_checkboxes(template_path):
    doc = fitz.open(template_path)
    page = doc[0]
    h_page = page.rect.height
    
    # 1. Find the Y position of the "Type de Stage" section by locating the word "Passage"
    words = page.get_text("words")
    type_stage_y = None
    for w in words:
        if "passage" in w[4].lower() or "altern" in w[4].lower():
            type_stage_y = w[1] # top coordinate of the text
            break
            
    if type_stage_y is None:
        type_stage_y = 324.87
        
    print(f"Detected Type de Stage text Y position (top-down): {type_stage_y:.3f}")
        
    # 2. Get drawings and filter vertical lines near this Y
    drawings = page.get_drawings()
    v_lines = []
    for d in drawings:
        r = d['rect']
        # Vertical line check: width < 1.5, height between 8 and 15, and Y within range around type_stage_y
        if abs(r.y0 - type_stage_y) < 15 and 8 <= r.height <= 15 and r.width < 1.5:
            # Exclude page borders at ~42 and ~558
            if 50 <= r.x0 <= 550:
                v_lines.append(r)
                
    # Sort vertical lines by X coordinate
    v_lines.sort(key=lambda r: r.x0)
    print(f"Found {len(v_lines)} vertical line segments in the Y range:")
    for idx, r in enumerate(v_lines):
        print(f"  Line {idx}: X={r.x0:.3f}, Y={r.y0:.3f} to {r.y1:.3f}, width={r.width:.3f}, height={r.height:.3f}")
    
    # Group them into pairs to form boxes
    boxes = []
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
            rl_y = h_page - (y + height) # bottom of the box in bottom-up
            rl_w = width
            rl_h = height
            
            boxes.append({
                'x': rl_x,
                'y': rl_y,
                'width': rl_w,
                'height': rl_h,
                'top_down_x': x,
                'top_down_y': y
            })
            i += 2
        else:
            i += 1
            
    return boxes

if __name__ == "__main__":
    pdf_path = "pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf"
    if not os.path.exists(pdf_path):
        print("Template file not found at", pdf_path)
    else:
        boxes = detect_checkboxes(pdf_path)
        print(f"\nDetected {len(boxes)} boxes:")
        labels = ["Passage", "Alterné", "Projet de fin d'étude"]
        for idx, box in enumerate(boxes):
            label = labels[idx] if idx < len(labels) else f"Box {idx+1}"
            print(f"{label}:")
            print(f"  ReportLab bottom-up: x={box['x']:.3f}, y={box['y']:.3f}, width={box['width']:.3f}, height={box['height']:.3f}")
            center_x = box['x'] + box['width'] / 2
            center_y = box['y'] + box['height'] / 2
            print(f"  Calculated center: center_x={center_x:.3f}, center_y={center_y:.3f}")
