"""Recupera os parâmetros corretos de itens que estão trocados de lugar no ITENS_PROVA (anos que não validam).

Passos (por ano/área): (1) atribuição ótima coluna->item por curva de acerto; (2) busca local de trocas que minimiza o erro da nota
oficial (constantes universais); (3) mapa por CO_ITEM; (4) VALIDAÇÃO nos outros cadernos, nunca usados no ajuste.
Uso: python -I corrigir_params.py <ano> <area> [n_ajuste=6000]
Saída: C:/dev/enem/_work/saida/params_ANO_AREA.json  {"doador": {CO_ITEM: CO_ITEM cujos parâmetros ele deve usar}, "validacao": {...}}
"""
import sys, json, collections, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
from scipy.optimize import linear_sum_assignment
import enem_pipeline as P

W = pathlib.Path('C:/dev/enem/_work'); G = P.GRID


def carregar(f, nome, cad, rel, area, prova_alvo, n):
    R = []
    for a, p, lg, resp, nota in P.participantes(f, nome):
        if a == area and p == prova_alvo and not P.em_branco(resp):
            R.append((lg, resp, nota))
            if len(R) >= n: break
    return R


def montar(cad, area, prova, R):
    lg = collections.Counter(l for l, _, _ in R).most_common(1)[0][0]; R = [(r, x) for l, r, x in R if l == lg]
    d = cad[(area, prova)]; its = d['langs'].get(lg) or next(iter(d['langs'].values())); n = len(its)
    gab = np.array([x['gab'] for x in its]); L = np.array([list(P.normalizar_resp(area, r, n, lg).ljust(n, '.')[:n]) for r, _ in R])
    return its, (L == gab[None, :]), np.array([x for _, x in R]), lg


def mae_params(ok, nota, A, B, C, aban, m, s):
    P_ = np.clip(C[:, None] + (1 - C[:, None]) / (1 + np.exp(-A[:, None] * (G[None, :] - B[:, None]))), 1e-9, 1 - 1e-9)
    lP = np.log(P_); lQ = np.log(1 - P_); lP[aban] = 0; lQ[aban] = 0
    okf = ok.astype(float); ll = okf @ lP + (1 - okf) @ lQ
    lp = ll - 0.5 * G[None, :] ** 2; w = np.exp(lp - lp.max(1, keepdims=True)); th = (w * G).sum(1) / w.sum(1)
    e = np.abs(m + s * th - nota); return float(e.mean()), float((e < 1).mean() * 100), float((e < 0.1).mean() * 100)


