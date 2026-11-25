"""Teste 9 (QA): estilo A (tela cheia, limpo) em 4 planos de 6 s com dissolvencia de 1 s. Movimento so entre cidade/rostos/bustos (sem pernas). SOD: janelas esquerda/direita, evitando a porta central alada."""
import base64, subprocess, os, numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 1280, 720; FPS = 24; SEC = 6; OV = 1
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
def load(name, box):
    im = Image.open(f"hnc/quarentena/{name}.jpg").convert("RGB"); return sepia(im.crop((int(box[0] * im.width), int(box[1] * im.height), int(box[2] * im.width), int(box[3] * im.height))))
P = {"LO": load("RK-LO-MENIGTE", (.215, .192, .738, .775)), "SOD": load("RK-SODOMA-CEGOS", (.053, .064, .939, .899))}
# (placa, janela inicial (cx, cy, largura), janela final, legenda); coordenadas em fracao da chapa
shots = [("LO", (.50, .17, 1.00), (.50, .30, .93), "Ló saiu à porta, diante da multidão."),
         ("LO", (.34, .30, .70), (.64, .30, .70), "Os homens da cidade cercaram a casa."),
         ("SOD", (.24, .28, .40), (.24, .38, .37), "E foram feridos de cegueira."),
         ("SOD", (.76, .30, .40), (.76, .40, .37), "Não conseguiam achar a porta.")]
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.30 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.45, 0, 1))[..., None]
def grade(fr, rng):
    a = np.asarray(fr).astype(np.float32) / 255; g = a.mean(axis=2, keepdims=True); a = g + (a - g) * 0.72
    a = np.clip((a - 0.5) * 0.92 + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.06; a[..., 2] *= 0.90
    return a * VIG + rng.normal(0, 0.014, (H, W, 1))
FT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
def caption(a, text):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im); w = d.textlength(text, font=FT); x = (W - w) / 2; y = H - 82
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2): d.text((x + dx, y + dy), text, font=FT, fill=(0, 0, 0))
    d.text((x, y), text, font=FT, fill=(244, 232, 205)); return np.asarray(im).astype(np.float32) / 255
rng = np.random.default_rng(5)
def render(si, i):
    n, a, b, txt = shots[si]; t = i / (SEC * FPS - 1); e = 0.5 - 0.5 * np.cos(np.pi * t) * 0.5 - 0.25 + 0.25 * 0; e = t * 0.75 + (0.5 - 0.5 * np.cos(np.pi * t)) * 0.25
    cx, cy, wf = [a[k] + (b[k] - a[k]) * e for k in range(3)]; im = P[n]
    w = im.width * wf; h = w * 9 / 16; x0 = max(0, min(im.width - w, im.width * cx - w / 2)); y0 = max(0, min(im.height - h, im.height * cy - h / 2))
    return caption(grade(im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)), rng), txt), (x0 / im.width, y0 / im.height, (x0 + w) / im.width, (y0 + h) / im.height)
p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "28", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "/tmp/anim9.mp4"], stdin=subprocess.PIPE)
F = SEC * FPS; O = OV * FPS; step = F - O; total = step * 4 + O; stills = {}
for g in range(total):
    parts = []
    for si in range(4):
        i = g - si * step
        if 0 <= i < F: parts.append((si, i))
    out = None
    for si, i in parts:
        fr, bb = render(si, i); m = 1.0
        if si > 0 and i < O: m = i / O
        if si < 3 and i >= F - O: m = (F - 1 - i) / O if len(parts) == 1 else 1.0
        out = fr * m if out is None else out * (1 - m) + fr * m
        if i in (0, F // 2, F - 1): stills[(si, i)] = (Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8)).resize((640, 360)), bb)
    fade = min(1, g / 12, (total - 1 - g) / 12); p.stdin.write((np.clip(out * fade, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
sh = Image.new("RGB", (1920, 1440))
for si in range(4):
    for k, i in enumerate((0, F // 2, F - 1)): sh.paste(stills[(si, i)][0], (k * 640, si * 360)); print("janela", si, i, [round(v, 2) for v in stills[(si, i)][1]])
sh.save("/tmp/look9.jpg", quality=82); print("bytes", os.path.getsize("/tmp/anim9.mp4"))
for tag, f in (("LOOK", "/tmp/look9.jpg"), ("MP4", "/tmp/anim9.mp4")):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
