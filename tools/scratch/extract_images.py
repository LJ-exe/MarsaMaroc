import os
from pypdf import PdfReader

def extract_pdf_images(pdf_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    reader = PdfReader(pdf_path)
    page = reader.pages[0]
    
    count = 0
    for image_file_object in page.images:
        filename = f"extracted_img_{count}.png"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as fp:
            fp.write(image_file_object.data)
        print(f"Extracted image to {filepath}")
        count += 1

if __name__ == "__main__":
    extract_pdf_images("pdf/Attestation de stage .pdf", "generated_pdfs")
