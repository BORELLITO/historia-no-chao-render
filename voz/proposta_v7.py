"""HNC EP01 - PROPOSTA de segmentacao em planos (V7) sobre a narracao real: cortes de 4-7 s (contrato) em fronteiras de frase/virgula,
com BATIDAS protegidas (curtas de proposito). Nao altera arte nem texto. Saida: voz/proposta_planos_v7.json."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import mapa_planos as mp

BATIDAS = {"Quarenta.", "Trinta.", "Vinte.", "Dez.", "Cegos.", "estranhos."}
MIN_S, MAX_S = 4.0, 7.0


def frases_idx(gw):
    res, ini = [], 0
    for i, w in enumerate(gw):
        fim_trecho = i + 1 == len(gw) or gw[i + 1]["tid"] != w["tid"]
        if re.search(r"[.!?]$", w["w"]) or fim_trecho:
            res.append((ini, i)); ini = i + 1
    return res


def sub_cortes(gw, a, b):
    """divide uma frase longa (a..b) em pedacos 4-7 s em virgulas/dois-pontos; sem pontuacao, corta perto de 6 s."""
    out, s = [], a
    while gw[b]["fim"] - gw[s]["ini"] > MAX_S:
        cand = [i for i in range(s, b) if re.search(r"[,:]$", gw[i]["w"]) and MIN_S <= gw[i]["fim"] - gw[s]["ini"] <= MAX_S]
        if cand:
            c = cand[-1]
        else:
            c = max([i for i in range(s, b) if gw[i]["fim"] - gw[s]["ini"] <= MAX_S] or [s])
        out.append((s, c)); s = c + 1
    out.append((s, b))
    return out


def proposta(gw):
    unidades = []
    for a, b in frases_idx(gw):
        dur = gw[b]["fim"] - gw[a]["ini"]
        unidades.extend(sub_cortes(gw, a, b) if dur > MAX_S else [(a, b)])
    # particao otima por programacao dinamica em cada bloco (entre batidas e fronteiras de trecho)
    blocos, atual = [], []
    for a, b in unidades:
        beat = gw[b]["w"] in BATIDAS and b - a <= 1
        if atual and gw[atual[0][0]]["tid"] != gw[a]["tid"]:
            blocos.append(("g", atual)); atual = []
        if beat:
            if atual:
                blocos.append(("g", atual)); atual = []
            blocos.append(("b", [(a, b)]))
        else:
            atual.append((a, b))
    if atual:
        blocos.append(("g", atual))

    def custo(d):
        return 0.0 if MIN_S <= d <= MAX_S else ((MIN_S - d) ** 2 if d < MIN_S else 1.5 * (d - MAX_S) ** 2)

    planos = []
    for tipo, us in blocos:
        if tipo == "b":
            planos.append(us[0]); continue
        n = len(us)
        best = [0.0] + [float("inf")] * n; prev = [0] * (n + 1)
        for j in range(1, n + 1):
            for i in range(j):
                d = gw[us[j - 1][1]]["fim"] - gw[us[i][0]]["ini"]
                c = best[i] + custo(d)
                if c < best[j]:
                    best[j], prev[j] = c, i
        j, cortes = n, []
        while j > 0:
            cortes.append((prev[j], j)); j = prev[j]
        for i, j in reversed(cortes):
            planos.append((us[i][0], us[j - 1][1]))
    return planos


def main(voz):
    voz = Path(voz)
    al = json.loads((voz / "alinhamento.json").read_text(encoding="utf8"))
    gw = mp.global_words(al); sil, extra = mp.aplicar_silencios(gw)
    mapa = json.loads((voz / "mapa_planos.json").read_text(encoding="utf8"))
    v5 = [(p["id"], p["ini"], p["ini"] + p["dur_visual"]) for p in mapa["planos"]]
    pl = proposta(gw)
    out, tot = [], gw[-1]["fim"]
    for k, (a, b) in enumerate(pl):
        ini = 0.0 if k == 0 else gw[a]["ini"]
        prox = gw[pl[k + 1][0]]["ini"] if k + 1 < len(pl) else tot
        dv = prox - ini
        beat = gw[b]["w"] in BATIDAS and b - a <= 1
        ov = [(min(f, prox) - max(i, ini), pid) for pid, i, f in v5 if min(f, prox) - max(i, ini) > 0.05]
        ov.sort(reverse=True)
        flag = "" if beat or MIN_S <= dv <= MAX_S else ("CURTO" if dv < MIN_S else "LONGO")
        out.append({"n": k + 1, "trecho": gw[a]["tid"], "ini": round(ini, 2), "dur": round(dv, 2), "batida": beat, "flag": flag,
                    "v5_principal": ov[0][1] if ov else None, "v5_cobre": [p for _, p in ov], "texto": " ".join(w["w"] for w in gw[a:b + 1])})
    json.dump({"versao_audio": "orig", "duracao_total_s": round(tot, 2), "planos": out}, open(voz / "proposta_planos_v7.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
    durs = [p["dur"] for p in out if not p["batida"]]
    print(f"VNC_V7 planos {len(out)} (batidas {sum(1 for p in out if p['batida'])}); media {sum(durs)/len(durs):.2f}s min {min(durs):.2f} max {max(durs):.2f}; fora de 4-7s (sem batidas): {sum(1 for p in out if p['flag'])}")
    for p in out:
        if p["flag"]:
            print("  ", p["n"], p["trecho"], p["ini"], p["dur"], p["flag"], "|", p["texto"][:70])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
