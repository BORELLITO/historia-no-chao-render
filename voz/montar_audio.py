"""HNC EP01 - trilha de voz da previa: takes ORIGINAIS (voz/orig) concatenados + silencios planejados (mesmos de mapa_planos). Saida: wav 44.1k mono.
Uso: python voz/montar_audio.py saida.wav"""
import json, subprocess, sys, copy
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "voz"))
from mapa_planos import global_words, aplicar_silencios
ORDEM = ["T1", "T2", "T3", "T4a", "T4b", "T5", "T6", "T7", "T8", "T9"]


def plano_audio():
    al = json.load(open(R / "voz/alinhamento.json")); gw = global_words(al); orig = copy.deepcopy(gw)
    sil, _ = aplicar_silencios(gw)
    pts = [(orig[i]["fim"], dur) for i, dur, _ in sil]   # instante (na linha original) apos o qual entra o silencio
    return sorted(pts), sum(d for _, d in pts)


def main(saida):
    pts, tot = plano_audio()
    lst = R / "voz/_orig.txt"; lst.write_text("".join(f"file '{R / 'voz/orig' / (t + '.mp3')}'\n" for t in ORDEM))
    ff = "ffmpeg"; base = "/tmp/_orig_all.wav"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "44100", "-ac", "1", base], check=True)
    cuts = [0.0] + [p for p, _ in pts]; fil, labs, n = [], [], 0
    for j, a in enumerate(cuts):
        b = cuts[j + 1] if j + 1 < len(cuts) else None
        fil.append(f"[0:a]atrim=start={a}" + (f":end={b}" if b else "") + f",asetpts=PTS-STARTPTS[s{n}]"); labs.append(f"[s{n}]"); n += 1
        if j < len(pts):
            fil.append(f"anullsrc=r=44100:cl=mono,atrim=duration={pts[j][1]}[z{j}]"); labs.append(f"[z{j}]")
    fil.append("".join(labs) + f"concat=n={len(labs)}:v=0:a=1[o]")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", base, "-filter_complex", ";".join(fil), "-map", "[o]", "-ar", "44100", "-ac", "1", saida], check=True)
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", saida]))
    print(f"audio_previa dur_s={d:.2f} silencios={pts} total_silencio_s={tot}")
    return d


def lufs(f):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = r.rfind("I:"); return r[i:i + 14].strip() + " | " + r[r.rfind("Peak:"):r.rfind("Peak:") + 16].strip() if i >= 0 else "?"


def mixar(voz, musica_dir, saida, dur):
    """trilha: Aria -> Variatio 13 -> Variatio 25 (Bach/Ishizaka, CC0) em cama continua, -16 dB abaixo da voz, ducking sob a fala, fade-in 3 s / fade-out 6 s."""
    fs = [Path(musica_dir) / (m + ".flac") for m in ("MUS-ARIA", "MUS-V13", "MUS-V25")]; fs = [f for f in fs if f.exists()]
    if not fs: print("SEM TRILHA: arquivos ausentes"); return False
    ins = sum([["-i", str(f)] for f in fs], []); n = len(fs)
    ch = ";".join(f"[{k + 1}:a]aformat=sample_rates=44100:channel_layouts=stereo[m{k}]" for k in range(n))
    cur = "[m0]"
    for k in range(1, n): ch += f";{cur}[m{k}]acrossfade=d=4[x{k}]"; cur = f"[x{k}]"
    ch += f";{cur}atrim=0:{dur},afade=t=in:d=3,afade=t=out:st={dur - 6}:d=6,loudnorm=I=-34:TP=-4:LRA=7[mus]"
    ch += ";[0:a]loudnorm=I=-18:TP=-2,aformat=sample_rates=44100:channel_layouts=stereo,asplit[v1][v2]"
    ch += ";[mus][v1]sidechaincompress=threshold=0.02:ratio=5:attack=60:release=900[md];[v2][md]amix=inputs=2:normalize=0,alimiter=limit=0.9[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", voz] + ins + ["-filter_complex", ch, "-map", "[o]", "-ar", "44100", saida], check=True)
    print("loudness voz:", lufs(voz), "| mix final:", lufs(saida)); return True


if __name__ == "__main__":
    saida = sys.argv[1]
    if len(sys.argv) > 2:
        d = main("/tmp/_voz_solo.wav"); ok = mixar("/tmp/_voz_solo.wav", sys.argv[2], saida, d)
        if not ok: Path(saida).write_bytes(Path("/tmp/_voz_solo.wav").read_bytes())
    else: main(saida)
