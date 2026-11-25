#!/usr/bin/env python3
"""QA tecnico de legendas HNC (so le o shots.json; opcional: video para medir simetria nos quadros).
Uso: python -I qa_legenda.py shots.json [video.mp4]   -> sai 1 se houver ERRO."""
import json, sys, re, os
from PIL import ImageFont, Image, ImageDraw
cfg = json.load(open(sys.argv[1], encoding="utf-8")); W, H = 1920, 1080; SC = 1.0; FPS = 24
OV = cfg.get("overlap", 0.8); errs = []; warns = []; info = []
def E(m): errs.append(m)
def Wn(m): warns.append(m)
def font(px):
    for f in ("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"):
        if os.path.exists(f): return ImageFont.truetype(f, px)
ft = font(92); d = ImageDraw.Draw(Image.new("L", (10, 10)))
def wrap(text, maxw):
    lines = []; cur = ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=ft) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines
BOOKREF = re.compile(r"^[A-ZÀ-Ú][a-zà-ú]+ \d{1,3}:\d{1,3}([-–]\d{1,3})?$")
t = 0.0
for i, s in enumerate(cfg["shots"], 1):
    cap = s.get("cap", ""); ref = s.get("ref"); dur = s["dur"]; tag = f"plano {i}"
    if not cap: Wn(f"{tag}: sem legenda"); continue
    # pontuacao / espacamento
    if cap != cap.strip(): E(f"{tag}: espaco nas pontas")
    if "  " in cap: E(f"{tag}: espaco duplo")
    if re.search(r"\s[,.;:!?]", cap): E(f"{tag}: espaco antes de pontuacao")
    if re.search(r"[,.;:!?][^\s\"')”.!?]", cap): E(f"{tag}: falta espaco depois de pontuacao")
    if not re.search(r"[.!?…]$", cap): E(f"{tag}: sem pontuacao final")
    if re.search(r"\.\.(?!\.)|,,|\.\,|,\.", cap): E(f"{tag}: pontuacao duplicada/estranha")
    if cap.count('"') % 2 or cap.count("“") != cap.count("”"): E(f"{tag}: aspas desbalanceadas")
    if cap[0].islower(): E(f"{tag}: inicia com minuscula")
    if "..." in cap: Wn(f"{tag}: reticencias '...' (preferir '…')")
    if re.search(r"\b(\w+) \1\b", cap, re.I): E(f"{tag}: palavra repetida")
    if ref and not BOOKREF.match(ref): E(f"{tag}: referencia fora do padrao '{ref}'")
    # geometria (simetria / margens / quebra)
    lines = wrap(cap, W * 2 * 0.78); ws = [d.textlength(l, font=ft) / 2 for l in lines]
    for l, w in zip(lines, ws):
        left = (W - w) / 2; right = W - left - w
        if abs(left - right) > 1: E(f"{tag}: linha assimetrica '{l}'")
        if w > W * 0.78 + 1: E(f"{tag}: linha passa de 78% da largura")
        if left < W * 0.11: E(f"{tag}: margem lateral < 11%")
    if len(lines) > 2: E(f"{tag}: {len(lines)} linhas (max 2)")
    if len(lines) > 1 and len(lines[-1].split()) == 1 and len(lines[-1]) < 6: Wn(f"{tag}: ultima linha orfã '{lines[-1]}'")
    if len(lines) > 1 and min(ws) < 0.35 * max(ws): Wn(f"{tag}: linhas desbalanceadas")
    # tempo / leitura
    nch = len(cap.replace(" ", "")); F = int(dur * FPS); dl = min(.5 * FPS, .15 * F); fi = min(.6 * FPS, .2 * F); fo = min(.5 * FPS, .2 * F)
    vis = (F - dl - fi - fo - 0.1 * FPS) / FPS
    cps = len(cap) / max(vis, .1)
    if cps > 17: E(f"{tag}: leitura {cps:.1f} car/s (>17)")
    elif cps > 15: Wn(f"{tag}: leitura {cps:.1f} car/s (>15)")
    if vis < 1.2: E(f"{tag}: legenda visivel so {vis:.1f}s")
    if not 4 <= dur <= 7 and s.get("kind") != "black": Wn(f"{tag}: duracao {dur}s fora de 4-7 s (contrato)")
    # karaoke (timing por palavra, se houver)
    tm = s.get("kara")
    if tm:
        n = len(cap.split())
        if len(tm) != n: E(f"{tag}: kara tem {len(tm)} palavras, legenda {n}")
        for k, (a, b) in enumerate(tm):
            if b <= a: E(f"{tag}: palavra {k+1} com fim<=inicio")
            if k and a < tm[k - 1][1] - 1e-6: E(f"{tag}: palavra {k+1} sobrepoe a anterior")
            if b > dur + 1e-6: E(f"{tag}: palavra {k+1} passa do fim do plano")
    info.append(f"{tag}: {len(lines)}l {cps:.1f}c/s vis={vis:.1f}s")
