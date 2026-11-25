"""Folha de contato dos arquivos em quarentena (QA visual) + dimensoes. Uso: python -I hnc/sheet.py ID1 ID2 ..."""
import sys, glob, base64, io
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
fs = []
for i in sys.argv[1:]:
    fs += glob.glob(f"hnc/quarentena/{i}.*")
ims = []
for f in fs:
    im = Image.open(f).convert("RGB"); print("arquivo", f, im.size); im.thumbnail((640, 640)); ims.append(im)
W = sum(i.width for i in ims) + 10 * len(ims); sh = Image.new("RGB", (W, 640), (30, 30, 30)); x = 0
for im in ims: sh.paste(im, (x, 0)); x += im.width + 10
b = io.BytesIO(); sh.save(b, "JPEG", quality=85); s = base64.b64encode(b.getvalue()).decode()
print("LOOKB64START"); [print(s[i:i + 4000]) for i in range(0, len(s), 4000)]; print("LOOKB64END", len(s))
