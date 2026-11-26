"""Motor ESTILO A v4 (= visual do v3 aprovado, mais rapido): a gravura e tratada UMA vez por plano (DOF, cor, bloom, raios);
por quadro so recorte+paralaxe+atmosfera+grao+legenda. Modo previa: 960x540, 24 fps.
Uso: python -I hnc/engine_d.py hnc/shots_xxx.json /tmp/saida.mp4 [preview]  (le hnc/quarentena/<ID>.jpg)."""
import base64, json, subprocess, sys, os, time, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg
Image.MAX_IMAGE_PIXELS = None
cfg = json.load(open(sys.argv[1])); OUT = sys.argv[2]; PREVIEW = len(sys.argv) > 3 and sys.argv[3] == "preview"
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H, FPS = cfg["w"], cfg["h"], cfg.get("fps", 30)
if PREVIEW: W, H, FPS = 960, 540, 24
SC = H / 1080; OV = int(cfg["overlap_s"] * FPS); CAPW = 1800 if PREVIEW else 3600; TAG = "P" if PREVIEW else ""
GRAY = cv2.COLOR_RGB2GRAY; WARMC = np.array([1.0, .85, .6], np.float32); T0 = time.time()
def sepia(im):
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    return Image.fromarray((np.clip(np.stack([g, g * .86, g * .66], 2) * 1.08, 0, 1) * 255).astype(np.uint8))
_pipe = [None]
def depth_for(im):
    try:
        if _pipe[0] is None:
            from transformers import pipeline
            _pipe[0] = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
        sm = im.copy(); sm.thumbnail((896, 896)); o = _pipe[0](sm)["depth"]
        d = np.asarray(o.resize(im.size, Image.BILINEAR)).astype(np.float32); d = (d - d.min()) / (d.max() - d.min() + 1e-6); src = "modelo"
    except Exception as e:
        print("profundidade: fallback gradiente:", repr(e)[:160]); g = np.linspace(0, 1, im.height, dtype=np.float32)[:, None] ** 1.2; d = np.repeat(g, im.width, axis=1); src = "gradiente"
    d = cv2.GaussianBlur(d, (0, 0), max(2, im.width / 350)); return d.astype(np.float32), src
P = {}; D = {}
for k, v in cfg["plates"].items():
    im = Image.open(f"hnc/quarentena/{k}.jpg").convert("RGB"); b = v["box"]
    if b == "auto":
        sm = np.asarray(im.resize((800, int(800 * im.height / im.width)))).astype(np.float32); e = max(2, int(sm.shape[0] * .02))
        edge = np.concatenate([sm[:e].reshape(-1, 3), sm[-e:].reshape(-1, 3), sm[:, :e].reshape(-1, 3), sm[:, -e:].reshape(-1, 3)]); bg = np.median(edge, axis=0)
        d_ = np.abs(sm - bg).max(axis=2) > 22; c = np.where(d_.mean(0) > .30)[0]; r = np.where(d_.mean(1) > .30)[0]
        b = [c[0] / sm.shape[1] + .01, r[0] / sm.shape[0] + .01, c[-1] / sm.shape[1] - .01, r[-1] / sm.shape[0] - .01]
    im = im.crop((int(b[0] * im.width), int(b[1] * im.height), int(b[2] * im.width), int(b[3] * im.height)))
    if im.width > CAPW: im = im.resize((CAPW, int(im.height * CAPW / im.width)), Image.LANCZOS)
    P[k] = sepia(im) if v["sepia"] else im; D[k], src = depth_for(P[k]); print("chapa", k, P[k].size, "profundidade:", src)
