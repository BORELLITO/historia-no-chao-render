"""HNC EP01 - persiste a narracao (10 trechos, voz Johnes Bittar) a partir de links assinados, mede a duracao real,
gera a versao +10% (atempo 1.10, tom preservado) e grava manifesto com sha256. Nao gasta credito, nao publica.
Uso: python -I voz/ingest_voz.py run/voz_links.json voz"""
import hashlib, json, os, re, subprocess, sys, urllib.request
from pathlib import Path

PREFIXO = "https://elevenlabsusercontent.com/"
ATEMPO = 1.10


def ffmpeg_exe():
    exe = os.environ.get("FFMPEG")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duracao(ff, path):
    r = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if not m:
        raise RuntimeError(f"sem duracao em {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def baixar(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()


def main(links_path, outdir, fetch=baixar):
    cfg = json.loads(Path(links_path).read_text(encoding="utf8"))
    ff = ffmpeg_exe()
    out = Path(outdir); (out / "orig").mkdir(parents=True, exist_ok=True); (out / "rapida").mkdir(parents=True, exist_ok=True)
    man = {"voz": "Johnes Bittar (sJfod1k0iiI5CA9IP0R2)", "modelo": "eleven_v4", "atempo": ATEMPO, "trechos": {}}
    tot_o = tot_r = 0.0
    for tid, url in cfg["trechos"].items():
        if not url.startswith(PREFIXO):
            print("VNC_VOZ_ABORT link_invalido", tid); return 4
        data = fetch(url)
        if len(data) < 5000 or not (data[:3] == b"ID3" or data[0] == 0xFF):
            print("VNC_VOZ_ABORT nao_e_mp3", tid, len(data)); return 3
        po = out / "orig" / f"{tid}.mp3"; po.write_bytes(data)
        pr = out / "rapida" / f"{tid}.mp3"
        r = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(po), "-filter:a", f"atempo={ATEMPO}", "-c:a", "libmp3lame", "-b:a", "192k", str(pr)], capture_output=True, text=True)
        if r.returncode != 0:
            print("VNC_VOZ_ABORT ffmpeg", tid, r.stderr[-300:]); return 5
        do, dr = duracao(ff, po), duracao(ff, pr)
        tot_o += do; tot_r += dr
        man["trechos"][tid] = {"orig_s": round(do, 2), "rapida_s": round(dr, 2), "bytes_orig": len(data),
                               "sha256_orig": hashlib.sha256(data).hexdigest(), "sha256_rapida": hashlib.sha256(pr.read_bytes()).hexdigest()}
        print(f"VNC_VOZ {tid} orig {do:.2f}s rapida {dr:.2f}s {len(data)} bytes")
    man["total_orig_s"], man["total_rapida_s"] = round(tot_o, 2), round(tot_r, 2)
    (out / "manifesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"VNC_VOZ_TOTAL orig {tot_o:.1f}s ({tot_o/60:.2f} min) rapida {tot_r:.1f}s ({tot_r/60:.2f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
