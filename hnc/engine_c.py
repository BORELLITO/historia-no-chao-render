"""Motor ESTILO A v3 (DOF por profundidade, raios de luz, brasas, tremor de camera, nitidez, crf 20): tela cheia + paralaxe 2.5D (profundidade), 30 fps, bloom, nevoa, poeira, flicker de fogo, legenda suave.
Uso: python -I hnc/engine_b.py hnc/shots_xxx.json /tmp/saida.mp4  (le hnc/quarentena/<ID>.jpg)."""
import base64, json, subprocess, sys, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
cfg = json.load(open(sys.argv[1])); OUT = sys.argv[2]
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H, FPS = cfg["w"], cfg["h"], cfg.get("fps", 30); OV = int(cfg["overlap_s"] * FPS)
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
_pipe = [None]
def depth_for(im):
    """mapa de profundidade 0..1 (1 = perto). Modelo Depth-Anything-V2-Small; se falhar, gradiente vertical (baixo = perto)."""
    try:
        if _pipe[0] is None:
            from transformers import pipeline
            _pipe[0] = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
        sm = im.copy(); sm.thumbnail((896, 896)); o = _pipe[0](sm)["depth"]
        d = np.asarray(o.resize(im.size, Image.BILINEAR)).astype(np.float32); d = (d - d.min()) / (d.max() - d.min() + 1e-6); src = "modelo"
    except Exception as e:
        print("profundidade: fallback gradiente:", repr(e)[:160]); g = np.linspace(0, 1, im.height, dtype=np.float32)[:, None] ** 1.2; d = np.repeat(g, im.width, axis=1); src = "gradiente"
    d = cv2.GaussianBlur(d, (0, 0), max(2, im.width / 350)); return d, src
