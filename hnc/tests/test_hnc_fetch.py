import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import hnc_fetch as h

def test_license_ok():
    a = {"license_marker": "Mixkit Stock Video Free License", "forbidden_marker": "Restricted License"}
    assert h.license_ok(a, "under the Mixkit Stock Video Free License.")[0]

def test_restricted_blocked():
    a = {"license_marker": "Mixkit Stock Video Free License", "forbidden_marker": "Restricted License"}
    ok, why = h.license_ok(a, "personal use only, under the Mixkit Restricted License")
    assert not ok and "proibido" in why

def test_missing_marker_blocked():
    a = {"license_marker": "Pixabay Content License"}
    assert not h.license_ok(a, "nada")[0]

def test_manifest_limit(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"max_files": 1, "assets": [{"id": "a"}, {"id": "b"}]}))
    try:
        h.load_manifest(str(p))
        assert False
    except SystemExit:
        pass

def test_real_manifest_valid():
    m = h.load_manifest(str(pathlib.Path(__file__).resolve().parent.parent / "manifest_ep01.json"))
    assert len(m["assets"]) == 8 and all(x["planos"] for x in m["assets"])

def test_lote4_manifest_valid():
    m = h.load_manifest(str(pathlib.Path(__file__).resolve().parent.parent / "manifest_lote4.json"))
    assert len(m["assets"]) == 4 and all(x["planos"] for x in m["assets"])
