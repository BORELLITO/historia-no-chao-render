import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import align

def test_alinhar_com_erro_de_asr():
    s = "Ele acordou cedo. Foi até Zoar e viu Cafarnaum".split()
    asr = [("ele", 0.0, 0.2), ("acordou", 0.2, 0.6), ("cedo", 0.6, 1.0), ("foi", 1.5, 1.7), ("até", 1.7, 1.9),
           ("zoá", 1.9, 2.4), ("e", 2.4, 2.5), ("viu", 2.5, 2.8), ("cafarnaum", 2.8, 3.5)]
    r = align.alinhar(s, asr)
    assert all(x[2] for x in r), r
    assert r[0][0] == 0.0 and r[-1][1] == 3.5

def test_interpola_palavra_perdida():
    s = "um dois tres quatro".split()
    asr = [("um", 0, 1), ("tres", 2, 3), ("quatro", 3, 4)]
    r = align.alinhar(s, asr)
    assert [x[2] for x in r] == [True, False, True, True]
    assert 1.0 <= r[1][0] <= 2.0

def test_frases():
    p = [{"w": "Oi.", "ini": 0, "fim": 1}, {"w": "Tudo", "ini": 1, "fim": 2}, {"w": "bem?", "ini": 2, "fim": 3}]
    f = align.frases(p)
    assert len(f) == 2 and f[1]["ini"] == 1 and f[1]["fim"] == 3
