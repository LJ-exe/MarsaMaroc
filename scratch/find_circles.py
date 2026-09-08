import zlib
import re
from pdfrw import PdfReader

reader = PdfReader('pdf/Evaluation stage .pdf')
page = reader.pages[0]
contents = page.Contents
decompressed = ""
if isinstance(contents, list):
    for c in contents:
        decompressed += zlib.decompress(c.stream.encode('latin1')).decode('latin1', errors='replace')
else:
    decompressed = zlib.decompress(contents.stream.encode('latin1')).decode('latin1', errors='replace')

# Look for bezier curves (usually 6 numbers followed by c)
curves = re.findall(r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+c', decompressed)
print(f"Found {len(curves)} bezier curves in the PDF content stream.")

# Let's filter curves where coords are within our Y range [240, 320]
matching_curves = []
for c in curves:
    y_coords = [float(c[1]), float(c[3]), float(c[5])]
    if any(230 <= y <= 325 for y in y_coords):
        matching_curves.append(c)

print(f"Found {len(matching_curves)} curves in Y range [230, 325]:")
for idx, c in enumerate(matching_curves[:40]):
    print(f"Curve {idx}: ({c[0]}, {c[1]}) to ({c[4]}, {c[5]}) via ({c[2]}, {c[3]})")
