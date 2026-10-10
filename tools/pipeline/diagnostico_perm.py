"""Hipótese: nas provas que não validam, os parâmetros a,b,c de alguns itens estão trocados de posição no arquivo ITENS.
Para cada coluna de resposta j, acha o item i cuja curva P_i(theta) melhor descreve o acerto observado (atribuição ótima / húngaro),
usando theta = (nota oficial - m)/s com as constantes universais. Se a atribuição for quase identidade com poucas trocas e a nota
passar a bater, a causa está confirmada.
Uso: python -I diagnostico_perm.py <ano> <area> <prova> [n=20000]
"""
import sys, json, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
from scipy.optimize import linear_sum_assignment
import enem_pipeline as P

K0 = P.K0
ano, area, prova = int(sys.argv[1]), sys.argv[2], sys.argv[3]; N = int(sys.argv[4]) if len(sys.argv) > 4 else 20000
f = P.Fonte(f'C:/dev/enem/_work/zips/microdados_enem_{ano}.zip'); nome = f.achar(r'^(microdados|resultados)')
itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens)
R = []
for a, p, lg, resp, nota in P.participantes(f, nome):
    if a == area and p == prova and not P.em_branco(resp):
        R.append((lg, resp, nota))
        if len(R) >= N: break
lg = collections.Counter(l for l, _, _ in R).most_common(1)[0][0]; R = [(r, n) for l, r, n in R if l == lg]
d = cad[(area, prova)]; its = d['langs'].get(lg) or next(iter(d['langs'].values())); n = len(its)
gab = np.array([x['gab'] for x in its]); aban = np.array([x['a'] is None or x['aban'] for x in its])
A = np.array([x['a'] or 0 for x in its]); B = np.array([x['b'] or 0 for x in its]); C = np.array([x['c'] or 0 for x in its])
L = np.array([list(P.normalizar_resp(area, r, n, lg).ljust(n, '.')[:n]) for r, _ in R]); ok = L == gab[None, :]; nota = np.array([x for _, x in R])
m, s = K0[area]; th_off = (nota - m) / s
bins = 14; qs = np.quantile(th_off, np.linspace(0, 1, bins + 1)); idx = np.clip(np.searchsorted(qs, th_off, side='right') - 1, 0, bins - 1); w = np.array([(idx == k).sum() for k in range(bins)], float)
Obs = np.array([[ok[idx == k, j].mean() for k in range(bins)] for j in range(n)])
Mod = np.array([[ (C[i] + (1 - C[i]) / (1 + np.exp(-A[i] * (th_off[idx == k] - B[i])))).mean() for k in range(bins)] for i in range(n)])
valid = [i for i in range(n) if not aban[i]]
cost = np.array([[ (w * (Obs[j] - Mod[i]) ** 2).sum() / w.sum() for i in valid] for j in valid])
ri, ci = linear_sum_assignment(cost)
atrib = {valid[r]: valid[c] for r, c in zip(ri, ci)}   # coluna j  -> item i
trocas = {j + 1: i + 1 for j, i in atrib.items() if j != i}
ident = sum(cost[r, r] for r in range(len(valid))); otimo = cost[ri, ci].sum()
print(f'{ano} {area} prova {prova}: n={len(nota)} | custo identidade={ident:.4f} -> ótimo={otimo:.4f} | colunas reatribuídas: {len(trocas)} de {len(valid)}')
print('  reatribuições (coluna -> item cujos parâmetros descrevem a coluna):', dict(list(trocas.items())[:24]))
def mae(Ap, Bp, Cp):
    G = P.GRID; ll = np.zeros((len(L), len(G)))
    for j in valid:
        p = np.clip(Cp[j] + (1 - Cp[j]) / (1 + np.exp(-Ap[j] * (G - Bp[j]))), 1e-9, 1 - 1e-9)
        ll += np.where(ok[:, j][:, None], np.log(p)[None, :], np.log(1 - p)[None, :])
    lp = ll - 0.5 * G[None, :] ** 2; ww = np.exp(lp - lp.max(1, keepdims=True)); th = (ww * G).sum(1) / ww.sum(1)
    e = np.abs(m + s * th - nota); return float(e.mean()), float((e < 1).mean() * 100), float(np.corrcoef(th, nota)[0, 1])
perm = np.arange(n)
for j, i in atrib.items(): perm[j] = i
print('  nota com parâmetros publicados:   MAE=%.2f | dentro de 1 pt=%.1f%% | corr=%.4f' % mae(A, B, C))
print('  nota com parâmetros reatribuídos: MAE=%.2f | dentro de 1 pt=%.1f%% | corr=%.4f' % mae(A[perm], B[perm], C[perm]))
json.dump(dict(ano=ano, area=area, prova=prova, lingua=lg, trocas=trocas), open(f'C:/dev/enem/_work/saida/perm_{ano}_{area}_{prova}.json', 'w'))
