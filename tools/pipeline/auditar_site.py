"""Auditoria independente dos artefatos finais do site: manifesto x dados/enem_ANO.json x relatórios de validação.
Uso: python -I auditar_site.py   -> imprime problemas (vazio = consistente) e um resumo por ano.
"""
import json, re, pathlib
raiz = pathlib.Path(__file__).parent.parent.parent
html = (raiz / 'index.html').read_text(encoding='utf-8')
man = json.loads(re.search(r'const MANIFEST = (\[.*?\]);\nconst HABS', html, re.S).group(1))
val = json.loads((raiz / 'tools' / 'validacao_por_ano.json').read_text(encoding='utf-8'))
probs = []; resumo = []
LET = set('ABCDE')
for m in man:
    ano = m['ano']; f = raiz / 'dados' / f'enem_{ano}.js'
    if not f.exists(): probs.append(f'{ano}: dados ausentes'); continue
    d = json.loads(f.read_text(encoding='utf-8').split('=',2)[2].rstrip().rstrip(';')); n_enun = 0; n_alt5 = 0
    for a, info in m['areas'].items():
        it = d['items'].get(a); cad = d['cad'].get(a)
        if not it or not cad: probs.append(f'{ano} {a}: sem itens/cadernos'); continue
        for cor, v in cad.items():
            listas = v if isinstance(v[0], list) else [v]
            for L in listas:
                if len(L) != 45: probs.append(f'{ano} {a} {cor}: caderno com {len(L)} itens')
                if any((not isinstance(i, int)) or i < 0 or i >= len(it) for i in L): probs.append(f'{ano} {a} {cor}: índice de item inválido')
                if len(set(L)) != len(L): probs.append(f'{ano} {a} {cor}: item repetido no caderno')
        for i, x in enumerate(it):
            aban = x[0] is None
            if not aban and not (x[0] > 0 and 0 <= x[2] <= 1): probs.append(f'{ano} {a} item {i}: parâmetros fora do esperado {x[:3]}')
            if x[4] not in LET and not (aban and x[4] in ('X', '*', '')): probs.append(f'{ano} {a} item {i}: gabarito "{x[4]}"')
        k = d['k'].get(a); classe = info['classe']
        if classe in ('EXATO', 'ESTIMADO') and not k: probs.append(f'{ano} {a}: {classe} sem constantes')
        if classe == 'NAO_VALIDO' and k: probs.append(f'{ano} {a}: sem TRI mas com constantes')
        if classe == 'ESTIMADO' and not d.get('band', {}).get(a): probs.append(f'{ano} {a}: estimado sem margem')
        if classe == 'EXATO' and k:
            ref = {'CN': (501.144, 113.102), 'CH': (501.489, 112.31), 'LC': (499.978, 108.086), 'MT': (500.02, 129.646)}[a]
            if abs(k[0] - ref[0]) > 0.01 or abs(k[1] - ref[1]) > 0.01: probs.append(f'{ano} {a}: EXATO com constantes diferentes das universais {k}')
        e = d.get('enun', {}).get(a, {})
        for ix, v in e.items():
            if int(ix) >= len(it): probs.append(f'{ano} {a}: enunciado com índice {ix} fora dos itens')
            n_enun += 1; n_alt5 += sum(1 for t in v['a'] if t) == 5
        if classe != val[str(ano)]['areas'][a]['classe']: probs.append(f'{ano} {a}: classe do manifesto difere da validação')
    for dia in ('1', '2'):
        if dia in m['links'] and len(m['links'][dia]) < 4: probs.append(f'{ano}: dia {dia} com só {len(m["links"][dia])} links de prova')
    if not m['links']: probs.append(f'{ano}: sem links de prova')
    resumo.append((ano, f.stat().st_size // 1024, n_enun, n_alt5, sorted(m['cores'].get('1', [])), sorted(m['cores'].get('2', [])), len(m['links'].get('1', {})) + len(m['links'].get('2', {}))))
print('ano   dados(KB)  enunciados  c/5 alternativas  cores dia1 / dia2  links')
for r in resumo: print(f'{r[0]}  {r[1]:>8}  {r[2]:>10}  {r[3]:>16}  {len(r[4])}/{len(r[5])}                {r[6]}')
print('\nPROBLEMAS:', 'nenhum' if not probs else '')
for p in probs: print(' -', p)
