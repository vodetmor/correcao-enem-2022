"""Auditoria de itens para áreas que não validam: qual item o INEP tratou diferente do arquivo de itens?

Para uma (ano, área, prova), testa variantes por item: (a) retirar o item do cálculo; (b) contar como certo para todos.
Escolhe gulosamente o item que mais melhora o ajuste linear nota ~ theta e para quando o erro cai a ~0 ou não melhora.
Uso: python -I auditar_itens.py <zip> <ano> <area> <prova> [amostra=6000] [max_itens=6]
"""
import sys, json, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
import enem_pipeline as P


def theta_variante(pc, L, retirar=(), certos=()):
    ok = L == pc['gab'][None, :]
    for i in certos: ok[:, i] = True
    aban = pc['aban'].copy()
    for i in retirar: aban[i] = True
    ll = np.zeros((len(L), len(P.GRID)))
    for i in range(pc['n']):
        if aban[i]: continue
        ll += np.where(ok[:, i][:, None], pc['lP'][i][None, :], pc['lQ'][i][None, :])
    lp = ll - 0.5 * P.GRID[None, :] ** 2
    w = np.exp(lp - lp.max(1, keepdims=True))
    return (w * P.GRID).sum(1) / w.sum(1)


def erro_ajuste(th, nota):
    s, m = np.polyfit(th, nota, 1)
    for _ in range(3):
        ok = np.abs(nota - (m + s * th)) < 3 * max(np.abs(nota - (m + s * th)).std(), 0.05)
        s, m = np.polyfit(th[ok], nota[ok], 1)
    r = nota - (m + s * th)
    return float(np.abs(r).mean()), float(m), float(s), float((np.abs(r) < 0.1).mean() * 100)


def auditar(zip_path, area, prova, amostra=6000, max_itens=6):
    f = P.Fonte(zip_path); nome = f.achar(r'^(microdados|resultados)')
    itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens)
    L0, notas, lgs = [], [], []
    for a, p, lg, resp, nota in P.participantes(f, nome):
        if a == area and p == prova and not P.em_branco(resp):
            L0.append((lg, resp, nota))
            if len(L0) >= amostra: break
    por_lg = collections.defaultdict(list)
    for lg, r, n in L0: por_lg[lg].append((r, n))
    lg = max(por_lg, key=lambda k: len(por_lg[k])); resp = [r for r, _ in por_lg[lg]]; nota = np.array([n for _, n in por_lg[lg]])
    pc = P.prep_caderno(cad, area, prova, lg)
    L = np.array([list(r.ljust(pc['n'], '.')[:pc['n']]) for r in resp])
    its = cad[(area, prova)]['langs'].get(lg) or next(iter(cad[(area, prova)]['langs'].values()))
    base_err = erro_ajuste(theta_variante(pc, L), nota)
    hist = [dict(passo=0, mudanca='nenhuma', mae=round(base_err[0], 3), m=round(base_err[1], 3), s=round(base_err[2], 3), dentro_0_1=round(base_err[3], 2))]
    ret, cer = [], []; atual = base_err[0]
    for passo in range(1, max_itens + 1):
        melhor = None
        for i in range(pc['n']):
            if i in ret or i in cer: continue
            for modo in ('retirar', 'certo'):
                r2 = ret + [i] if modo == 'retirar' else ret; c2 = cer + [i] if modo == 'certo' else cer
                e = erro_ajuste(theta_variante(pc, L, r2, c2), nota)
                if melhor is None or e[0] < melhor[0][0]: melhor = (e, i, modo)
        e, i, modo = melhor
        if e[0] > atual * 0.85: break
        (ret if modo == 'retirar' else cer).append(i); atual = e[0]
        hist.append(dict(passo=passo, mudanca=f'{modo} item posicao_no_caderno={i + 1} CO_ITEM={its[i]["item"]} gab={its[i]["gab"]} aban={its[i]["aban"]}',
                         mae=round(e[0], 3), m=round(e[1], 3), s=round(e[2], 3), dentro_0_1=round(e[3], 2)))
        if e[0] < 0.1: break
    return dict(zip=str(zip_path), area=area, prova=prova, idioma=lg, n=len(nota), historico=hist, retirar=[its[i]['item'] for i in ret], certos=[its[i]['item'] for i in cer])


if __name__ == '__main__':
    a = sys.argv
    r = auditar(a[1], a[3], a[4], int(a[5]) if len(a) > 5 else 6000, int(a[6]) if len(a) > 6 else 6)
    out = pathlib.Path('C:/dev/enem/_work/saida') / f'auditoria_{a[2]}_{a[3]}_{a[4]}.json'
    out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
    for h in r['historico']: print(h)
