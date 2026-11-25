"""Teste 6 (QA): animatic 3 planos com Ken Burns nas gravuras Rijksmuseum (recortes sem asas), tratamento leve e legenda. 960x540."""
import base64, subprocess, os, numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 960, 540; FPS = 24; N = 96
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.28 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.35, 0, 1))[..., None]
def grade(im, rng):
    a = np.asarray(im).astype(np.float32) / 255; g = a.mean(axis=2, keepdims=True); a = g + (a - g) * 0.72
    a = np.clip((a - 0.5) * 0.92 + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.06; a[..., 2] *= 0.90
    a = a * VIG + rng.normal(0, 0.018, (H, W, 1)); return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
def font():
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, 26)
    return ImageFont.load_default()
FT = font()
def caption(im, text):
    d = ImageDraw.Draw(im); w = d.textlength(text, font=FT); x = (W - w) / 2; y = H - 62
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2): d.text((x + dx, y + dy), text, font=FT, fill=(0, 0, 0))
    d.text((x, y), text, font=FT, fill=(244, 232, 205)); return im
shots = [("RK-LO-MENIGTE", (.50, .32, .50), (.56, .40, .40), "Ló saiu à porta, diante da multidão."),
         ("RK-SODOMA-CEGOS", (.72, .50, .45), (.74, .42, .40), "Os homens da cidade cercaram a casa."),
         ("RK-SODOMA-CEGOS", (.28, .52, .45), (.22, .60, .40), "E foram feridos de cegueira.")]
p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "/tmp/anim.mp4"], stdin=subprocess.PIPE)
rng = np.random.default_rng(7); stills = []; cache = {}
for name, a, b, txt in shots:
    if name not in cache: cache[name] = sepia(Image.open(f"hnc/quarentena/{name}.jpg").convert("RGB"))
    im = cache[name]
    for i in range(N):
        t = i / (N - 1); t = t * t * (3 - 2 * t)
        cx, cy, wf = [a[k] + (b[k] - a[k]) * t for k in range(3)]
        w = im.width * wf; h = w * 9 / 16; x0 = max(0, min(im.width - w, im.width * cx - w / 2)); y0 = max(0, min(im.height - h, im.height * cy - h / 2))
        fr = im.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((W, H), Image.LANCZOS)
        fr = caption(grade(fr, rng), txt); p.stdin.write(np.asarray(fr).tobytes())
        if i in (0, N - 1): stills.append(fr.resize((480, 270)))
p.stdin.close(); p.wait()
sh = Image.new("RGB", (960, 810))
for k, s in enumerate(stills): sh.paste(s, ((k % 2) * 480, (k // 2) * 270))
sh.save("/tmp/look6.jpg", quality=84); print("mp4 bytes", os.path.getsize("/tmp/anim.mp4"))
for tag, f in (("LOOK", "/tmp/look6.jpg"), ("MP4", "/tmp/anim.mp4")):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
