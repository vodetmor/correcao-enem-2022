"""Reajuste dos parâmetros de MT 2013 com amostra ESTRATIFICADA por nota (o ajuste original sorteou ao acaso e viu pouco o topo da escala).
Ajusta por CO_ITEM usando os 4 cadernos juntos; valida em participantes que NÃO entraram no ajuste e na amostra natural de 600 mil."""
import sys, json, pathlib, collections, time, random
sys.path.insert(0, 'C:/dev/enem/correcao-enem/tools/pipeline')
import numpy as np
from scipy.optimize import least_squares
import enem_pipeline as P
W = pathlib.Path('C:/dev/enem/_work'); G = P.GRID; random.seed(13); np.random.seed(13)
f = P.Fonte(W / 'zips' / 'microdados_enem_2013.zip'); nome = f.achar(r'^(microdados|resultados)')
itens, _ = P.carregar_itens(f); P.aplicar_override(itens, 2013); cad = P.montar_cadernos(itens); m, s = P.K0['MT']
PROVAS = ('179', '180', '181', '182')
col = {p: cad[('MT', p)]['langs'][''] for p in PROVAS}
cods = sorted({x['item'] for p in PROVAS for x in col[p] if x['a'] is not None and not x['aban']}); ix = {c: i for i, c in enumerate(cods)}; NI = len(cods)
ini = {}
for p in PROVAS:
    for x in col[p]:
        if x['item'] in ix: ini[x['item']] = (x['a'], x['b'], x['c'])
A0 = np.array([ini[c][0] for c in cods]); B0 = np.array([ini[c][1] for c in cods]); C0 = np.array([ini[c][2] for c in cods])
gab = {p: np.array([x['gab'] for x in col[p]]) for p in PROVAS}
mapa = {p: np.array([ix.get(x['item'], -1) for x in col[p]]) for p in PROVAS}   # coluna -> índice do item (-1 = fora da nota)
print('itens com parâmetros:', NI, '| colunas fora da nota por caderno:', {p: int((mapa[p] < 0).sum()) for p in PROVAS}, flush=True)
BINS = [0, 600, 700, 750, 800, 850, 900, 1001]; CAP = {0: 2500, 1: 3500, 2: 2500, 3: 2500, 4: 2500, 5: 2000, 6: 1500}
POOL = collections.defaultdict(list); vistos = collections.Counter(); n = 0; SKIP = 600000   # as primeiras 600 mil linhas ficam para teste natural
t0 = time.time()
for a, prova, lg, resp, nota in P.participantes(f, nome):
    if a != 'MT' or prova not in PROVAS or P.em_branco(resp): continue
    n += 1
    if n <= SKIP: continue
    b = int(np.searchsorted(BINS, nota, side='right') - 1); k = (prova, b); vistos[k] += 1
    if len(POOL[k]) < CAP[b]: POOL[k].append((resp, nota))
    else:
        j = random.randrange(vistos[k])
        if j < CAP[b]: POOL[k][j] = (resp, nota)
    if n >= SKIP + 1500000: break
print('amostra coletada em %.0fs' % (time.time() - t0), {k: len(v) for k, v in sorted(POOL.items())[:7]}, flush=True)
def matriz(lst, p):
    L = np.array([list(r.ljust(len(gab[p]), '.')[:len(gab[p])]) for r, _ in lst]); return (L == gab[p][None, :]), np.array([x for _, x in lst])
TR = {p: [] for p in PROVAS}; HO = {p: [] for p in PROVAS}
for (p, b), lst in POOL.items():
    random.shuffle(lst); cut = int(len(lst) * .8); TR[p] += lst[:cut]; HO[p] += lst[cut:]
TRm = {p: matriz(TR[p], p) for p in PROVAS}; HOm = {p: matriz(HO[p], p) for p in PROVAS}
print('treino:', {p: len(TR[p]) for p in PROVAS}, 'holdout:', {p: len(HO[p]) for p in PROVAS}, flush=True)
def theta_de(ok, mp, a, b, c):
    P_ = np.clip(c[:, None] + (1 - c[:, None]) / (1 + np.exp(-a[:, None] * (G[None, :] - b[:, None]))), 1e-9, 1 - 1e-9)
    lP = np.log(P_); lQ = np.log(1 - P_); sel = mp >= 0
    okf = ok[:, sel].astype(float); lPs = lP[mp[sel]]; lQs = lQ[mp[sel]]
    ll = okf @ lPs + (1 - okf) @ lQs; lp = ll - 0.5 * G[None, :] ** 2; w = np.exp(lp - lp.max(1, keepdims=True)); return (w * G).sum(1) / w.sum(1)
def vec(x): return np.exp(x[:NI]), x[NI:2 * NI], 1 / (1 + np.exp(-x[2 * NI:]))
def resid(x, data):
    a, b, c = vec(x); out = []
    for p in PROVAS:
        ok, nota = data[p]; out.append(m + s * theta_de(ok, mapa[p], a, b, c) - nota)
    return np.concatenate(out)
def aval(x, data):
    r = np.abs(resid(x, data)); return float(r.mean()), float((r < 1).mean() * 100), float((r < .1).mean() * 100)
x0 = np.load(W / 'diag' / 'x_mt2013.npy')   # parte da solução do 1º refinamento
print('ANTES  treino MAE/<1/<0,1: %.3f %.2f%% %.2f%% | holdout: %.3f %.2f%% %.2f%%' % (*aval(x0, TRm), *aval(x0, HOm)), flush=True)
t1 = time.time(); sol = least_squares(resid, x0, args=(TRm,), loss='soft_l1', f_scale=0.12, max_nfev=int(sys.argv[1]) if len(sys.argv) > 1 else 50, diff_step=1e-4, verbose=0)
print('refino em %.0fs, nfev=%d' % (time.time() - t1, sol.nfev), flush=True)
print('DEPOIS treino MAE/<1/<0,1: %.3f %.2f%% %.2f%% | holdout: %.3f %.2f%% %.2f%%' % (*aval(sol.x, TRm), *aval(sol.x, HOm)), flush=True)
np.save(W / 'diag' / 'x_mt2013_v2.npy', sol.x); json.dump(cods, open(W / 'diag' / 'cods_mt2013.json', 'w'))
