"""Motor ESTILO A (aprovado pelo dono): arte PD em TELA CHEIA, movimento lento por janelas 16:9 dentro da chapa, dissolvencia, grade leve, legenda no pe.
Uso: python -I hnc/engine_a.py hnc/shots_xxx.json /tmp/saida.mp4   (le hnc/quarentena/<ID>.jpg). Janela = (cx, cy, largura) em fracao da chapa util."""
import base64, json, subprocess, sys, os, numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
cfg = json.load(open(sys.argv[1])); OUT = sys.argv[2]
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H, FPS = cfg["w"], cfg["h"], cfg["fps"]; OV = int(cfg["overlap_s"] * FPS)
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
P = {}
for k, v in cfg["plates"].items():
    im = Image.open(f"hnc/quarentena/{k}.jpg").convert("RGB"); b = v["box"]
    if b == "auto":  # area util = o que difere da cor do papel (mediana da borda externa)
        sm = np.asarray(im.resize((800, int(800 * im.height / im.width)))).astype(np.float32); e = max(2, int(sm.shape[0] * .02))
        edge = np.concatenate([sm[:e].reshape(-1, 3), sm[-e:].reshape(-1, 3), sm[:, :e].reshape(-1, 3), sm[:, -e:].reshape(-1, 3)]); bg = np.median(edge, axis=0)
        d = np.abs(sm - bg).max(axis=2) > 22; c = np.where(d.mean(0) > .30)[0]; r = np.where(d.mean(1) > .30)[0]
        b = [c[0] / sm.shape[1] + .01, r[0] / sm.shape[0] + .01, c[-1] / sm.shape[1] - .01, r[-1] / sm.shape[0] - .01]; print("auto-box", k, [round(float(x), 3) for x in b])
    im = im.crop((int(b[0] * im.width), int(b[1] * im.height), int(b[2] * im.width), int(b[3] * im.height)))
    if im.width > 2800: im = im.resize((2800, int(im.height * 2800 / im.width)), Image.LANCZOS)
    P[k] = sepia(im) if v["sepia"] else im; print("chapa", k, P[k].size)
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.30 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.45, 0, 1))[..., None]
def grade(fr, rng):
    a = np.asarray(fr).astype(np.float32) / 255; g = a.mean(axis=2, keepdims=True); a = g + (a - g) * 0.72
    a = np.clip((a - 0.5) * 0.92 + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.06; a[..., 2] *= 0.90
    return a * VIG + rng.normal(0, 0.009, (H, W, 1))
FT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
def caption(a, text):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im); w = d.textlength(text, font=FT); x = (W - w) / 2; y = H - 82
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2): d.text((x + dx, y + dy), text, font=FT, fill=(0, 0, 0))
    d.text((x, y), text, font=FT, fill=(244, 232, 205)); return np.asarray(im).astype(np.float32) / 255
rng = np.random.default_rng(11)
def render(s, i):
    F = int(s["dur"] * FPS); t = i / (F - 1); e = t * 0.75 + (0.5 - 0.5 * np.cos(np.pi * t)) * 0.25
    cx, cy, wf = [s["a"][k] + (s["b"][k] - s["a"][k]) * e for k in range(3)]; im = P[s["src"]]
    w = im.width * wf; h = w * 9 / 16
    if h > im.height: h = im.height; w = h * 16 / 9   # nunca passa da altura da chapa
    x0 = max(0, min(im.width - w, im.width * cx - w / 2)); y0 = max(0, min(im.height - h, im.height * cy - h / 2))
    fr = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)); return caption(grade(fr, rng), s["cap"]), (x0 / im.width, y0 / im.height, (x0 + w) / im.width, (y0 + h) / im.height)
shots = cfg["shots"]; starts = []; pos = 0
for s in shots:  # regra do dono: sem foco extremo em detalhes; janela >= 55% da largura da chapa
    assert min(s['a'][2], s['b'][2]) >= 0.55, f"janela estreita demais em {s['src']}: {s['a'][2]}/{s['b'][2]}"
for s in shots: starts.append(pos); pos += int(s["dur"] * FPS) - OV
total = pos + OV
p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "31", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
stills = {}
for g in range(total):
    out = None
    for si, s in enumerate(shots):
        F = int(s["dur"] * FPS); i = g - starts[si]
        if not 0 <= i < F: continue
        fr, bb = render(s, i)
        if si in (0,) or i >= OV: m = 1.0
        else: m = i / OV
        if si < len(shots) - 1 and i >= F - OV: m = 1.0  # o proximo plano entra por cima
        out = fr if out is None else out * (1 - m) + fr * m
        if i in (0, F // 2, F - 1): stills[(si, i)] = (Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8)).resize((480, 270)), bb)
    fade = min(1, g / 12, (total - 1 - g) / 12); p.stdin.write((np.clip(out * fade, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait(); print("frames", total, "dur_s", round(total / FPS, 1), "bytes", os.path.getsize(OUT))
sh = Image.new("RGB", (1440, 270 * len(shots)))
for si, s in enumerate(shots):
    F = int(s["dur"] * FPS)
    for k, i in enumerate((0, F // 2, F - 1)): sh.paste(stills[(si, i)][0], (k * 480, si * 270)); print("janela", s["src"], i, [round(float(v), 2) for v in stills[(si, i)][1]])
sh.save("/tmp/sheet.jpg", quality=80)
for tag, f in (("LOOK", "/tmp/sheet.jpg"), ("MP4", OUT)):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