# video: simetria medida nos quadros
if len(sys.argv) > 2:
    import subprocess, numpy as np, imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe(); pos = 0
    for i, s in enumerate(cfg["shots"], 1):
        if i > 1 and s.get("in", "dissolve") == "dissolve": pos -= OV
        F = s["dur"]; mid = pos + F * (0.45 if s.get("kind") == "black" else 0.55); pos += F
        if not s.get("cap"): continue
        n = int(mid * FPS)
        r = subprocess.run([ff, "-v", "error", "-i", sys.argv[2], "-vf", f"select=eq(n\\,{n})", "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if not r: Wn(f"plano {i}: quadro nao lido"); continue
        a = np.frombuffer(r, np.uint8).reshape(-1, 960, 3).astype(float); h = a.shape[0]
        if s.get("kind") == "black":
            mm = a[int(F * 0 + 0):].min(axis=2) > 150; ys, xs = np.nonzero(mm)
            if len(xs) < 20: Wn(f"plano {i}: cartao preto sem texto no quadro"); continue
            ox = (xs.min() + xs.max()) / 2 - 480; oy = (ys.min() + ys.max()) / 2 - h / 2
            (E if abs(ox) > 6 or abs(oy) > 6 else info.append)(f"plano {i}: cartao preto centro dx={ox:+.1f} dy={oy:+.1f}px")
            continue
        nl = len(wrap(s["cap"], W * 2 * 0.78)); y0 = int((2160 - 190 - 119.6 * nl) / 4) - 6; y1 = y0 + int(30 * nl) + 12
        reg = a[y0:y1]
        m = (reg.min(axis=2) > 225) | ((reg[..., 1] > 175) & (reg[..., 2] < 150) & (reg[..., 0] > 150))
        cols = m.sum(axis=0); xs = np.nonzero(cols >= 2)[0]
        if len(xs) < 20: Wn(f"plano {i}: texto nao detectado no quadro (fade/preto?)"); continue
        lo, hi = np.percentile(xs, 1), np.percentile(xs, 99); c = (lo + hi) / 2; off = c - 480
        w_exp = max(d.textlength(l, font=ft) / 2 for l in wrap(s["cap"], W * 2 * 0.78)) / 2
        if abs(off) > 6: E(f"plano {i}: centro do texto no video {off:+.1f}px (limite 6)")
        else: info.append(f"plano {i}: centro no video {off:+.1f}px ok; largura medida {hi-lo:.0f}px / esperada {w_exp:.0f}px")
        if lo < 960 * .08 or hi > 960 * .92: E(f"plano {i}: texto fora da zona segura lateral")
print("\n".join(info)); print("\nAVISOS:" if warns else "\nAvisos: nenhum"); [print(" -", w) for w in warns]
print("ERROS:" if errs else "Erros: nenhum"); [print(" -", e) for e in errs]
sys.exit(1 if errs else 0)
