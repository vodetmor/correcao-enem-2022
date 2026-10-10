"""Diagnóstico das áreas que não reproduzem a nota oficial: testa hipóteses sobre COMO o INEP calculou (k, c, prior, grade).
Uso: python -I diagnostico_falhas.py <ano> <area> <prova> [n=4000]
"""
import sys, json, collections, itertools, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
import enem_pipeline as P

ano, area, prova = int(sys.argv[1]), sys.argv[2], sys.argv[3]; N = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
f = P.Fonte(f'C:/dev/enem/_work/zips/microdados_enem_{ano}.zip'); nome = f.achar(r'^(microdados|resultados)')
itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens)
R = []
for a, p, lg, resp, nota in P.participantes(f, nome):
    if a == area and p == prova and not P.em_branco(resp):
        R.append((lg, resp, nota))
        if len(R) >= N: break
por = collections.Counter(l for l, _, _ in R); lg = por.most_common(1)[0][0]
R = [(r, n) for l, r, n in R if l == lg]
d = cad[(area, prova)]; its = d['langs'].get(lg) or next(iter(d['langs'].values())); n = len(its)
gab = np.array([x['gab'] for x in its]); aban = np.array([x['a'] is None or x['aban'] for x in its])
A = np.array([x['a'] or 0 for x in its]); B = np.array([x['b'] or 0 for x in its]); C = np.array([x['c'] or 0 for x in its])
L = np.array([list(P.normalizar_resp(area, r, n, lg).ljust(n, '.')[:n]) for r, _ in R]); ok = L == gab[None, :]; nota = np.array([x for _, x in R])
print(f'{ano} {area} prova {prova} lingua {lg!r}: n={len(nota)} itens={n} aban={int(aban.sum())} | nota oficial {nota.min():.0f}..{nota.max():.0f}')
print('  itens aban no arquivo:', [(i + 1, its[i]['item'], its[i]['motivo'][:40]) for i in range(n) if aban[i]][:6])
G = np.linspace(-4, 4, 40)

def theta(k=1.0, cmul=1.0, mu=0.0, sg=1.0, amul=1.0, grid=G, usa_aban=False):
    ll = np.zeros((len(L), len(grid)))
    for i in range(n):
        if aban[i]: continue
        c = min(0.99, C[i] * cmul)
        p = np.clip(c + (1 - c) / (1 + np.exp(-k * amul * A[i] * (grid - B[i]))), 1e-9, 1 - 1e-9)
        ll += np.where(ok[:, i][:, None], np.log(p)[None, :], np.log(1 - p)[None, :])
    lp = ll - 0.5 * ((grid - mu) / sg) ** 2
    w = np.exp(lp - lp.max(1, keepdims=True)); return (w * grid).sum(1) / w.sum(1)

def err(th):
    s, m = np.polyfit(th, nota, 1)
    for _ in range(3):
        r = nota - (m + s * th); keep = np.abs(r) < 3 * max(r.std(), .05); s, m = np.polyfit(th[keep], nota[keep], 1)
    r = nota - (m + s * th); return float(np.abs(r).mean()), float(m), float(s), float(np.corrcoef(th, nota)[0, 1])

base = err(theta()); print(f'  referência (k=1, c, N(0,1)): MAE={base[0]:.2f} m={base[1]:.1f} s={base[2]:.1f} corr={base[3]:.4f}')
res = []
for k in (0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.7, 2.0, 2.5):
    for cmul in (0.0, 0.5, 1.0, 1.5):
        e = err(theta(k=k, cmul=cmul)); res.append((e[0], f'k={k} c*{cmul}', e))
res.sort(key=lambda x: x[0])
print('  melhores variantes de k e c:'); [print(f'    MAE={r[0]:.2f} {r[1]} m={r[2][1]:.1f} s={r[2][2]:.1f} corr={r[2][3]:.4f}') for r in res[:4]]
# gabarito alternativo por item: para cada item, aceitar cada outra letra como certa
melhor = (base[0], None)
for i in range(n):
    if aban[i]: continue
    for alt in 'ABCDE':
        if alt == gab[i]: continue
        ok2 = ok.copy(); ok2[:, i] = ok[:, i] | (L[:, i] == alt)
        ll = np.zeros((len(L), len(G)))
        for j in range(n):
            if aban[j]: continue
            p = np.clip(C[j] + (1 - C[j]) / (1 + np.exp(-A[j] * (G - B[j]))), 1e-9, 1 - 1e-9)
            ll += np.where(ok2[:, j][:, None], np.log(p)[None, :], np.log(1 - p)[None, :])
        w = np.exp(ll - 0.5 * G[None, :] ** 2 - (ll - 0.5 * G[None, :] ** 2).max(1, keepdims=True)); th = (w * G).sum(1) / w.sum(1)
        e = err(th)
        if e[0] < melhor[0]: melhor = (e[0], (i + 1, its[i]['item'], alt))
print('  melhor "gabarito duplo" (1 item aceita outra letra):', melhor)
