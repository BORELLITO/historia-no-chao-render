import json, subprocess, shutil, tempfile, os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import ingest_voz

def test_fluxo(tmp_path):
    ff = shutil.which("ffmpeg")
    assert ff, "ffmpeg ausente"
    os.environ["FFMPEG"] = ff
    mp3 = tmp_path / "t.mp3"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=10", "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)], check=True)
    data = mp3.read_bytes()
    links = tmp_path / "l.json"
    links.write_text(json.dumps({"trechos": {"T1": ingest_voz.PREFIXO + "x"}}))
    assert ingest_voz.main(str(links), str(tmp_path / "o"), fetch=lambda u: data) == 0
    m = json.loads((tmp_path / "o" / "manifesto.json").read_text())
    t = m["trechos"]["T1"]
    assert abs(t["orig_s"] - 10.0) < 0.2
    assert abs(t["rapida_s"] - 10.0 / 1.10) < 0.2

def test_link_invalido(tmp_path):
    links = tmp_path / "l.json"
    links.write_text(json.dumps({"trechos": {"T1": "https://evil.example/x.mp3"}}))
    assert ingest_voz.main(str(links), str(tmp_path / "o"), fetch=lambda u: b"") == 4

def test_nao_mp3(tmp_path):
    os.environ["FFMPEG"] = shutil.which("ffmpeg") or "ffmpeg"
    links = tmp_path / "l.json"
    links.write_text(json.dumps({"trechos": {"T1": ingest_voz.PREFIXO + "x"}}))
    assert ingest_voz.main(str(links), str(tmp_path / "o"), fetch=lambda u: b"<html>" * 2000) == 3
