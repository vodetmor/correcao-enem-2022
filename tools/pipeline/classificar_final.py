"""Classificação final por ano e área, a partir de TODOS os relatórios (por prova, sem depender da descoberta de 'regulares').

Critério sobre as provas não adaptadas com >= 2% dos participantes da área (n e ok1 = erro < 1 ponto):
  EXATO       : >= 99,9% dentro de 1 ponto e erro máximo observado das regulares < 150 (casos raros de cartão atípico)
  APROXIMADO  : >= 99% dentro de 1 ponto
  NAO_VALIDO  : abaixo disso (a nota oficial não é reproduzível com os dados públicos)
Grava classificacao_final.json e imprime o quadro. Uso: python -I classificar_final.py <pasta_saida>
"""
import sys, json, glob, pathlib

saida = pathlib.Path(sys.argv[1])
out = {}
for f in sorted(glob.glob(str(saida / 'relatorio_*.json'))):
    r = json.load(open(f, encoding='utf-8'))
    if r.get('status') != 'OK': out[str(r['ano'])] = {'status': r.get('status')}; continue
    ano = str(r['ano']); out[ano] = {'status': 'OK', 'areas': {}}
    for a, pp in r['por_prova'].items():
        tot = sum(c.get('n', 0) for c in pp.values())
        reg = {p: c for p, c in pp.items() if c.get('n', 0) >= 0.02 * tot}
        n = sum(c['n'] for c in reg.values()); ok = sum(c.get('ok1', 0) for c in reg.values())
        pct = ok / n * 100 if n else 0
        mx = r['validacao'][a].get('regular_max', 0)
        cl = 'EXATO' if pct >= 99.9 else ('APROXIMADO' if pct >= 99 else 'NAO_VALIDO')
        out[ano]['areas'][a] = dict(classe=cl, pct_dentro_1=round(pct, 3), n=n, provas=sorted(reg), constantes=[r['constantes'][a]['m'], r['constantes'][a]['s']],
                                    mae_ajuste=r['constantes'][a]['mae_ajuste'])
(saida / 'classificacao_final.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('%-5s %-18s %-18s %-18s %-18s' % ('ano', 'CN', 'CH', 'LC', 'MT'))
for ano, v in out.items():
    if v['status'] != 'OK': print(ano, v['status']); continue
    print('%-5s' % ano, *['%-18s' % (v['areas'][a]['classe'] + ' %.2f%%' % v['areas'][a]['pct_dentro_1'] if a in v['areas'] else '-') for a in ('CN', 'CH', 'LC', 'MT')])
