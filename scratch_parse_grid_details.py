import zlib
import re
from pdfrw import PdfReader

reader = PdfReader('pdf/FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf')
page = reader.pages[0]
contents = page.Contents
decompressed = zlib.decompress(contents.stream.encode('latin1')).decode('latin1', errors='replace')

# Print V-lines and H-lines between Y=580 and Y=670
print("=== LINES BETWEEN Y=580 AND Y=670 ===")
lines = []
path_commands = re.findall(r'([-\d.]+)\s+([-\d.]+)\s+([ml])', decompressed)
for i in range(len(path_commands) - 1):
    x1, y1, op1 = path_commands[i]
    x2, y2, op2 = path_commands[i+1]
    x1, y1 = float(x1), float(y1)
    x2, y2 = float(x2), float(y2)
    if op1 == 'm' and op2 == 'l':
        if 580 <= y1 <= 670 or 580 <= y2 <= 670:
            if y1 == y2:
                lines.append(("H", y1, x1, x2, abs(x2-x1)))
            elif x1 == x2:
                lines.append(("V", x1, y1, y2, abs(y2-y1)))

# Sort by Y descending, then type, then X ascending
lines.sort(key=lambda l: (-l[1], l[0], l[2]))
for l in lines:
    if l[0] == "H":
        print(f"H-Line: y={l[1]:6.2f} | x1={l[2]:6.2f} -> x2={l[3]:6.2f} (w={l[4]:.2f})")
    else:
        print(f"V-Line: x={l[1]:6.2f} | y1={l[2]:6.2f} -> y2={l[3]:6.2f} (h={l[4]:.2f})")
