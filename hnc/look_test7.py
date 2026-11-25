"""Teste 7 (QA): gravura INTEIRA (so a chapa, sem margem de papel/legenda latina), push-in lento (100->106% em 10 s), dissolvencia de 1 s, 1280x720."""
import base64, subprocess, os, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 1280, 720; FPS = 24; SEC = 10; OV = 1; S = 2
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
def plate(im, name):
    if name == "RK-LO-MENIGTE": fx0, fx1, fy0, fy1 = .215, .738, .192, .775  # fx0: corta o nicho com o anjo alado (regra: sem asas)
    else:
        sm = np.asarray(im.convert("L").resize((800, int(800 * im.height / im.width)))).astype(np.float32); d = sm < 140
        c = np.where(d.mean(0) > .12)[0]; r = np.where(d.mean(1) > .12)[0]
        fx0, fx1, fy0, fy1 = c[0] / sm.shape[1] + .006, c[-1] / sm.shape[1] - .006, r[0] / sm.shape[0] + .006, min(r[-1] / sm.shape[0] - .006, .905)
    print(name, "chapa", [round(v, 3) for v in (fx0, fx1, fy0, fy1)])
    return im.crop((int(fx0 * im.width), int(fy0 * im.height), int(fx1 * im.width), int(fy1 * im.height)))
def compose(pl):  # chapa inteira, centralizada na altura; fundo = a propria chapa desfocada e escurecida
    CW, CH = W * S, H * S
    bg = pl.resize((CW, CH)).filter(ImageFilter.GaussianBlur(60 * S)); bg = Image.fromarray((np.asarray(bg) * 0.30).astype(np.uint8))
    k = min(CW * .86 / pl.width, CH * .80 / pl.height); r = pl.resize((int(pl.width * k), int(pl.height * k)), Image.LANCZOS)
    bg.paste(r, ((CW - r.width) // 2, int(CH * .045))); return bg
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.30 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.45, 0, 1))[..., None]
def grade(im, rng):
    a = np.asarray(im).astype(np.float32) / 255; g = a.mean(axis=2, keepdims=True); a = g + (a - g) * 0.72
    a = np.clip((a - 0.5) * 0.92 + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.06; a[..., 2] *= 0.90
    return a * VIG + rng.normal(0, 0.014, (H, W, 1))
FT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
def caption(a, text):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im); w = d.textlength(text, font=FT); x = (W - w) / 2; y = H - 78
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2): d.text((x + dx, y + dy), text, font=FT, fill=(0, 0, 0))
    d.text((x, y), text, font=FT, fill=(244, 232, 205)); return np.asarray(im).astype(np.float32) / 255
shots = [("RK-LO-MENIGTE", (.50, .50, 1.00), (.515, .495, 1.06), "Ló saiu à porta, diante da multidão."),
         ("RK-SODOMA-CEGOS", (.50, .50, 1.00), (.485, .505, 1.06), "E os homens que estavam à porta foram feridos de cegueira.")]
comps = {}; rng = np.random.default_rng(7)
for n in dict.fromkeys(s[0] for s in shots):
    pl = plate(Image.open(f"hnc/quarentena/{n}.jpg").convert("RGB"), n); pl.resize((600, int(600 * pl.height / pl.width))).save(f"/tmp/plate_{n}.jpg", quality=80); comps[n] = sepia(compose(pl))
def render(si, i):
    n, a, b, txt = shots[si]; t = i / (SEC * FPS - 1); t = 0.5 - 0.5 * np.cos(np.pi * t) * 0 + 0  # placeholder
    t = i / (SEC * FPS - 1); e = t * 0.7 + (0.5 - 0.5 * np.cos(np.pi * t)) * 0.3  # quase linear, suaviza so as pontas
    cx, cy, z = [a[k] + (b[k] - a[k]) * e for k in range(3)]; im = comps[n]; w = im.width / z; h = im.height / z
    x0 = im.width * cx - w / 2; y0 = im.height * cy - h / 2
    fr = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)); return caption(grade(fr, rng), txt)
p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-crf", "29", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "/tmp/anim7.mp4"], stdin=subprocess.PIPE)
F = SEC * FPS; O = OV * FPS; total = F * 2 - O; stills = []
for g in range(total):
    if g < F - O: fr = render(0, g)
    elif g < F: m = (g - (F - O)) / O; fr = render(0, g) * (1 - m) + render(1, g - (F - O)) * m
    else: fr = render(1, g - (F - O))
    fade = min(1, g / 12, (total - 1 - g) / 12); fr = fr * fade
    p.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes())
    if g in (30, 200, total - 40): stills.append(Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8)).resize((640, 360)))
p.stdin.close(); p.wait()
sh = Image.new("RGB", (1280, 720 + 0))
for k, s in enumerate(stills): sh.paste(s, ((k % 2) * 640, (k // 2) * 360))
for n in comps: sh.paste(Image.open(f"/tmp/plate_{n}.jpg").resize((320, 180)), (640 + (0 if n.startswith("RK-LO") else 320), 360))
sh.save("/tmp/look7.jpg", quality=84); print("mp4 bytes", os.path.getsize("/tmp/anim7.mp4"))
for tag, f in (("LOOK", "/tmp/look7.jpg"), ("MP4", "/tmp/anim7.mp4")):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
