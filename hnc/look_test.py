"""Teste de coerencia visual (so QA, nao e master): mesmo tratamento em arte antiga, video real e grafico original."""
import base64, subprocess, sys, numpy as np
from PIL import Image
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1920, 1080
def frame(mp4, t, out):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(t), "-i", mp4, "-frames:v", "1", "-vf", f"scale={W}:{H}", out], check=True)
    return Image.open(out).convert("RGB")
def crop169(im, cx, cy, w):
    h = int(w * 9 / 16); x = max(0, min(im.width - w, int(cx - w / 2))); y = max(0, min(im.height - h, int(cy - h / 2)))
    return im.crop((x, y, x + w, y + h)).resize((W, H), Image.LANCZOS)
def grade(im, seed=1):
    a = np.asarray(im).astype(np.float32) / 255
    g = a.mean(axis=2, keepdims=True); a = g + (a - g) * 0.72            # dessatura
    a = np.clip((a - 0.5) * 0.92 + 0.5 + 0.02, 0, 1)                      # contraste suave
    a[..., 0] *= 1.06; a[..., 1] *= 1.0; a[..., 2] *= 0.90                # tom quente
    yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a *= (1 - 0.28 * np.clip(r - 0.35, 0, 1)[..., None])                  # vinheta
    rng = np.random.default_rng(seed); a += rng.normal(0, 0.018, (H, W, 1))  # grao
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
mk = "hnc/quarentena/MK-52009.mp4"
martin = Image.open("hnc/quarentena/WM-MARTIN.jpg").convert("RGB"); print("martin", martin.size)
shots = [frame(mk, 3, "/tmp/f1.png"), frame(mk, 14, "/tmp/f2.png"),
         crop169(martin, martin.width * 0.5, martin.height * 0.45, int(martin.width * 0.8)),
         crop169(martin, martin.width * 0.72, martin.height * 0.5, int(martin.width * 0.45)),
         Image.open("hnc/gfx/manre_p022.png").convert("RGB").resize((W, H))]
tw, th = 480, 270
sheet = Image.new("RGB", (tw * len(shots), th * 2), (20, 20, 20))
for i, s in enumerate(shots):
    sheet.paste(s.resize((tw, th), Image.LANCZOS), (i * tw, 0))
    sheet.paste(grade(s, i).resize((tw, th), Image.LANCZOS), (i * tw, th))
sheet.save("/tmp/look.jpg", quality=82)
b = base64.b64encode(open("/tmp/look.jpg", "rb").read()).decode()
print("LOOKB64START"); [print(b[i:i + 4000]) for i in range(0, len(b), 4000)]; print("LOOKB64END", len(b))
