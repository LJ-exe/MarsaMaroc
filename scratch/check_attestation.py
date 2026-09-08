from pypdf import PdfReader
reader = PdfReader("pdf/Attestation de stage .pdf")
print("Metadata:", reader.metadata)
page = reader.pages[0]
print("Images found:", len(page.images))
print("Raw Text Length:", len(page.extract_text()))
print("Raw Text Contents:\n", page.extract_text())

