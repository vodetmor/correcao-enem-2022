import pathlib
base = pathlib.Path('C:/dev/enem/correcao-enem/tools/pipeline')
def patch(arq, pares):
    p = base / arq; s = p.read_text(encoding='utf-8')
    for old, new in pares:
        assert old in s, f'{arq}: âncora não encontrada: {old[:90]}'
        s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8')

patch('corrigir_params.py', [
    ("def resolver(ano, area, n=6000):", "def resolver(ano, area, n=6000, incluir_aban=False):"),
    ("    N_it = len(its); aban = np.array([x['a'] is None or x['aban'] for x in its])\n    A0 = np.array([x['a'] or 0 for x in its]); B0 = np.array([x['b'] or 0 for x in its]); C0 = np.array([x['c'] or 0 for x in its])",
     "    N_it = len(its); aban = np.array([x['a'] is None or x['aban'] for x in its])\n    A0 = np.array([x['a'] or 0 for x in its]); B0 = np.array([x['b'] or 0 for x in its]); C0 = np.array([x['c'] or 0 for x in its])\n    if incluir_aban:   # itens sem parâmetros no arquivo entram com valores iniciais típicos e parâmetros livres\n        for i in range(N_it):\n            if aban[i]: A0[i], B0[i], C0[i] = 1.4, 0.5, 0.15\n        aban = np.zeros(N_it, bool)\n        print('   itens sem parâmetros incluídos:', [(i + 1, its[i]['item']) for i in range(N_it) if its[i]['a'] is None or its[i]['aban']], flush=True)"),
    ("        ab2 = np.array([x['a'] is None or x['aban'] for x in its2])", "        ab2 = np.array([x['item'] not in finais for x in its2])"),
    ("    resolver(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6000)", "    resolver(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6000, len(sys.argv) > 4 and sys.argv[4] == '1')"),
])
patch('enem_pipeline.py', [
    ("            if x['area'] == a and x['item'] in pr and not x['aban'] and x['a'] is not None: x['a'], x['b'], x['c'] = pr[x['item']]",
     "            if x['area'] == a and x['item'] in pr:\n                x['a'], x['b'], x['c'] = pr[x['item']]; x['aban'] = False; x['motivo'] = ''   # inclui itens que o arquivo marcava sem parâmetros mas entraram na nota"),
])
print('ok')
