#!/usr/bin/env python3
"""HNC asset fetcher (RASCUNHO, nao rodado em remoto). Modos: check (so le paginas e valida licenca) e fetch (baixa para quarentena).
Regras: sem bypass de Cloudflare/captcha; para no 403/429; limite de arquivos; ledger com sha256; nunca grava segredos."""
import argparse, hashlib, json, sys, time, urllib.request, urllib.error
UA = "VerboNoChaoHNC/0.1 (+https://github.com/BORELLITO/verbo-no-chao-privado; uso pontual, 2 arquivos)"

def load_manifest(path, limit=None):
    m = json.load(open(path, encoding="utf-8"))
    assets = m["assets"]
    cap = min(m.get("max_files", 10), limit or 10**9)
    if len(assets) > cap:
        raise SystemExit(f"manifest tem {len(assets)} ativos; limite {cap}")
    return m

def license_ok(asset, html):
    """True so se o marcador de licenca existe e o marcador proibido NAO existe."""
    low = html.lower()
    if asset.get("forbidden_marker") and asset["forbidden_marker"].lower() in low:
        return False, "marcador proibido presente: " + asset["forbidden_marker"]
    if asset["license_marker"].lower() not in low:
        return False, "marcador de licenca ausente: " + asset["license_marker"]
    return True, "ok"

def http_get(url, binary=False, max_bytes=60_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read(max_bytes + 1)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise SystemExit(f"PARADO: HTTP {e.code} em {url} (sem contornar bloqueio)")
        raise
    if len(data) > max_bytes:
        raise SystemExit("arquivo acima do limite de bytes")
    return data if binary else data.decode("utf-8", "replace")

def process(asset, a):
    page = http_get(asset["page"])
    ok, why = license_ok(asset, page)
    row = {"id": asset["id"], "licenca_ok": ok, "motivo": why, "planos": asset["planos"]}
    if ok and a.mode == "fetch":
        data = http_get(asset["file"], binary=True)
        ext = asset["file"].rsplit(".", 1)[-1].split("?")[0]
        import os
        os.makedirs(a.out, exist_ok=True)
        fn = f"{a.out}/{asset['id']}.{ext}"
        open(fn, "wb").write(data)
        row.update(arquivo=fn, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return row

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="manifest_ep01.json")
    ap.add_argument("--mode", choices=["check", "fetch"], default="check")
    ap.add_argument("--out", default="quarentena")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    m = load_manifest(a.manifest, a.limit)
    ledger = []
    for asset in m["assets"]:
        try:
            ledger.append(process(asset, a))
        except SystemExit as e:
            ledger.append({"id": asset["id"], "licenca_ok": None, "motivo": str(e), "planos": asset["planos"], "parado": True})
            print(f"parado em {asset['id']}: {e}", file=sys.stderr)
            break
        time.sleep(30)
    json.dump(ledger, open("ledger.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(ledger, ensure_ascii=False, indent=1))
    return 0 if all(r["licenca_ok"] for r in ledger) else 2

if __name__ == "__main__":
    sys.exit(main())
