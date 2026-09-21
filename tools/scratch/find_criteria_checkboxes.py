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

re_matches = re.findall(r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+re', decompressed)
rects = []
for match in re_matches:
    x, y, w, h = map(float, match)
    if 200 <= y <= 330:
        rects.append((x, y, w, h))

rects = list(set(rects))
rects.sort(key=lambda r: (-r[1], r[0]))

print(f"Found {len(rects)} unique rectangles in Y in [200, 330]:")
for r in rects:
    print(f"x={r[0]:6.2f}, y={r[1]:6.2f}, w={r[2]:6.2f}, h={r[3]:6.2f}")
