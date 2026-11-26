"""HNC EP01 - mapa de tempo dos planos sobre a narracao real (voz original). Entrada: voz/alinhamento.json + voz/planos_v5.txt
(id|dur_v5|tipo|texto, texto ADAPTADO ao V4g). Saida: voz/mapa_planos.json e tabela no stdout.
Silencios planejados (decididos no roteiro): +2,0 s depois de 'Dez.'; +1,0 s depois de 'Para estranhos.'; +1,0 s depois de 'Cegos.'; +3,0 s de transicao entre T5 e T6."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from align import alinhar, norm


def global_words(al):
    out = []
    for tid in ["T1", "T2", "T3", "T4a", "T4b", "T5", "T6", "T7", "T8", "T9"]:
        t = al["trechos"][tid]; g = t["inicio_global_s"]
        for p in t["palavras"]:
            out.append({"w": p["w"], "ini": p["ini"] + g, "fim": p["fim"] + g, "tid": tid})
    return out


def aplicar_silencios(gw):
    """retorna lista de silencios [(indice_palavra_apos, segundos, rotulo)] e desloca os tempos."""
    sil = []
    ix = lambda f: next(i for i, w in enumerate(gw) if f(i, w))
    i_est = ix(lambda i, w: w["w"] == "estranhos." and gw[i - 1]["w"] == "Para")
    sil.append((i_est, 1.0, "pausa 'Para estranhos.' (P030)"))
    i_dez = max(i for i, w in enumerate(gw) if w["tid"] == "T4a")
    sil.append((i_dez, 2.0, "silencio total apos 'Dez.' (P050)"))
    i_ceg = max(i for i, w in enumerate(gw) if w["tid"] == "T5" and w["w"] == "Cegos.")
    sil.append((i_ceg, 1.0, "silencio apos 'Cegos.' (P069)"))
    i_t5 = max(i for i, w in enumerate(gw) if w["tid"] == "T5")
    sil.append((i_t5, 3.0, "transicao noite -> madrugada (P072)"))
    sil.sort()
    off, k = 0.0, 0
    for i, w in enumerate(gw):
        w["ini"] += off; w["fim"] += off
        while k < len(sil) and sil[k][0] == i:
            off += sil[k][1]; k += 1
    return sil, off


def mapear(planos, gw):
    pw, owner = [], []
    for pid, dur, tipo, txt in planos:
        if txt.startswith("("):
            continue
        for w in txt.split():
            pw.append(w); owner.append(pid)
    asr = [(w["w"], w["ini"], w["fim"]) for w in gw]
    al = alinhar(pw, asr)
    seg = {}
    for w, o, (a, b, c) in zip(pw, owner, al):
        s = seg.setdefault(o, {"ini": a, "fim": b, "n": 0, "casadas": 0})
        s["ini"] = min(s["ini"], a); s["fim"] = max(s["fim"], b); s["n"] += 1; s["casadas"] += 1 if c else 0
    return seg


def main(voz):
    voz = Path(voz)
    al = json.loads((voz / "alinhamento.json").read_text(encoding="utf8"))
    gw = global_words(al)
    sil, extra = aplicar_silencios(gw)
    planos = [l.rstrip("\n").split("|", 3) for l in (voz / "planos_v5.txt").read_text(encoding="utf8").splitlines() if l.strip()]
    planos = [(p[0], int(p[1]), p[2], p[3]) for p in planos]
    seg = mapear(planos, gw)
    lista = [p for p in planos if p[0] in seg]
    res, tot_dur = [], gw[-1]["fim"]
    for k, (pid, dur5, tipo, txt) in enumerate(lista):
        s = seg[pid]
        inicio = 0.0 if k == 0 else s["ini"]
        prox = seg[lista[k + 1][0]]["ini"] if k + 1 < len(lista) else tot_dur
        dv = prox - inicio
        flag = "" if 4.0 <= dv <= 7.0 else ("CURTO <4s" if dv < 4.0 else "LONGO >7s")
        if s["casadas"] / s["n"] < 0.8:
            flag = (flag + " TEXTO NAO CASA").strip()
        res.append({"id": pid, "tipo": tipo, "ini": round(inicio, 2), "dur_visual": round(dv, 2), "dur_v5": dur5, "casadas": f"{s['casadas']}/{s['n']}", "flag": flag, "texto": txt[:70]})
    out = {"versao_audio": "orig", "silencios": [{"apos_palavra": gw[i]["w"], "s": s, "rotulo": r} for i, s, r in sil],
           "duracao_total_s": round(tot_dur, 2), "planos": res}
    (voz / "mapa_planos.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
    n_ok = sum(1 for r in res if not r["flag"])
    print(f"VNC_MAPA total {tot_dur:.1f}s ({tot_dur/60:.2f} min) com silencios +{extra:.1f}s; planos {len(res)}; dentro de 4-7s: {n_ok}")
    for r in res:
        if r["flag"]:
            print(f"  {r['id']} {r['tipo']:5} ini {r['ini']:7.2f} dur {r['dur_visual']:5.2f} (v5 {r['dur_v5']}) {r['flag']} | {r['texto']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
