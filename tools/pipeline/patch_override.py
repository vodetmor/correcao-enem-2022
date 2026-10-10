import pathlib
base = pathlib.Path('C:/dev/enem/correcao-enem/tools/pipeline')


def patch(arq, pares):
    p = base / arq; s = p.read_text(encoding='utf-8')
    for old, new in pares:
        assert old in s, f'{arq}: âncora não encontrada: {old[:80]}'
        s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8')


patch('enem_pipeline.py', [
    ('def montar_cadernos(itens):', '''def aplicar_override(itens, ano, saida='C:/dev/enem/_work/saida', minimo=99.5):
    """Substitui os parâmetros de itens cujos valores publicados não reproduzem a nota oficial (ver corrigir_params.py).
    Só vale para a área cujo ajuste passou na validação (mesmo caderno com outros participantes E demais cadernos >= minimo% a menos de 1 ponto)."""
    areas = set()
    for f in pathlib.Path(saida).glob(f'params_{ano}_*.json'):
        d = json.loads(f.read_text(encoding='utf-8')); h = d.get('holdout', {}); outros = list(d.get('validacao_outros_cadernos', {}).values())
        if h.get('dentro_1', 0) < minimo or any(v.get('corrigido_dentro_1', 0) < minimo for v in outros): continue
        a, pr = d['area'], d['params']
        for x in itens:
            if x['area'] == a and x['item'] in pr and not x['aban'] and x['a'] is not None: x['a'], x['b'], x['c'] = pr[x['item']]
        areas.add(a)
    return areas


def montar_cadernos(itens):'''),
    ("    itens, hitens = carregar_itens(fonte); cad = montar_cadernos(itens)\n    h, _ = linhas(fonte, nome_res); m, il = mapa_resultados(h)\n    rel['areas_com_respostas_e_notas'] = sorted(m); rel['tem_TP_LINGUA'] = il is not None\n    if not m: rel['status'] = 'SEM_RESPOSTAS_OU_NOTAS'; return rel\n    st = {",
     "    itens, hitens = carregar_itens(fonte); rel['areas_parametros_recuperados'] = sorted(aplicar_override(itens, ano)); cad = montar_cadernos(itens)\n    h, _ = linhas(fonte, nome_res); m, il = mapa_resultados(h)\n    rel['areas_com_respostas_e_notas'] = sorted(m); rel['tem_TP_LINGUA'] = il is not None\n    if not m: rel['status'] = 'SEM_RESPOSTAS_OU_NOTAS'; return rel\n    st = {"),
])
patch('empacotar.py', [
    ("    itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens)\n    avisos = []",
     "    itens, _ = P.carregar_itens(f); recuperadas = P.aplicar_override(itens, ano); cad = P.montar_cadernos(itens)\n    avisos = []"),
    ("classe=classe, pct_dentro_1=info['pct_dentro_1'],", "classe=classe, recuperado=(a in recuperadas), pct_dentro_1=info['pct_dentro_1'],"),
])
print('ok')
