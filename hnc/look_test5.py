"""Teste 5 (QA): grade 3x3 de recortes 16:9 (largura 45%) em cada gravura, com tratamento leve, para escolher recortes sem asas."""
import base64, subprocess, numpy as np
from PIL import Image, ImageDraw
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 1920, 1080
src = open("hnc/look_test.py").read(); ns = {}
exec(src[src.index("def frame"):src.index("mk = ")], {"subprocess": subprocess, "np": np, "Image": Image, "FF": FF, "W": W, "H": H}, ns)
crop169, grade = ns["crop169"], ns["grade"]
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
tw, th = 480, 270; out = []
for name in ["RK-LO-MENIGTE", "RK-SODOMA-CEGOS"]:
    im = Image.open(f"hnc/quarentena/{name}.jpg").convert("RGB"); sh = Image.new("RGB", (tw * 3, th * 3))
    for r, cy in enumerate([.30, .50, .70]):
        for c, cx in enumerate([.28, .50, .72]):
            t = grade(sepia(crop169(im, im.width * cx, im.height * cy, int(im.width * .45)))).resize((tw, th))
            d = ImageDraw.Draw(t); d.rectangle((0, 0, 110, 18), fill=(0, 0, 0)); d.text((3, 3), f"{name[3:6]} x{int(cx*100)} y{int(cy*100)}", fill=(255, 255, 255))
            sh.paste(t, (c * tw, r * th))
    out.append(sh)
sheet = Image.new("RGB", (tw * 3, th * 6)); sheet.paste(out[0], (0, 0)); sheet.paste(out[1], (0, th * 3)); sheet.save("/tmp/look5.jpg", quality=82)
b = base64.b64encode(open("/tmp/look5.jpg", "rb").read()).decode()
print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
