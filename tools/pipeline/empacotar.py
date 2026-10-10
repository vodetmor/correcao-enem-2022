"""Etapa 3: monta o pacote de dados de um ano (o que o site consome) a partir do zip + relatório v2 + enunciados.

Uso: python -I empacotar.py <ano> [pasta_saida]
Entradas (em C:/dev/enem/_work): zips/microdados_enem_ANO.zip, saida/relatorio2_ANO.json, enunciados/enunciados_ANO.json e relatorio_enunciados_ANO.json.
Regras:
  - só entram áreas com classe EXATO ou ESTIMADO (NAO_VALIDO vira "acertos apenas", sem TRI);
  - a numeração e o dia vêm da numeração IMPRESSA lida nos PDFs (relatorio_enunciados.numeracao_impressa);
  - ESTIMADO usa as constantes ajustadas do ano e leva a margem (p95 do erro).
"""
import sys, json, re, pathlib, unicodedata
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import enem_pipeline as P

W = pathlib.Path('C:/dev/enem/_work')
NOMES = {'CN': 'Ciências da Natureza', 'CH': 'Ciências Humanas', 'LC': 'Linguagens e Códigos', 'MT': 'Matemática'}
LANG_NOME = {'0': 'Inglês', '1': 'Espanhol'}
ORDEM_COR = ['AZUL', 'AMARELA', 'BRANCA', 'ROSA', 'CINZA']


def cor_norm(c):
    c = unicodedata.normalize('NFD', c or '').encode('ascii', 'ignore').decode().upper().strip()
    return {'AMARELO': 'AMARELA', 'BRANCO': 'BRANCA'}.get(c, c)


def empacotar(ano, saida):
    rel = json.loads((W / 'saida' / f'relatorio2_{ano}.json').read_text(encoding='utf-8'))
    enr = json.loads((W / 'enunciados' / f'relatorio_enunciados_{ano}.json').read_text(encoding='utf-8')) if (W / 'enunciados' / f'relatorio_enunciados_{ano}.json').exists() else {}
    enu = json.loads((W / 'enunciados' / f'enunciados_{ano}.json').read_text(encoding='utf-8'))['itens'] if (W / 'enunciados' / f'enunciados_{ano}.json').exists() else {}
    num = enr.get('numeracao_impressa', {})
    f = P.Fonte(W / 'zips' / f'microdados_enem_{ano}.zip')
    itens, _ = P.carregar_itens(f); recuperadas = P.aplicar_override(itens, ano); cad = P.montar_cadernos(itens)
    avisos = []; areas = {}; dados = dict(items={}, cad={}, tert={}, k={}, enun={}, band={}); cores = {1: set(), 2: set()}; langs_ano = None
    sem_hab = True; tem_enun = bool(enu); provas_cor = {}
    for a in P.AREAS:
        info = rel.get('areas', {}).get(a)
        if not info: avisos.append(f'{a}: sem dados no relatório'); continue
        classe = info['classe']
        if classe not in ('EXATO', 'ESTIMADO'):
            avisos.append(f'{a}: TRI indisponível neste ano ({classe}); só acertos');
        idx = {}; lista = []; ids = []; por_cor = {}; bases = []
        for prova in info['provas_regulares']:
            d = cad.get((a, prova))
            if not d: continue
            cor = cor_norm(d['cor'])
            if cor in por_cor: continue
            provas_cor.setdefault(a, {})[prova] = cor
            listas = []
            for lg in sorted(d['langs']):
                its = d['langs'][lg]; bases.append(its[0]['pos'])
                seq = []
                for x in its:
                    k = x['item']
                    if k not in idx:
                        idx[k] = len(lista); ids.append(k)
                        mc = 0 if not x['aban'] else (1 if 'pedag' in x['motivo'] else 2)
                        lista.append([None, None, None, x['hab'], x['gab'], mc] if (x['aban'] or x['a'] is None) else [x['a'], x['b'], x['c'], x['hab'], x['gab'], 0])
                        if x['hab']: sem_hab = False
                    seq.append(idx[k])
                listas.append((lg, seq))
            if len(listas) == 1 and listas[0][0] == '': por_cor[cor] = listas[0][1]
            else:
                if langs_ano is None: langs_ano = [lg for lg, _ in listas]
                por_cor[cor] = [seq for _, seq in listas]
        if not por_cor: avisos.append(f'{a}: nenhum caderno regular'); continue
        n_imp = num.get(a)
        if n_imp: base, dia = n_imp['min'], n_imp['dia']
        else:
            base = min(bases); dia = 1 if base <= 46 else 2; avisos.append(f'{a}: numeração impressa não confirmada pelo PDF; usei CO_POSICAO')
        tam = {len(v) if isinstance(v[0], int) else len(v[0]) for v in por_cor.values()}
        if tam != {45}: avisos.append(f'{a}: tamanho de caderno {sorted(tam)}')
        bs = sorted(i[1] for i in lista if i[1] is not None)
        dados['items'][a] = lista; dados['cad'][a] = por_cor; dados['tert'][a] = [round(bs[len(bs) // 3], 3), round(bs[2 * len(bs) // 3], 3)]
        if classe == 'EXATO': dados['k'][a] = info['constantes']
        elif classe == 'ESTIMADO':
            aj = info['ajuste']; dados['k'][a] = [aj['m'], aj['s']]; dados['band'][a] = aj['p95']
        else: dados['k'][a] = None
        if tem_enun:
            e = {}
            for i, co in enumerate(ids):
                v = enu.get(a, {}).get(co)
                if v and (v.get('s') or any(v.get('a', []))): e[str(i)] = v
            dados['enun'][a] = e
        areas[a] = dict(nome=NOMES[a], base=base, dia=dia, lang=any(isinstance(v[0], list) for v in por_cor.values()),
                        classe=classe, recuperado=(a in recuperadas), pct_dentro_1=info['pct_dentro_1'], corr=info.get('ajuste', {}).get('corr'), band=dados['band'].get(a))
        cores[dia].update(por_cor.keys())
    areas = dict(sorted(areas.items(), key=lambda kv: (kv[1]['dia'], kv[1]['base'])))
    cores = {str(d): sorted(s, key=lambda c: ORDEM_COR.index(c) if c in ORDEM_COR else 99) for d, s in cores.items()}
    dia1 = [a for a, v in areas.items() if v['dia'] == 1]
    ordem_moderna = set(dia1) == {'LC', 'CH'}
    pac = dict(ano=ano, areas=areas, cores=cores, langs=[LANG_NOME.get(l, 'Idioma ' + l) for l in (langs_ano or [])], langs_codigos=langs_ano or [],
               sem_habilidade=sem_hab, ordem_moderna=ordem_moderna, provas_cor=provas_cor, dados=dados, avisos=avisos,
               qualidade_enunciados=dict(pct_alternativas_completas=enr.get('pct_alternativas_completas'), qualidade_baixa=enr.get('qualidade_baixa')) if enr else None)
    out = pathlib.Path(saida); out.mkdir(parents=True, exist_ok=True)
    (out / f'pacote_{ano}.json').write_text(json.dumps(pac, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return pac


if __name__ == '__main__':
    ano = int(sys.argv[1]); saida = sys.argv[2] if len(sys.argv) > 2 else str(W / 'pacotes')
    p = empacotar(ano, saida)
    print(ano, {a: (v['dia'], v['base'], v['lang'], v['classe']) for a, v in p['areas'].items()}, 'cores', p['cores'], 'langs', p['langs'], 'ordem_moderna', p['ordem_moderna'], 'sem_hab', p['sem_habilidade'], 'avisos', p['avisos'])
