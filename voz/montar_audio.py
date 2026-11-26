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


if __name__ == "__main__":
    main(sys.argv[1])
