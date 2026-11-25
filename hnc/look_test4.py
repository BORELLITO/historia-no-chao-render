"""Teste 4 (QA): confere as 2 gravuras Rijksmuseum baixadas (dimensoes) e gera folha de previa em baixa resolucao."""
import base64, glob, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
fs = sorted(glob.glob("hnc/quarentena/RK-*.jpg")); print("arquivos", fs)
ims = []
for f in fs:
    im = Image.open(f).convert("RGB"); print(os.path.basename(f), im.size, os.path.getsize(f)); ims.append(im)
if ims:
    tw = 900; rs = [i.resize((tw, int(i.height * tw / i.width))) for i in ims]
    sheet = Image.new("RGB", (tw * len(rs), max(r.height for r in rs)), (20, 20, 20))
    for k, r in enumerate(rs): sheet.paste(r, (k * tw, 0))
    sheet.save("/tmp/look4.jpg", quality=80)
    b = base64.b64encode(open("/tmp/look4.jpg", "rb").read()).decode()
    print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
