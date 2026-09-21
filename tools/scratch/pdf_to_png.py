import fitz
import os

def pdf_page_to_png(pdf_path, png_path, page_num=0):
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return False
        
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Use higher zoom for better resolution
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(png_path)
    doc.close()
    print(f"Successfully converted page {page_num} of {pdf_path} to {png_path}")
    return True

if __name__ == "__main__":
    os.makedirs("generated_pdfs", exist_ok=True)
    pdf_page_to_png("generated_pdfs/test_fiche_passage.pdf", "generated_pdfs/test_fiche_passage.png")
    pdf_page_to_png("generated_pdfs/test_fiche_alterne.pdf", "generated_pdfs/test_fiche_alterne.png")
    pdf_page_to_png("generated_pdfs/test_fiche_projet.pdf", "generated_pdfs/test_fiche_projet.png")
