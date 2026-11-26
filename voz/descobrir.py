"""Descoberta (somente leitura) de imagens/audio no Wikimedia Commons via API. Imprime titulo|mime|WxH|licenca|credito. Nao baixa nada."""
import json, sys, time, urllib.parse, urllib.request
UA = "VerboNoChaoHNC/0.1 (+https://github.com/BORELLITO/historia-no-chao-render; descoberta pontual)"
QS = json.load(open(sys.argv[1]))
def api(**p):
    p.update(format="json"); u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p)
    for k in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=40))
        except Exception as e: print("erro", repr(e)[:100]); time.sleep(8)
    return {}
for q in QS:
    print("\n### ", q["q"]); time.sleep(3)
    r = api(action="query", generator="search", gsrnamespace=6, gsrsearch=q["q"], gsrlimit=q.get("n", 12), prop="imageinfo", iiprop="url|size|mime|extmetadata", iiextmetadatafilter="LicenseShortName|Artist|ObjectName")
    for p in sorted((r.get("query", {}).get("pages", {})).values(), key=lambda x: x.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        print(f"{p['title']}|{ii.get('mime')}|{ii.get('width')}x{ii.get('height')}|{m.get('LicenseShortName',{}).get('value')}|{str(m.get('Artist',{}).get('value'))[:50]}")