P = {}; D = {}
for k, v in cfg["plates"].items():
    im = Image.open(f"hnc/quarentena/{k}.jpg").convert("RGB"); b = v["box"]
    if b == "auto":
        sm = np.asarray(im.resize((800, int(800 * im.height / im.width)))).astype(np.float32); e = max(2, int(sm.shape[0] * .02))
        edge = np.concatenate([sm[:e].reshape(-1, 3), sm[-e:].reshape(-1, 3), sm[:, :e].reshape(-1, 3), sm[:, -e:].reshape(-1, 3)]); bg = np.median(edge, axis=0)
        d_ = np.abs(sm - bg).max(axis=2) > 22; c = np.where(d_.mean(0) > .30)[0]; r = np.where(d_.mean(1) > .30)[0]
        b = [c[0] / sm.shape[1] + .01, r[0] / sm.shape[0] + .01, c[-1] / sm.shape[1] - .01, r[-1] / sm.shape[0] - .01]
    im = im.crop((int(b[0] * im.width), int(b[1] * im.height), int(b[2] * im.width), int(b[3] * im.height)))
    if im.width > 3600: im = im.resize((3600, int(im.height * 3600 / im.width)), Image.LANCZOS)
    P[k] = sepia(im) if v["sepia"] else im; D[k], src = depth_for(P[k]); print("chapa", k, P[k].size, "profundidade:", src)
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.30 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.45, 0, 1))[..., None].astype(np.float32)
MX, MY = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
rng = np.random.default_rng(21)
HAZE = cv2.resize(rng.random((7, 12)).astype(np.float32), (int(W * 1.8), H), interpolation=cv2.INTER_CUBIC); HAZE = cv2.GaussianBlur(HAZE, (0, 0), 30); HAZE = (HAZE - HAZE.min()) / (HAZE.max() - HAZE.min())
FTBIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 68)
def cap_masks(text):
    big = Image.new("L", (W * 2, H * 2), 0); d = ImageDraw.Draw(big); w = d.textlength(text, font=FTBIG); x = (W * 2 - w) / 2; y = H * 2 - 164; d.text((x, y), text, font=FTBIG, fill=255)
    ol = big.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2)); tx = big
    f = lambda m: np.asarray(m.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255
    return f(tx), np.clip(f(ol) * 1.4, 0, 1)
class Dust:
    def __init__(s, n=55): s.p = rng.uniform(0, 1, (n, 2)) * [W, H]; s.z = rng.uniform(0.3, 1.0, n); s.v = rng.uniform(-.25, .25, (n, 2)) * [1, .6] + [.15, -.12]; s.ph = rng.uniform(0, 6, n)
    def layer(s, f, camdx):
        s.p += s.v * s.z[:, None] * 1.4; s.p[:, 0] -= camdx * s.z * 0.6; s.p[:, 0] %= W; s.p[:, 1] %= H; L = np.zeros((H, W), np.float32)
        for (x, y), z, ph in zip(s.p, s.z, s.ph): cv2.circle(L, (int(x), int(y)), 1 + int(z * 1.6), float((0.30 + 0.30 * np.sin(f * .09 + ph)) * z), -1, cv2.LINE_AA)
        return cv2.GaussianBlur(L, (0, 0), 1.2)
class Embers:
    def __init__(s, n=70): s.p = rng.uniform(0, 1, (n, 2)) * [W, H]; s.z = rng.uniform(0.3, 1.0, n); s.ph = rng.uniform(0, 6, n); s.vx = rng.uniform(-.6, .6, n)
    def layer(s, f):
        s.p[:, 1] -= (1.6 + 2.2 * s.z); s.p[:, 0] += s.vx + 0.8 * np.sin(f * .05 + s.ph); s.p[:, 0] %= W
        low = s.p[:, 1] < -10; s.p[low, 1] = H + 10; s.p[low, 0] = rng.uniform(0, W, low.sum()); L = np.zeros((H, W), np.float32)
        for (x, y), z, ph in zip(s.p, s.z, s.ph): cv2.circle(L, (int(x), int(y)), 1 + int(z * 2), float((0.55 + 0.45 * np.sin(f * .3 + ph)) * z), -1, cv2.LINE_AA)
        return cv2.GaussianBlur(L, (0, 0), 1.0)
def lb(x, sg):
    """blur barato: reduz a metade, desfoca, volta (so p/ efeitos de baixa frequencia)."""
    sm = cv2.resize(x, (W // 2, H // 2), interpolation=cv2.INTER_AREA); sm = cv2.GaussianBlur(sm, (0, 0), sg / 2)
    return cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
def rays(hi, cx, cy, n=10, k=0.035):
    hs = cv2.resize(hi, (W // 2, H // 2), interpolation=cv2.INTER_AREA); acc = np.zeros_like(hs)
    for j in range(1, n + 1):
        M = cv2.getRotationMatrix2D((cx / 2, cy / 2), 0, 1 + k * j / n * 3); acc += cv2.warpAffine(hs, M, (W // 2, H // 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * (1 - j / (n + 1))
    return cv2.resize(acc / n, (W, H), interpolation=cv2.INTER_LINEAR)
def sstep(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
shots = cfg["shots"]
for s in shots:
    assert min(s["a"][2], s["b"][2]) >= 0.55, f"janela estreita demais em {s['src']}"
    s["_tx"], s["_ol"] = cap_masks(s["cap"]); s["_dust"] = Dust(); s["_emb"] = Embers()
def render(s, i, F):
    t = i / (F - 1); e = 0.5 * t + 0.5 * sstep(t); fx = s.get("fx", {})
    cx, cy, wf = [s["a"][k] + (s["b"][k] - s["a"][k]) * e for k in range(3)]; im = P[s["src"]]; dm = D[s["src"]]
    hh = fx.get("handheld", 0.0012); ph = s["_dust"].ph[1]
    cx += hh * (np.sin(i * 0.037 + ph) + 0.5 * np.sin(i * 0.091 + 2 * ph)); cy += hh * (np.sin(i * 0.029 + 3 * ph) + 0.5 * np.sin(i * 0.083 + ph))
    w = im.width * wf; h = w * 9 / 16
    if h > im.height: h = im.height; w = h * 16 / 9
    x0 = max(0, min(im.width - w, im.width * cx - w / 2)); y0 = max(0, min(im.height - h, im.height * cy - h / 2)); box = (x0, y0, x0 + w, y0 + h)
    fr = np.asarray(im.resize((W, H), Image.LANCZOS, box=box)); par = fx.get("parallax", 14)
    dd = np.asarray(Image.fromarray(dm, mode="F").resize((W, H), Image.BILINEAR, box=box)); sign = 1 if s["b"][0] >= s["a"][0] else -1
    if par:
        off = par * (e - 0.5) * 2 * sign * (dd - 0.5); fr = cv2.remap(fr, MX + off, MY + 0.35 * off, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    a = fr.astype(np.float32) * np.float32(1 / 255)
    dof = fx.get("dof", 0.0)
    if dof:
        f0, f1 = fx.get("focus", [0.35, 0.65]); foc = f0 + (f1 - f0) * e; dist = np.abs(dd - foc)[..., None]
        b1 = lb(a, 2.2 * dof); b2 = lb(a, 5.5 * dof)
        w1 = np.clip((dist - 0.12) / 0.18, 0, 1); w2 = np.clip((dist - 0.30) / 0.25, 0, 1)
        a = a * (1 - w1) + b1 * w1; a = a * (1 - w2) + b2 * w2
    bl0 = cv2.GaussianBlur(a, (0, 0), 1.4); a = np.clip(a + (a - bl0) * 0.45, 0, 1)
    gr = fx.get("grade", {}); sat = gr.get("sat", 0.72); warm = gr.get("warm", 1.0); con = gr.get("contrast", 0.92)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)[..., None]; a = g + (a - g) * sat; a = np.clip((a - 0.5) * con + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.0 + 0.06 * warm; a[..., 2] *= 1.0 - 0.10 * warm
    bl = fx.get("bloom", 0.5); warmc = np.array([1.0, .85, .6], np.float32)
    if bl: hi = np.clip(a - 0.70, 0, 1); a = a + lb(hi, 16) * bl * warmc
    ry = fx.get("rays", 0.0)
    if ry:
        hi = np.clip(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY) - 0.78, 0, 1).astype(np.float32); ys, xs = np.nonzero(hi > 0.05)
        if len(xs) > 50: a = a + rays(hi, float(xs.mean()), float(ys.mean()))[..., None] * ry * warmc
    hz = fx.get("haze", 0.06)
    if hz:
        sh = int((t * 0.35 + s["_dust"].ph[0] * 0.01) * W * 0.8) % int(W * 0.8); layer = HAZE[:, sh:sh + W]; wy = (1 - np.linspace(0, 1, H, dtype=np.float32))[:, None] ** 0.8
        a = a + (layer * wy)[..., None] * hz * np.array([1.0, .88, .66], np.float32)
    if fx.get("fire"): a = a * np.float32(1 + 0.03 * np.sin(i * 0.8) + 0.02 * rng.normal())
    if fx.get("dust", True): a = a + s["_dust"].layer(i, (cx - s["a"][0]) * 8 if i else 0)[..., None] * np.array([.95, .78, .5], np.float32) * 0.6
    if fx.get("embers"): a = a + s["_emb"].layer(i)[..., None] * np.array([1.0, .55, .2], np.float32) * fx["embers"]
    a = np.ascontiguousarray(a, dtype=np.float32); lum = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)[..., None]; gn = rng.standard_normal((H, W), dtype=np.float32)[..., None]
    a = a * VIG + gn * 0.016 * (1.15 - lum); al = min(1, i / 14, (F - 1 - i) / 14)
    col = np.array([.957, .91, .804], np.float32)
    a = a * (1 - s["_ol"] * al * 0.75); a = a * (1 - s["_tx"] * al) + col * s["_tx"] * al
    return np.clip(a, 0, 1)
starts = []; pos = 0
for s in shots: starts.append(pos); pos += int(s["dur"] * FPS) - OV
total = pos + OV
p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
stills = {}
for g in range(total):
    out = None
    for si, s in enumerate(shots):
        F = int(s["dur"] * FPS); i = g - starts[si]
        if not 0 <= i < F: continue
        fr = render(s, i, F)
        m = 1.0 if (si == 0 or i >= OV) else sstep(i / OV)
        if si < len(shots) - 1 and i >= F - OV: m = 1.0
        out = fr if out is None else out * (1 - m) + fr * m + (0.05 * np.sin(np.pi * m) * np.array([1.0, .85, .6], np.float32) if 0 < m < 1 else 0)
        if i in (F // 3, 2 * F // 3): stills[(si, i)] = Image.fromarray((fr * 255).astype(np.uint8)).resize((480, 270))
    fade = min(1, g / 15, (total - 1 - g) / 15); p.stdin.write((np.clip(out * fade, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait(); print("frames", total, "dur_s", round(total / FPS, 1), "bytes", os.path.getsize(OUT))
ks = sorted(stills); sh = Image.new("RGB", (960, 270 * ((len(ks) + 1) // 2)))
for n, k in enumerate(ks): sh.paste(stills[k], ((n % 2) * 480, (n // 2) * 270))
sh.save("/tmp/sheet.jpg", quality=82)
for tag, f in (("LOOK", "/tmp/sheet.jpg"), ("MP4", OUT)):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
