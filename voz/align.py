"""HNC EP01 - alinha o texto do roteiro (V4g) ao tempo real da voz. Transcreve cada trecho com faster-whisper (CPU, gratis),
alinha palavra a palavra com o texto (Needleman-Wunsch com similaridade fuzzy) e grava voz/alinhamento.json:
palavras com inicio/fim, frases com inicio/fim, cobertura. Uso: python voz/align.py voz [--sem-whisper arquivo.json]"""
import difflib, json, re, sys, unicodedata
from pathlib import Path

LIM = 0.62


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def alinhar(script_words, asr_words):
    """script_words: lista de str; asr_words: lista de (str, ini, fim). Retorna lista (ini, fim, casou) por palavra do roteiro."""
    n, m = len(script_words), len(asr_words)
    S = [norm(w) for w in script_words]
    A = [norm(w[0]) for w in asr_words]
    gap = -0.4
    sc = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        sc[i][0] = i * gap; bt[i][0] = 1
    for j in range(1, m + 1):
        sc[0][j] = j * gap; bt[0][j] = 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = sim(S[i - 1], A[j - 1])
            d = sc[i - 1][j - 1] + (2 * s - 1 if s >= LIM else -1.0)
            u = sc[i - 1][j] + gap
            l = sc[i][j - 1] + gap
            best = max(d, u, l)
            sc[i][j] = best
            bt[i][j] = 0 if best == d else (1 if best == u else 2)
    i, j, par = n, m, {}
    while i > 0 or j > 0:
        t = bt[i][j]
        if i > 0 and j > 0 and t == 0:
            if sim(S[i - 1], A[j - 1]) >= LIM:
                par[i - 1] = j - 1
            i -= 1; j -= 1
        elif i > 0 and (t == 1 or j == 0):
            i -= 1
        else:
            j -= 1
    out = [None] * n
    for i, j in par.items():
        out[i] = (asr_words[j][1], asr_words[j][2], True)
    # interpola as nao casadas entre vizinhas casadas
    idx = [i for i in range(n) if out[i]]
    if not idx:
        return [(0.0, 0.0, False)] * n
    for k in range(n):
        if out[k]:
            continue
        prev = max([i for i in idx if i < k], default=None)
        nxt = min([i for i in idx if i > k], default=None)
        t0 = out[prev][1] if prev is not None else out[nxt][0]
        t1 = out[nxt][0] if nxt is not None else out[prev][1]
        lo = prev if prev is not None else k
        hi = nxt if nxt is not None else k
        span = max(hi - lo, 1)
        pos = (k - lo) / span if prev is not None else 0
        a = t0 + (t1 - t0) * pos
        out[k] = (round(a, 3), round(a + max(0.05, (t1 - t0) / span), 3), False)
    return out


def frases(words):
    """words: [{w,ini,fim}] -> frases por pontuacao final."""
    res, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?:]$|\.\.\.$", w["w"]):
            res.append(cur); cur = []
    if cur:
        res.append(cur)
    return [{"texto": " ".join(x["w"] for x in f), "ini": f[0]["ini"], "fim": f[-1]["fim"]} for f in res]


def transcrever(mp3):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(mp3), language="pt", word_timestamps=True, vad_filter=False, beam_size=5)
    return [(w.word.strip(), float(w.start), float(w.end)) for s in segs for w in s.words]


def main(voz_dir, asr_fn=transcrever):
    voz = Path(voz_dir)
    tx = json.loads((voz / "texto_trechos.json").read_text(encoding="utf8"))
    man = json.loads((voz / "manifesto.json").read_text(encoding="utf8"))
    res = {"fonte_texto": tx["fonte"], "versao_audio": "orig", "trechos": {}}
    t_global, tot_casou, tot = 0.0, 0, 0
    for tid in tx["ordem"]:
        words_txt = tx["trechos"][tid].split()
        asr = asr_fn(voz / "orig" / f"{tid}.mp3")
        al = alinhar(words_txt, asr)
        pal = [{"w": w, "ini": round(a, 3), "fim": round(b, 3), "casou": c} for w, (a, b, c) in zip(words_txt, al)]
        casou = sum(1 for p in pal if p["casou"])
        dur = man["trechos"][tid]["orig_s"]
        res["trechos"][tid] = {"duracao_s": dur, "inicio_global_s": round(t_global, 2), "palavras": pal, "frases": frases(pal),
                               "cobertura": round(casou / len(pal), 3), "palavras_asr": len(asr)}
        print(f"VNC_ALIGN {tid} palavras {len(pal)} casadas {casou} cobertura {casou/len(pal):.2%} dur {dur}s inicio_global {t_global:.1f}s")
        tot_casou += casou; tot += len(pal); t_global += dur
    res["cobertura_total"] = round(tot_casou / tot, 3)
    res["duracao_total_s"] = round(t_global, 2)
    (voz / "alinhamento.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"VNC_ALIGN_TOTAL palavras {tot} cobertura {tot_casou/tot:.2%} duracao {t_global:.1f}s")
    return 0 if tot_casou / tot >= 0.9 else 6


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
