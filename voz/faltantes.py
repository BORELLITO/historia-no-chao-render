"""Gera manifestos so com ativos ainda ausentes em hnc/quarentena (cache). Uso: python voz/faltantes.py hnc m1.json m2.json ... ; imprime caminhos a buscar."""
import glob, json, os, sys
base = sys.argv[1]
for m in sys.argv[2:]:
    d = json.load(open(f"{base}/{m}")); falta = [a for a in d["assets"] if not glob.glob(f"{base}/quarentena/{a['id']}.*")]
    if falta:
        d["assets"] = falta; p = f"/tmp/falta_{m}"; json.dump(d, open(p, "w")); print(p)
