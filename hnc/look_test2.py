"""Teste 2 (QA, nao e master): estilo PINTURA unico. Video real e grafico passam por filtro pictorico deterministico (OpenCV, sem IA, sem custo)."""
import base64, subprocess, numpy as np, cv2
from PIL import Image
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 1920, 1080
src = open("hnc/look_test.py").read()
ns = {}; exec(src[src.index("def frame"):src.index("mk = ")], {"subprocess": subprocess, "np": np, "Image": Image, "FF": FF, "W": W, "H": H}, ns)
frame, crop169, grade = ns["frame"], ns["crop169"], ns["grade"]
def paint(im, strength=1.0, seed=3):
    bgr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    small = cv2.resize(bgr, (960, 540), interpolation=cv2.INTER_AREA)
    s = cv2.stylization(small, sigma_s=int(45 + 25 * strength), sigma_r=0.35 + 0.15 * strength)
    s = cv2.resize(s, (W, H), interpolation=cv2.INTER_CUBIC)
    # pinceladas: realce de contorno suave + textura de tela
    rng = np.random.default_rng(seed); tex = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.6)
    tex = (tex / (np.abs(tex).max() + 1e-6)) * 14 * strength
    out = np.clip(s.astype(np.float32) + tex[..., None], 0, 255).astype(np.uint8)
    return grade(Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)), seed)
mk = "hnc/quarentena/MK-52009.mp4"
martin = Image.open("hnc/quarentena/WM-MARTIN.jpg").convert("RGB")
f1, f2 = frame(mk, 3, "/tmp/f1.png"), frame(mk, 14, "/tmp/f2.png")
m1 = crop169(martin, martin.width * 0.5, martin.height * 0.45, int(martin.width * 0.8))
mn = Image.open("hnc/gfx/manre_p022.png").convert("RGB").resize((W, H))
cols = [(m1, grade(m1, 0)), (f1, paint(f1, 0.6)), (f1, paint(f1, 1.0)), (f2, paint(f2, 0.8)), (mn, paint(mn, 0.8))]
tw, th = 480, 270
sheet = Image.new("RGB", (tw * len(cols), th * 2), (20, 20, 20))
for i, (a, b) in enumerate(cols):
    sheet.paste(a.resize((tw, th), Image.LANCZOS), (i * tw, 0)); sheet.paste(b.resize((tw, th), Image.LANCZOS), (i * tw, th))
sheet.save("/tmp/look2.jpg", quality=82)
b = base64.b64encode(open("/tmp/look2.jpg", "rb").read()).decode()
print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
