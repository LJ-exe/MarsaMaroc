import sys

try:
    import pypdf
    print("pypdf: available")
except ImportError:
    print("pypdf: NOT available")

try:
    import pdfplumber
    print("pdfplumber: available")
except ImportError:
    print("pdfplumber: NOT available")

try:
    import fitz # PyMuPDF
    print("pymupdf (fitz): available")
except ImportError:
    print("pymupdf (fitz): NOT available")

try:
    import pdfminer
    print("pdfminer: available")
except ImportError:
    print("pdfminer: NOT available")

try:
    import pdfrw
    print("pdfrw: available")
except ImportError:
    print("pdfrw: NOT available")

try:
    import reportlab
    print("reportlab: available")
except ImportError:
    print("reportlab: NOT available")
