"""Confiabilidade dos parâmetros dos itens: ajuste item a item contra o comportamento real dos participantes.

Para cada (ano, área): pega até N participantes de um caderno regular, converte a NOTA OFICIAL em proficiência (theta = (nota - m)/s),
agrupa em faixas de theta e compara, para cada item, a taxa observada de acerto com a prevista por P(theta) = c + (1-c)/(1+exp(-a(theta-b))).
Métrica por item: RMSE ponderado entre observado e previsto (erro de amostragem típico fica abaixo de ~0,02 com N=25 mil).
Uso: python -I item_fit.py <ano> -> grava C:/dev/enem/_work/saida/item_fit_ANO.json
"""
import sys, json, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
import enem_pipeline as P

W = pathlib.Path('C:/dev/enem/_work')


def item_fit_ano(ano, nmax=25000, bins=12, max_linhas=800000):
    rel = json.loads((W / 'saida' / f'relatorio2_{ano}.json').read_text(encoding='utf-8'))
    f = P.Fonte(W / 'zips' / f'microdados_enem_{ano}.zip'); nome = f.achar(r'^(microdados|resultados)')
    itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens)
    primeira = {}; rows = {a: [] for a in P.AREAS}; n = 0
    for a, prova, lg, resp, nota in P.participantes(f, nome):
        n += 1
        if n > max_linhas: break
        if a not in rel['areas'] or P.em_branco(resp): continue
        if prova not in rel['areas'][a]['provas_regulares']: continue
        primeira.setdefault(a, prova)
        if prova == primeira[a] and len(rows[a]) < nmax: rows[a].append((lg, resp, nota))
        if all(len(rows[x]) >= nmax for x in rel['areas']): break
    saida = {}
    for a, info in rel['areas'].items():
        R = rows[a]
        if len(R) < 2000: saida[a] = dict(erro='poucos participantes'); continue
        por = collections.Counter(lg for lg, _, _ in R); lg = por.most_common(1)[0][0]
        R = [(r, nt) for l, r, nt in R if l == lg]
        prova = primeira[a]; d = cad[(a, prova)]; its = d['langs'].get(lg) or next(iter(d['langs'].values()))
        gab = np.array([x['gab'] for x in its]); n_it = len(its)
        L = np.array([list(P.normalizar_resp(a, r, n_it, lg).ljust(n_it, '.')[:n_it]) for r, _ in R]); ok = (L == gab[None, :])
        nota = np.array([nt for _, nt in R])
        m, s = (info['ajuste']['m'], info['ajuste']['s']) if 'ajuste' in info else info['constantes']
        th = (nota - m) / s
        qs = np.quantile(th, np.linspace(0, 1, bins + 1)); idx = np.clip(np.searchsorted(qs, th, side='right') - 1, 0, bins - 1)
        res = []
        for i, x in enumerate(its):
            if x['aban'] or x['a'] is None: continue
            p = x['c'] + (1 - x['c']) / (1 + np.exp(-x['a'] * (th - x['b'])))
            ob = np.array([ok[idx == k, i].mean() for k in range(bins)]); ex = np.array([p[idx == k].mean() for k in range(bins)]); w = np.array([(idx == k).sum() for k in range(bins)])
            rm = float(np.sqrt((w * (ob - ex) ** 2).sum() / w.sum())); vies = float((w * (ob - ex)).sum() / w.sum())
            res.append((rm, vies, i, x['item'], x['a'], x['b'], x['c'], float(ok[:, i].mean())))
        rms = np.array([r[0] for r in res])
        pior = sorted(res, reverse=True)[:3]
        saida[a] = dict(classe=info['classe'], prova=prova, n=len(R), itens=len(res), rmse_mediana=round(float(np.median(rms)), 4), rmse_p90=round(float(np.percentile(rms, 90)), 4),
                        rmse_max=round(float(rms.max()), 4), itens_acima_0_04=int((rms > 0.04).sum()), itens_acima_0_06=int((rms > 0.06).sum()),
                        piores=[dict(posicao=r[2] + 1, co_item=r[3], rmse=round(r[0], 3), vies_obs_menos_prev=round(r[1], 3), a=round(r[4], 2), b=round(r[5], 2), c=round(r[6], 2), taxa_acerto=round(r[7], 2)) for r in pior])
    return saida


if __name__ == '__main__':
    ano = int(sys.argv[1]); out = item_fit_ano(ano)
    (W / 'saida' / f'item_fit_{ano}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(ano, {a: (v.get('classe'), v.get('rmse_mediana'), v.get('itens_acima_0_06')) for a, v in out.items()})
