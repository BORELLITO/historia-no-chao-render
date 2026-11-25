"""Teste 12 (QA): confere o lote 4 (paisagens PD) e gera folha de previa."""
import base64, glob, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ids = ["RB-HEBRON", "RB-MARMORTO-BM", "WH-ESCAPE-BODE", "RB-RIJKS-TERRASANTA"]; tiles = []
for i in ids:
    fs = glob.glob(f"hnc/quarentena/{i}.*")
    if not fs: print("AUSENTE", i); continue
    im = Image.open(fs[0]).convert("RGB"); print("ok", i, im.size, os.path.getsize(fs[0])); t = im.copy(); t.thumbnail((900, 640)); tiles.append(t)
sh = Image.new("RGB", (1800, 1280), (20, 20, 20))
for k, t in enumerate(tiles): sh.paste(t, ((k % 2) * 900 + (900 - t.width) // 2, (k // 2) * 640))
sh.save("/tmp/look12.jpg", quality=82); b = base64.b64encode(open("/tmp/look12.jpg", "rb").read()).decode()
print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
