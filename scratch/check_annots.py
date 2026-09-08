from pypdf import PdfReader

reader = PdfReader("pdf/Evaluation stage .pdf")
page = reader.pages[0]
print("Annots:", page.annotations)
if page.annotations:
    print(f"Found {len(page.annotations)} annotations.")
    for idx, annot in enumerate(page.annotations):
        obj = annot.get_object()
        print(f"Annot {idx}: Type={obj.get('/Subtype')}, Rect={obj.get('/Rect')}, Name={obj.get('/T')}")