def resolver(ano, area, n=6000, incluir_aban=False):
    rel = json.loads((W / 'saida' / f'relatorio2_{ano}.json').read_text(encoding='utf-8'))
    f = P.Fonte(W / 'zips' / f'microdados_enem_{ano}.zip'); nome = f.achar(r'^(microdados|resultados)')
    itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens); m, s = P.K0[area]
    provas = rel['areas'][area]['provas_regulares']
    alvo = provas[0]
    R = carregar(f, nome, cad, rel, area, alvo, 3 * n)
    its, ok_all, nota_all, lg = montar(cad, area, alvo, R)
    ok, nota = ok_all[:n], nota_all[:n]; ok_v, nota_v = ok_all[n:], nota_all[n:]
    N_it = len(its); aban = np.array([x['a'] is None or x['aban'] for x in its])
    A0 = np.array([x['a'] or 0 for x in its]); B0 = np.array([x['b'] or 0 for x in its]); C0 = np.array([x['c'] or 0 for x in its])
    if incluir_aban:   # itens sem parâmetros no arquivo entram com valores iniciais típicos e parâmetros livres
        for i in range(N_it):
            if aban[i]: A0[i], B0[i], C0[i] = 1.4, 0.5, 0.15
        aban = np.zeros(N_it, bool)
        print('   itens sem parâmetros incluídos:', [(i + 1, its[i]['item']) for i in range(N_it) if its[i]['a'] is None or its[i]['aban']], flush=True)
    valid = [i for i in range(N_it) if not aban[i]]
    # (1) atribuição ótima
    th_off = (nota - m) / s; bins = 14; qs = np.quantile(th_off, np.linspace(0, 1, bins + 1)); idx = np.clip(np.searchsorted(qs, th_off, side='right') - 1, 0, bins - 1); w = np.array([(idx == k).sum() for k in range(bins)], float)
    Obs = np.array([[ok[idx == k, j].mean() for k in range(bins)] for j in range(N_it)])
    Mod = np.array([[(C0[i] + (1 - C0[i]) / (1 + np.exp(-A0[i] * (th_off[idx == k] - B0[i])))).mean() for k in range(bins)] for i in range(N_it)])
    cost = np.array([[(w * (Obs[j] - Mod[i]) ** 2).sum() / w.sum() for i in valid] for j in valid]); ri, ci = linear_sum_assignment(cost)
    perm = np.arange(N_it)
    for r_, c_ in zip(ri, ci): perm[valid[r_]] = valid[c_]
    base = mae_params(ok, nota, A0, B0, C0, aban, m, s); cur = mae_params(ok, nota, A0[perm], B0[perm], C0[perm], aban, m, s)
    print(f'{ano} {area} prova {alvo}: publicado MAE={base[0]:.2f} | após atribuição ótima MAE={cur[0]:.2f}', flush=True)
    # (2) busca local de trocas (primeira melhora) até estabilizar
    best = cur[0]; t0 = time.time()
    for varredura in range(12):
        melhorou = False
        for a_ in range(len(valid)):
            for b_ in range(a_ + 1, len(valid)):
                j1, j2 = valid[a_], valid[b_]
                if perm[j1] == perm[j2]: continue
                perm[j1], perm[j2] = perm[j2], perm[j1]
                e = mae_params(ok, nota, A0[perm], B0[perm], C0[perm], aban, m, s)[0]
                if e < best - 1e-6: best = e; melhorou = True
                else: perm[j1], perm[j2] = perm[j2], perm[j1]
        print(f'   varredura {varredura + 1}: MAE={best:.3f} ({time.time() - t0:.0f}s)', flush=True)
        if not melhorou or best < 0.04: break
    # (2b) refinamento contínuo (mínimos quadrados robusto) partindo do arranjo achado
    from scipy.optimize import least_squares
    Ap, Bp, Cp = A0[perm].copy(), B0[perm].copy(), C0[perm].copy(); vi = np.array(valid)
    def vec(x):
        a, b, c = Ap.copy(), Bp.copy(), Cp.copy(); k = len(vi)
        a[vi] = np.exp(x[:k]); b[vi] = x[k:2 * k]; c[vi] = 1 / (1 + np.exp(-x[2 * k:])); return a, b, c
    def resid(x):
        a, b, c = vec(x)
        P_ = np.clip(c[:, None] + (1 - c[:, None]) / (1 + np.exp(-a[:, None] * (G[None, :] - b[:, None]))), 1e-9, 1 - 1e-9)
        lP = np.log(P_); lQ = np.log(1 - P_); lP[aban] = 0; lQ[aban] = 0
        okf = ok.astype(float); ll = okf @ lP + (1 - okf) @ lQ
        lp = ll - 0.5 * G[None, :] ** 2; w = np.exp(lp - lp.max(1, keepdims=True)); th = (w * G).sum(1) / w.sum(1)
        return m + s * th - nota
    x0 = np.concatenate([np.log(np.clip(Ap[vi], 1e-3, None)), Bp[vi], np.log(np.clip(Cp[vi], 1e-4, 0.6) / (1 - np.clip(Cp[vi], 1e-4, 0.6)))])
    t1 = time.time(); sol = least_squares(resid, x0, loss='soft_l1', f_scale=0.5, max_nfev=80, diff_step=1e-4)
    A1, B1, C1 = vec(sol.x); e_ref = mae_params(ok, nota, A1, B1, C1, aban, m, s)
    print(f'   refinamento contínuo ({time.time() - t1:.0f}s): MAE ajuste={e_ref[0]:.3f} dentro de 1 pt={e_ref[1]:.1f}%', flush=True)
    if e_ref[0] < best: A0r, B0r, C0r = A1, B1, C1
    else: A0r, B0r, C0r = A0[perm], B0[perm], C0[perm]
    fim = mae_params(ok_v, nota_v, A0r, B0r, C0r, aban, m, s); pub_v = mae_params(ok_v, nota_v, A0, B0, C0, aban, m, s)
    print(f'   HOLD-OUT (mesmo caderno, outros participantes): publicado MAE={pub_v[0]:.2f}/{pub_v[1]:.1f}% -> corrigido MAE={fim[0]:.3f}, dentro de 1 pt={fim[1]:.2f}%, dentro de 0,1={fim[2]:.1f}%', flush=True)
    # (3) mapa por CO_ITEM: o item na coluna j usa os parâmetros do item da linha perm[j]
    doador = {its[j]['item']: its[int(perm[j])]['item'] for j in range(N_it) if perm[j] != j}
    finais = {its[j]['item']: [round(float(A0r[j]), 5), round(float(B0r[j]), 5), round(float(C0r[j]), 5)] for j in range(N_it) if not aban[j]}
    # (4) validação nos OUTROS cadernos (mapeando por CO_ITEM)
    pars = {x['item']: (x['a'], x['b'], x['c']) for x in its if x['a'] is not None}
    valid_out = {}
    for outra in provas[1:]:
        R2 = carregar(f, nome, cad, rel, area, outra, 4000)
        if len(R2) < 500: continue
        its2, ok2, nota2, lg2 = montar(cad, area, outra, R2)
        ab2 = np.array([x['item'] not in finais for x in its2])
        def vet(corr):
            arr = []
            for x in its2:
                pr = (finais.get(x['item']) if corr else pars.get(x['item'])) or (x['a'], x['b'], x['c'])
                arr.append([(v if v is not None else 0) for v in pr])
            arr = np.array(arr); return arr[:, 0], arr[:, 1], arr[:, 2]
        a1, b1, c1 = vet(False); a2, b2, c2 = vet(True)
        pub = mae_params(ok2, nota2, a1, b1, c1, ab2, m, s); cor = mae_params(ok2, nota2, a2, b2, c2, ab2, m, s)
        valid_out[outra] = dict(n=len(nota2), publicado_mae=round(pub[0], 3), corrigido_mae=round(cor[0], 3), corrigido_dentro_1=round(cor[1], 2), corrigido_dentro_0_1=round(cor[2], 1))
        print(f'   CADERNO {outra} (não usado no ajuste): publicado MAE={pub[0]:.2f} -> corrigido MAE={cor[0]:.3f} | dentro de 1 pt={cor[1]:.2f}% | de 0,1={cor[2]:.1f}%', flush=True)
    out = dict(ano=ano, area=area, prova_ajuste=alvo, doador=doador, params=finais, mae_final_ajuste=best, holdout=dict(mae=fim[0], dentro_1=fim[1], dentro_0_1=fim[2]), validacao_outros_cadernos=valid_out)
    (W / 'saida' / f'params_{ano}_{area}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    return out


if __name__ == '__main__':
    resolver(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6000, len(sys.argv) > 4 and sys.argv[4] == '1')
