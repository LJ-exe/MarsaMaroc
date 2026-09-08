from pypdf import PdfReader

reader = PdfReader("pdf/Evaluation stage .pdf")
page = reader.pages[0]

def visitor(text, cm, tm, fontDict, fontSize):
    t = text.strip()
    if t:
        print(f"Txt: {t!r:25} | Hex: {t.encode('utf-8').hex()} | X: {tm[4]:6.2f} | Y: {tm[5]:6.2f} | Font: {fontDict.get('/BaseFont', 'None')}")

page.extract_text(visitor_text=visitor)