yy, xx = np.mgrid[0:H, 0:W]; VIG = (1 - 0.30 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.45, 0, 1))[..., None].astype(np.float32)
MX, MY = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
rng = np.random.default_rng(21)
HAZE = cv2.resize(rng.random((7, 12)).astype(np.float32), (int(W * 1.8), H), interpolation=cv2.INTER_CUBIC); HAZE = cv2.GaussianBlur(HAZE, (0, 0), 30 * SC); HAZE = (HAZE - HAZE.min()) / (HAZE.max() - HAZE.min())
WY = ((1 - np.linspace(0, 1, H, dtype=np.float32))[:, None] ** 0.8).astype(np.float32)
FTBIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(68 * SC))
COL = np.array([.957, .91, .804], np.float32)
CAPV2 = cfg.get("caption_style") == "v2"
KARA = CAPV2 and cfg.get("karaoke", True)
OLIVE = np.array(cfg.get("karaoke_rgb", [.72, .78, .40]), np.float32)  # verde oliva claro
def _font(px):
    for f in ("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f): return ImageFont.truetype(f, px), os.path.basename(f)
    return ImageFont.load_default(), "default"
def cap_masks(text, ref=None, center=False):
    f_ = lambda m: np.asarray(m.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255
    if not CAPV2:
        big = Image.new("L", (W * 2, H * 2), 0); d = ImageDraw.Draw(big); w = d.textlength(text, font=FTBIG); x = (W * 2 - w) / 2; y = H * 2 - int(164 * SC); d.text((x, y), text, font=FTBIG, fill=255)
        mf = max(3, int(9 * SC) | 1); ol = big.filter(ImageFilter.MaxFilter(mf)).filter(ImageFilter.GaussianBlur(2 * SC)); return f_(big), np.clip(f_(ol) * 1.4, 0, 1), None
    big = Image.new("L", (W * 2, H * 2), 0); d = ImageDraw.Draw(big); fs = int(92 * SC); ft, fname = _font(fs); maxw = W * 2 * 0.78; lines = []; cur = ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=ft) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    lh = int(fs * 1.3); top = (int(H * 2 * 0.635) - lh * len(lines) // 2) if center == 'mid_low' else ((H * 2 - lh * len(lines)) // 2 if center else H * 2 - int(190 * SC) - lh * len(lines))
    wl = []; tot = sum(len(w_) + 1 for w_ in text.split()) or 1; acc = 0
    for n, ln in enumerate(lines):
        x0 = (W * 2 - d.textlength(ln, font=ft)) / 2; y0 = top + n * lh; d.text((x0, y0), ln, font=ft, fill=255); pre = ""
        for wd in ln.split():
            xa = x0 + d.textlength(pre, font=ft); xb = xa + d.textlength(wd, font=ft); pre += wd + " "; w8 = len(wd) + 1
            wl.append((xa / 2, xb / 2, y0 / 2, (y0 + lh) / 2, acc / tot, (acc + w8) / tot)); acc += w8
    if ref:
        fr_, _ = _font(int(56 * SC)); d.text((W * 2 - int(120 * SC) - d.textlength(ref, font=fr_), int(100 * SC)), ref, font=fr_, fill=255)
    ol = big.filter(ImageFilter.MaxFilter(max(3, int(11 * SC) | 1))).filter(ImageFilter.GaussianBlur(5 * SC)); return f_(big), np.clip(f_(ol) * 1.7, 0, 1), wl
_by = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]; BAND = (0.55 * np.clip((_by - 0.60) / 0.40, 0, 1) ** 1.6).astype(np.float32)
MIDBAND = (0.42 * np.exp(-(((_by - 0.635) / 0.14) ** 2))).astype(np.float32)  # faixa suave atras da legenda centralizada (um pouco abaixo do meio)
def cap_al(i, F):
    if not CAPV2: return min(1, i / 14, (F - 1 - i) / 14)
    dl = min(0.5 * FPS, 0.15 * F); fi = min(0.6 * FPS, 0.2 * F); fo = min(0.5 * FPS, 0.2 * F)
    return min(sstep((i - dl) / fi), sstep(((F - 1 - i) - 0.1 * FPS) / fo))
def kara_map(wl, F, timing=None):
    # mapa (H,W,2) com [inicio, fim] (em quadros) da palavra a que cada pixel pertence; so a palavra "da vez" fica oliva, o resto branco.
    # timing opcional por plano: [[ini_s, fim_s], ...] por palavra (sincronia com a locucao); senao, proporcional ao tamanho das palavras.
    dl = min(0.5 * FPS, 0.15 * F); fi = min(0.6 * FPS, 0.2 * F); ts = dl + 0.5 * fi; te = max(ts + 1, F - 0.1 * FPS - min(0.5 * FPS, 0.2 * F) - 0.15 * FPS)
    T = np.full((H, W, 2), 1e9, np.float32)
    for k, (xa, xb, ya, yb, f0, f1) in enumerate(wl):
        a_, b_ = (timing[k][0] * FPS, timing[k][1] * FPS) if timing and k < len(timing) else (ts + f0 * (te - ts), ts + f1 * (te - ts))
        x0, x1, y0, y1 = max(0, int(xa)), min(W, int(xb) + 1), max(0, int(ya)), min(H, int(yb) + 1)
        T[y0:y1, x0:x1, 0] = a_; T[y0:y1, x0:x1, 1] = b_
    return T
class Dust:
    def __init__(s, n=55): s.p = rng.uniform(0, 1, (n, 2)) * [W, H]; s.z = rng.uniform(0.3, 1.0, n); s.v = (rng.uniform(-.25, .25, (n, 2)) * [1, .6] + [.15, -.12]) * SC; s.ph = rng.uniform(0, 6, n)
    def layer(s, f, camdx):
        s.p += s.v * s.z[:, None] * 1.4; s.p[:, 0] -= camdx * s.z * 0.6 * SC; s.p[:, 0] %= W; s.p[:, 1] %= H; L = np.zeros((H, W), np.float32)
        for (x, y), z, ph in zip(s.p, s.z, s.ph): cv2.circle(L, (int(x), int(y)), max(1, int((1 + z * 1.6) * SC)), float((0.30 + 0.30 * np.sin(f * .09 + ph)) * z), -1, cv2.LINE_AA)
        return cv2.GaussianBlur(L, (0, 0), 1.2 * SC)
class Embers:
    def __init__(s, n=70): s.p = rng.uniform(0, 1, (n, 2)) * [W, H]; s.z = rng.uniform(0.3, 1.0, n); s.ph = rng.uniform(0, 6, n); s.vx = rng.uniform(-.6, .6, n)
    def layer(s, f):
        s.p[:, 1] -= (1.6 + 2.2 * s.z) * SC; s.p[:, 0] += (s.vx + 0.8 * np.sin(f * .05 + s.ph)) * SC; s.p[:, 0] %= W
        low = s.p[:, 1] < -10; s.p[low, 1] = H + 10; s.p[low, 0] = rng.uniform(0, W, low.sum()); L = np.zeros((H, W), np.float32)
        for (x, y), z, ph in zip(s.p, s.z, s.ph): cv2.circle(L, (int(x), int(y)), max(1, int((1 + z * 2) * SC)), float((0.55 + 0.45 * np.sin(f * .3 + ph)) * z), -1, cv2.LINE_AA)
        return cv2.GaussianBlur(L, (0, 0), 1.0 * SC)
def sstep(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
def blur(x, sg):
    if sg <= 2.5: return cv2.GaussianBlur(x, (0, 0), max(sg, 0.3))
    ds = int(min(8, max(2, sg / 1.5))); h, w = x.shape[:2]
    sm = cv2.resize(x, (max(1, w // ds), max(1, h // ds)), interpolation=cv2.INTER_AREA); sm = cv2.GaussianBlur(sm, (0, 0), sg / ds)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
def rays(hi, cx, cy, n=10, k=0.035):
    h, w = hi.shape; ds = 4; hs = cv2.resize(hi, (w // ds, h // ds), interpolation=cv2.INTER_AREA); acc = np.zeros_like(hs)
    for j in range(1, n + 1):
        M = cv2.getRotationMatrix2D((cx / ds, cy / ds), 0, 1 + k * j / n * 3); acc += cv2.warpAffine(hs, M, (w // ds, h // ds), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * (1 - j / (n + 1))
    return cv2.resize(acc / n, (w, h), interpolation=cv2.INTER_LINEAR)
class Prep:
    """tratamento da gravura inteira, feito 1x por plano."""
    def __init__(s, sh):
        t = time.time(); im = P[sh["src"]]; dm = D[sh["src"]]; fx = sh.get("fx", {}); wf = (sh["a"][2] + sh["b"][2]) / 2; k = max(0.5, im.width * wf / W)
        base = np.asarray(im).astype(np.float32) * np.float32(1 / 255); gr = fx.get("grade", {}); sat = gr.get("sat", 0.72); warm = gr.get("warm", 1.0); con = gr.get("contrast", 0.92)
        dof = fx.get("dof", 0.0); f0, f1 = fx.get("focus", [0.35, 0.65]); bl = fx.get("bloom", 0.5); ry = fx.get("rays", 0.0)
        focs = ([f0, f1] if abs(f1 - f0) > 0.05 else [(f0 + f1) / 2]) if dof else [None]; s.imgs = []
        for foc in focs:
            a = base
            if foc is not None:
                dist = np.abs(dm - foc)[..., None]; b1 = blur(a, 2.2 * dof * SC * k); b2 = blur(a, 5.5 * dof * SC * k)
                w1 = np.clip((dist - 0.12) / 0.18, 0, 1); w2 = np.clip((dist - 0.30) / 0.25, 0, 1); a = a * (1 - w1) + b1 * w1; a = a * (1 - w2) + b2 * w2
            else: a = a.copy()
            g = cv2.cvtColor(a, GRAY)[..., None]; a = g + (a - g) * sat; a = np.clip((a - 0.5) * con + 0.5 + 0.02, 0, 1); a[..., 0] *= 1.0 + 0.06 * warm; a[..., 2] *= 1.0 - 0.10 * warm
            if bl: hi = np.clip(a - 0.70, 0, 1); a = a + blur(hi, 16 * SC * k) * bl * WARMC
            if ry:
                hi2 = np.clip(cv2.cvtColor(np.ascontiguousarray(a, dtype=np.float32), GRAY) - 0.78, 0, 1).astype(np.float32); ys, xs = np.nonzero(hi2[::4, ::4] > 0.05)
                if len(xs) > 50: a = a + rays(cv2.GaussianBlur(hi2, (0, 0), 6 * k), float(xs.mean() * 4), float(ys.mean() * 4))[..., None] * ry * WARMC
            s.imgs.append(Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)))
        s.dm = Image.fromarray(dm, mode="F"); s.sec = round(time.time() - t, 1); print(f"prep {sh['src']} em {s.sec}s", flush=True)
shots = cfg["shots"]
for s in shots:
    s["_black"] = s.get("kind") == "black"
    if not s["_black"]: assert min(s["a"][2], s["b"][2]) >= 0.55, f"janela estreita demais em {s['src']}"
    tx, ol, wl = cap_masks(s.get("cap", ""), s.get("ref"), center=("mid_low" if s.get("cap_pos") == "mid_low" else bool(s["_black"] or s.get("cap_pos") == "center"))); s["_tx"], s["_ol"] = tx, ol
    s["_T"] = kara_map(wl, int(s["dur"] * FPS), s.get("kara")) if (KARA and wl) else None
    band = MIDBAND if (CAPV2 and s.get("cap_pos") == "mid_low") else (BAND if (CAPV2 and not s["_black"] and s.get("cap_pos") != "center") else 0)
    s["_band"] = band; s["_K1"] = (1 - (0.75 if not CAPV2 else 0.85) * ol) * (1 - tx) * (1 - band); s["_C1"] = COL * tx; s["_dust"] = Dust(); s["_emb"] = Embers()
WHITE = np.array(cfg.get("karaoke_base_rgb", [.98, .98, .96]), np.float32)
def kcol(s, i):
    if s["_T"] is None: return s["_C1"]
    sf = np.float32(max(2, 0.08 * FPS)); T = s["_T"]
    m = np.clip((np.float32(i) - T[..., :1]) / sf + 0.5, 0, 1) * np.clip((T[..., 1:] - np.float32(i)) / sf + 0.5, 0, 1)
    return (WHITE + (OLIVE - WHITE) * m) * s["_tx"]
MCOL = np.array([[1.0, .95, 1.0], [.88, .78, .55], [.66, .5, .2]], np.float32)
def render(s, i, F, pr):
    if s["_black"]:
        al = cap_al(i, F); return np.clip((kcol(s, i) if s["_T"] is not None else COL * s["_tx"]) * al, 0, 1)
    t = i / (F - 1); e = 0.5 * t + 0.5 * sstep(t); fx = s.get("fx", {}); im = pr.imgs[0]
    cx, cy, wf = [s["a"][k] + (s["b"][k] - s["a"][k]) * e for k in range(3)]
    hh = fx.get("handheld", 0.0012); ph = s["_dust"].ph[1]
    cx += hh * (np.sin(i * 0.037 + ph) + 0.5 * np.sin(i * 0.091 + 2 * ph)); cy += hh * (np.sin(i * 0.029 + 3 * ph) + 0.5 * np.sin(i * 0.083 + ph))
    w = im.width * wf; h = w * 9 / 16
    if h > im.height: h = im.height; w = h * 16 / 9
    x0 = max(0, min(im.width - w, im.width * cx - w / 2)); y0 = max(0, min(im.height - h, im.height * cy - h / 2)); box = (x0, y0, x0 + w, y0 + h)
    fr = np.asarray(im.resize((W, H), Image.LANCZOS, box=box))
    if len(pr.imgs) == 2: fr = cv2.addWeighted(fr, 1 - e, np.asarray(pr.imgs[1].resize((W, H), Image.LANCZOS, box=box)), e, 0)
    par = fx.get("parallax", 14) * SC
    if par:
        dd = np.asarray(pr.dm.resize((W, H), Image.BILINEAR, box=box)); sign = 1 if s["b"][0] >= s["a"][0] else -1
        off = par * (e - 0.5) * 2 * sign * (dd - 0.5); fr = cv2.remap(fr, MX + off, MY + 0.35 * off, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    a = fr.astype(np.float32) * np.float32(1 / 255); a = cv2.addWeighted(a, 1.45, cv2.GaussianBlur(a, (0, 0), 1.4 * SC), -0.45, 0)
    hz = fx.get("haze", 0.06); sh = int((t * 0.35 + s["_dust"].ph[0] * 0.01) * W * 0.8) % int(W * 0.8)
    L = cv2.merge([(HAZE[:, sh:sh + W] * WY) * np.float32(hz),
                   s["_dust"].layer(i, (cx - s["a"][0]) * 8 if i else 0) * np.float32(0.6) if fx.get("dust", True) else np.zeros((H, W), np.float32),
                   s["_emb"].layer(i) * np.float32(fx["embers"]) if fx.get("embers") else np.zeros((H, W), np.float32)])
    a = a + cv2.transform(L, MCOL)
    if fx.get("fire"): a = a * np.float32(1 + 0.03 * np.sin(i * 0.8) + 0.02 * rng.normal())
    a = np.ascontiguousarray(a, dtype=np.float32); lum = cv2.cvtColor(a, GRAY); gn = rng.standard_normal((H, W), dtype=np.float32)
    a = a * VIG + (gn * np.float32(0.016) * (np.float32(1.15) - lum))[..., None]; al = cap_al(i, F)
    if al >= 1: a = a * s["_K1"] + kcol(s, i)
    else: a = a * (1 - s["_band"] * al) * (1 - s["_ol"] * al * (0.75 if not CAPV2 else 0.85)); a = a * (1 - s["_tx"] * al) + kcol(s, i) * al
    return np.clip(a, 0, 1)
for si, s in enumerate(shots): s["_ov"] = OV if (si > 0 and s.get("in", "dissolve") == "dissolve") else 0
starts = []; pos = 0
for si, s in enumerate(shots): pos -= s["_ov"]; starts.append(pos); pos += int(s["dur"] * FPS)
total = pos
p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "24" if PREVIEW else "21", "-preset", "veryfast" if PREVIEW else "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
stills = {}; PR = {}; TR = time.time()
for g in range(total):
    out = None
    for si, s in enumerate(shots):
        F = int(s["dur"] * FPS); i = g - starts[si]
        if not 0 <= i < F: continue
        if si not in PR: PR[si] = None if s["_black"] else Prep(s)
        fr = render(s, i, F, PR[si]); ov = s["_ov"]; m = 1.0 if (ov == 0 or i >= ov) else sstep(i / ov)
        fd = 1.0
        if s.get("in") == "dip": fd = min(fd, sstep(i / (0.4 * FPS)))
        if si + 1 < len(shots) and shots[si + 1].get("in") == "dip": fd = min(fd, sstep((F - 1 - i) / (0.4 * FPS)))
        fr = fr * np.float32(fd)
        out = fr if out is None else out * (1 - m) + fr * m + (np.float32(0.05 * np.sin(np.pi * m)) * WARMC if 0 < m < 1 else 0)
        if i in (F // 3, 2 * F // 3) and not s["_black"]: stills[(si, i)] = Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8)).resize((480, 270))
    for si in list(PR):
        if g >= starts[si] + int(shots[si]["dur"] * FPS): del PR[si]
    fade = min(1, g / 15, (total - 1 - g) / 15); p.stdin.write((np.clip(out * fade, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait(); el = time.time() - TR
print(f"PERF modo={'previa' if PREVIEW else 'final'} {W}x{H} {FPS}fps quadros={total} dur_s={round(total / FPS, 1)} render_s={round(el, 1)} s_por_quadro={round(el / total, 3)} total_s={round(time.time() - T0, 1)} bytes={os.path.getsize(OUT)}")
ks = sorted(stills); sh_ = Image.new("RGB", (960, 270 * ((len(ks) + 1) // 2)))
for n, k in enumerate(ks): sh_.paste(stills[k], ((n % 2) * 480, (n // 2) * 270))
SHEET = OUT + ".sheet.jpg"; sh_.save(SHEET, quality=82)
for tag, f in ((TAG + "LOOK", SHEET), (TAG + "MP4", OUT)):
    b64 = base64.b64encode(open(f, "rb").read()).decode(); print(f"{tag}B64START"); [print(b64[i:i + 4000]) for i in range(0, len(b64), 4000)]; print(f"{tag}B64END", len(b64))
