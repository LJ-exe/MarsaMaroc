import os
from pypdf import PdfReader

def dump_pdf_info(pdf_path):
    print(f"\n=================== DUMPING {pdf_path} ===================")
    if not os.path.exists(pdf_path):
        print("File does not exist")
        return
    
    reader = PdfReader(pdf_path)
    print(f"Number of pages: {len(reader.pages)}")
    
    for idx, page in enumerate(reader.pages):
        print(f"--- Page {idx + 1} ---")
        print("Page MediaBox:", page.mediabox)
        
        # We can extract text with positions by using visitor functions
        def visitor_body(text, cm, tm, fontDict, fontSize):
            if text.strip():
                # tm is the text matrix. tm[4] is X coordinate, tm[5] is Y coordinate
                print(f"Text: {text!r:30} | X: {tm[4]:6.2f} | Y: {tm[5]:6.2f} | FontSize: {fontSize:4.1f}")
        
        page.extract_text(visitor_text=visitor_body)

if __name__ == "__main__":
    dump_pdf_info("pdf/Evaluation stage .pdf")
    dump_pdf_info("pdf/ATTESTATION DE STAGE challal.pdf")
