"""Teste 10 (QA): confere dimensoes dos arquivos baixados (lote 3) e gera folha de previa."""
import base64, glob, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ids = ["RK-LO-FUGA", "RK-LOTSVROUW", "RK-ABRAAO-REFEICAO", "NGA-DURER-FUGA", "WM-MARTIN", "WM-FRENCH-ABRAHAM", "RK-LO-MENIGTE", "RK-SODOMA-CEGOS"]
tiles = []
for i in ids:
    fs = glob.glob(f"hnc/quarentena/{i}.*")
    if not fs: print("AUSENTE", i); continue
    im = Image.open(fs[0]).convert("RGB"); print("ok", i, im.size, os.path.getsize(fs[0])); t = im.copy(); t.thumbnail((620, 460)); tiles.append(t)
sh = Image.new("RGB", (620 * 4, 460 * 2), (20, 20, 20))
for k, t in enumerate(tiles): sh.paste(t, ((k % 4) * 620 + (620 - t.width) // 2, (k // 4) * 460))
sh.save("/tmp/look10.jpg", quality=80); b = base64.b64encode(open("/tmp/look10.jpg", "rb").read()).decode()
print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
