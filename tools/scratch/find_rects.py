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

# Look for drawing commands like rects: x y w h re or m l
# and look for text chunks
print("Decompressed content length:", len(decompressed))

# Find lines/rects
re_matches = re.findall(r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+re', decompressed)
if re_matches:
    print(f"Found {len(re_matches)} rectangles:")
    for match in re_matches[:50]:
        x, y, w, h = map(float, match)
        print(f"Rect: x={x:.2f}, y={y:.2f}, w={w:.2f}, h={h:.2f}")

path_commands = re.findall(r'([-\d.]+)\s+([-\d.]+)\s+([ml])', decompressed)
print(f"Found {len(path_commands)} path commands")
