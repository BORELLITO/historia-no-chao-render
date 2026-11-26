"""HNC EP01 - monta hnc/shots_ep01_previa.json (V7 + voz real + karaoke sincronizado). ARTE PROVISORIA, nao aprovada.
Plano V7 -> chapa: primeiro v5_cobre com ativo nos manifestos (ordem de prioridade); sem ativo -> cartao tipografico preto (kind black).
Saida: hnc/shots_ep01_previa.json + voz/previa_mapa.txt (tabela plano|chapa|motivo)."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "voz"))
from mapa_planos import global_words, aplicar_silencios
FPS, OVS = 24, 0.5
EXIGE = '--exige-arquivos' in sys.argv
VETADOS = {"WC-LEYDEN-ABRAAO"}
MANIFS = ["manifest_ep01.json", "manifest_lote4.json", "manifest_lote5b.json", "manifest_cena56.json"]
MOV = [([.30, .50, .75], [.70, .50, .75]), ([.70, .52, .75], [.32, .50, .72]), ([.5, .5, 1.0], [.5, .5, .66]), ([.5, .5, .66], [.5, .5, 1.0]),
       ([.35, .4, .7], [.6, .6, .7]), ([.65, .6, .7], [.4, .4, .7])]


def carregar_chapas():
    ch = {}
    for f in sorted((R / "hnc").glob("shots_*.json")):
        ch.update(json.load(open(f)).get("plates", {}))
    por_plano = {}
    for mf in MANIFS:
        for a in json.load(open(R / "hnc" / mf))["assets"]:
            if a["id"] in VETADOS or a["id"] not in ch: continue
            if EXIGE and not (R / "hnc/quarentena" / (a["id"] + ".jpg")).exists(): continue
            for p in a.get("planos", []): por_plano.setdefault(p, []).append(a["id"])
    return ch, por_plano


def montar():
    prop = json.load(open(R / "voz/proposta_planos_v7.json"))["planos"]
    al = json.load(open(R / "voz/alinhamento.json")); gw = global_words(al); aplicar_silencios(gw)
    ch, por_plano = carregar_chapas(); shots, linhas, k, uso, ultima = [], [], 0, 0, None
    for i, p in enumerate(prop):
        toks = p["texto"].split(); seg = gw[k:k + len(toks)]
        assert [w["w"] for w in seg] == toks, f"plano {p['n']}: palavras nao conferem com o alinhamento"
        k += len(toks)
        ini = p["ini"]; ov = OVS if i > 0 else 0.0
        nxt = prop[i + 1]["ini"] if i + 1 < len(prop) else ini + p["dur"]
        f0 = round(ini * FPS); f1 = round(nxt * FPS); dur = ((f1 - f0) + (int(OVS * FPS) if i > 0 else 0)) / FPS
        # o shot comeca ov antes de 'ini' (dissolve); durante o overlap o texto ainda nao fala
        t0 = f0 / FPS - (int(OVS * FPS) / FPS if i > 0 else 0)
        kara = [[round(w["ini"] - t0, 3), round(w["fim"] - t0, 3)] for w in seg]
        src = next((a for pid in p["v5_cobre"] for a in por_plano.get(pid, [])), None); reuso = False
        if not src and not p.get("batida") and ultima:
            src = ultima; reuso = True   # arte PROVISORIA: reaproveita a chapa do plano anterior (continuidade), so para julgar ritmo/legenda
        if src and not reuso: ultima = src
        sh = {"dur": dur + 0.001, "cap": p["texto"], "kara": kara}
        if p.get("batida"): sh["cap_pos"] = "center"
        if src:
            a, b = MOV[uso % len(MOV)]; uso += 1
            sh.update({"src": src, "a": a, "b": b, "in": "dissolve" if i > 0 else "cut", "fx": {"parallax": 12, "bloom": 0.35, "haze": 0.05}})
            linhas.append(f"{p['n']:>3}|{p['trecho']}|{p['dur']:.2f}s|{src}{' (REUSO PROVISORIO)' if reuso else ''}|{'BATIDA' if p.get('batida') else ''}")
        else:
            sh.update({"src": "preto", "kind": "black", "in": "dissolve" if i > 0 else "cut", "cap_pos": "center"})
            linhas.append(f"{p['n']:>3}|{p['trecho']}|{p['dur']:.2f}s|CARTAO PRETO (sem ativo p/ {','.join(p['v5_cobre'])})|{'BATIDA' if p.get('batida') else ''}")
        shots.append(sh)
    usadas = sorted({s["src"] for s in shots if s["src"] != "preto"})
    cfg = {"fps": 30, "w": 1920, "h": 1080, "overlap_s": OVS, "plates": {u: ch[u] for u in usadas}, "shots": shots}
    return cfg, linhas, usadas


if __name__ == "__main__":
    cfg, linhas, usadas = montar()
    json.dump(cfg, open(R / "hnc/shots_ep01_previa.json", "w"), ensure_ascii=False, indent=1)
    (R / "voz/previa_mapa.txt").write_text("\n".join(linhas) + "\n")
    n_pb = sum(1 for s in cfg["shots"] if s["src"] == "preto")
    print(f"shots={len(cfg['shots'])} com_arte={len(cfg['shots']) - n_pb} cartao_preto={n_pb} chapas={usadas}")
    print("duracao_total_s=", round(sum(s['dur'] for s in cfg['shots']) - OVS * (len(cfg['shots']) - 1), 1))
