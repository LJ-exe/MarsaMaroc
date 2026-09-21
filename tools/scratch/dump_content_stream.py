import zlib
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

# Print lines in decompressed that are related to text or drawings
lines = decompressed.split('\n')
print(f"Total lines in content stream: {len(lines)}")
# Find lines with text Tj or TJ, or drawing commands, and filter for Y positions
current_y = 0.0
for idx, line in enumerate(lines):
    # Keep track of text matrices
    if 'Tm' in line or 'Td' in line or 'TD' in line:
        parts = line.split()
        if len(parts) >= 6:
            try:
                current_y = float(parts[5])
            except ValueError:
                pass
    if 240 <= current_y <= 325:
        if 'Tj' in line or 'TJ' in line or 're' in line or 'c' in line:
            print(f"Line {idx} (Y ~ {current_y:.2f}): {line}")
