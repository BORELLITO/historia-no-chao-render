import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import proposta_v7 as pv

def _gw(frases, tid="T1", dur=1.0):
    gw, t = [], 0.0
    for f in frases:
        for w in f.split():
            gw.append({"w": w, "ini": t, "fim": t + dur / 2, "tid": tid}); t += dur / 2
    return gw

def test_batida_fica_sozinha():
    gw = _gw(["a b c d e f g h.", "Dez.", "i j k l m n o p."])
    pl = pv.proposta(gw)
    assert (8, 8) in pl            # 'Dez.' isolada
    assert all(a <= b for a, b in pl)

def test_cobre_tudo_sem_sobrepor():
    gw = _gw(["um dois tres quatro.", "cinco seis sete oito.", "nove dez onze doze."] * 3)
    pl = pv.proposta(gw)
    assert pl[0][0] == 0 and pl[-1][1] == len(gw) - 1
    assert all(pl[i][1] + 1 == pl[i + 1][0] for i in range(len(pl) - 1))

def test_grupos_dentro_de_4_7():
    gw = _gw(["a b c.", "d e f.", "g h i.", "j k l.", "m n o."], dur=1.0)  # frases de 1,5 s
    pl = pv.proposta(gw)
    for a, b in pl:
        assert 4.0 <= gw[b]["fim"] - gw[a]["ini"] <= 7.0 or b == len(gw) - 1
