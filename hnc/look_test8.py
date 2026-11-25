"""Teste 8 (QA): TELA CHEIA. A = limpo (tilt+zoom lento sobre a chapa inteira, sem membros em foco). B = mesmo com stop-motion 8 fps (jitter + 'boiling') e poeira em suspensao. 1280x720, 8 s cada."""
import base64, subprocess, os, numpy as np, cv2
from PIL import Image
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H = 1280, 720; FPS = 24; N = 8 * FPS
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
im = Image.open("hnc/quarentena/RK-LO-MENIGTE.jpg").convert("RGB")
pl = im.crop((int(.215 * im.width), int(.192 * im.height), int(.738 * im.width), int(.775 * im.height)))  # chapa sem o nicho alado
base = sepia(pl); print("chapa", base.size)
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.30 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.45, 0, 1))[..., None]
def grade(fr, rng, grain=0.014):
    a = np.asarray(fr).astype(np.float32) / 255; g = a.mean(axis=2, keepdims=True); a = g + (a - g) * 0.72
    a = np.clip((a - 0.5) * 0.92 + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.06; a[..., 2] *= 0.90
    return a * VIG + rng.normal(0, grain, (H, W, 1))
def view(t, jx=0, jy=0):
    e = t * 0.7 + (0.5 - 0.5 * np.cos(np.pi * t)) * 0.3; z = 1.0 + 0.05 * e
    w = base.width / z; h = w * 9 / 16; x0 = (base.width - w) / 2 + jx; y0 = (base.height - h) * (0.10 + 0.80 * e) + jy   # tilt do topo ate o pe, devagar
    x0 = max(0, min(base.width - w, x0)); y0 = max(0, min(base.height - h, y0))
    return base.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))
def noise_field(rng, amp):
    lo = rng.normal(0, 1, (5, 8, 2)).astype(np.float32); f = cv2.resize(lo, (W, H), interpolation=cv2.INTER_CUBIC) * amp; return f
mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
class Dust:
    def __init__(s, rng, n=70): s.p = rng.uniform(0, 1, (n, 2)) * [W, H]; s.v = rng.uniform(.2, .8, (n, 2)) * [1, -1] * [1.2, 0.8]; s.r = rng.uniform(1, 2.6, n); s.ph = rng.uniform(0, 6, n)
    def draw(s, a, f):
        s.p += s.v; s.p[:, 0] %= W; s.p[:, 1] %= H; layer = np.zeros((H, W), np.float32)
        for (x, y), r, ph in zip(s.p, s.r, s.ph): cv2.circle(layer, (int(x), int(y)), int(r), float(0.55 + 0.35 * np.sin(f * .15 + ph)), -1, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), 1.3); return 1 - (1 - a) * (1 - layer[..., None] * np.array([.95, .72, .42], np.float32))
def run(path, stop):
    rng = np.random.default_rng(3); dust = Dust(rng) if stop else None
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "29", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    jx = jy = 0; field = None; frames = []
    for i in range(N):
        t = i / (N - 1)
        if stop:
            if i % 3 == 0: jx, jy = rng.normal(0, 4), rng.normal(0, 4); field = noise_field(rng, 2.2); pose = np.random.default_rng(i)
            fr = np.asarray(view(t, jx, jy)); fr = cv2.remap(fr, mx + field[..., 0], my + field[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            a = grade(Image.fromarray(fr), pose, 0.03); a = dust.draw(a, i)
        else: a = grade(view(t), rng)
        fade = min(1, i / 12, (N - 1 - i) / 12); a = a * fade; b = (np.clip(a, 0, 1) * 255).astype(np.uint8); p.stdin.write(b.tobytes())
        if i in (20, 100, 170): frames.append(Image.fromarray(b).resize((640, 360)))
    p.stdin.close(); p.wait(); return frames
fa = run("/tmp/anim8a.mp4", False); fb = run("/tmp/anim8b.mp4", True)
sh = Image.new("RGB", (1920, 720))
for k, f in enumerate(fa): sh.paste(f, (k * 640, 0))
for k, f in enumerate(fb): sh.paste(f, (k * 640, 360))
sh.save("/tmp/look8.jpg", quality=84); print("bytes", os.path.getsize("/tmp/anim8a.mp4"), os.path.getsize("/tmp/anim8b.mp4"))
for tag, f in (("LOOK", "/tmp/look8.jpg"), ("MPA", "/tmp/anim8a.mp4"), ("MPB", "/tmp/anim8b.mp4")):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
