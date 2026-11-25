"""Teste 3 (QA): tratamento leve unico em Gn 18 (Frances, Murillo) ao lado de Mixkit e Martin. Sem filtro de pincelada."""
import base64, subprocess, numpy as np
from PIL import Image, ImageFilter
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 1920, 1080
src = open("hnc/look_test.py").read()
ns = {}; exec(src[src.index("def frame"):src.index("mk = ")], {"subprocess": subprocess, "np": np, "Image": Image, "FF": FF, "W": W, "H": H}, ns)
frame, crop169, grade = ns["frame"], ns["crop169"], ns["grade"]
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    t = np.stack([g * 1.0, g * 0.86, g * 0.66], axis=2) * 1.08
    return Image.fromarray((np.clip(t, 0, 1) * 255).astype(np.uint8))
def fit(im):  # cabe inteiro na moldura 16:9; fundo = a propria obra desfocada e escurecida
    bg = im.resize((W, H)).filter(ImageFilter.GaussianBlur(40)); bg = Image.fromarray((np.asarray(bg) * 0.35).astype(np.uint8))
    s = H / im.height; r = im.resize((int(im.width * s), H), Image.LANCZOS); bg.paste(r, ((W - r.width) // 2, 0)); return bg
fr = Image.open("hnc/quarentena/WM-FRENCH-ABRAHAM.jpg").convert("RGB"); mu = Image.open("hnc/quarentena/WM-MURILLO.jpg").convert("RGB")
mt = Image.open("hnc/quarentena/WM-MARTIN.jpg").convert("RGB"); print("french", fr.size, "murillo", mu.size)
f1 = frame("hnc/quarentena/MK-52009.mp4", 3, "/tmp/f1.png")
fr_a = crop169(fr, fr.width * 0.5, fr.height * 0.55, int(fr.width * 0.98))
fr_b = crop169(fr, fr.width * 0.5, fr.height * 0.62, int(fr.width * 0.55))
cols = [(fr_a, grade(sepia(fr_a), 1)), (fr_b, grade(sepia(fr_b), 2)), (fit(mu), grade(fit(mu), 3)),
        (f1, grade(f1, 4)), (crop169(mt, mt.width * .5, mt.height * .45, int(mt.width * .8)), grade(crop169(mt, mt.width * .5, mt.height * .45, int(mt.width * .8)), 5))]
tw, th = 480, 270
sheet = Image.new("RGB", (tw * len(cols), th * 2), (20, 20, 20))
for i, (a, b) in enumerate(cols):
    sheet.paste(a.resize((tw, th), Image.LANCZOS), (i * tw, 0)); sheet.paste(b.resize((tw, th), Image.LANCZOS), (i * tw, th))
sheet.save("/tmp/look3.jpg", quality=84)
b = base64.b64encode(open("/tmp/look3.jpg", "rb").read()).decode()
print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
