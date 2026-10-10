"""Monta o site multi-prova: ../index.html (shell + manifesto) e ../dados/enem_ANO.json (um por prova).

Uso (dentro de tools/): python -I montar_multi.py [pasta_pacotes=C:/dev/enem/_work/pacotes] [anos...]
Entradas: pacote_ANO.json (pipeline/empacotar.py), pipeline/links_provas.verificado.json, dados_enem2022.json (habilidades), red_niveis.json.
"""
import sys, json, pathlib

aqui = pathlib.Path(__file__).parent
raiz = aqui.parent
pacotes = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('C:/dev/enem/_work/pacotes')
anos = sorted({int(x) for x in sys.argv[2:]} or {int(p.stem.split('_')[1]) for p in pacotes.glob('pacote_*.json')}, reverse=True)
links = json.loads((aqui / 'pipeline' / 'links_provas.verificado.json').read_text(encoding='utf-8'))
habs = json.loads((aqui / 'dados_enem2022.json').read_text(encoding='utf-8'))['habs']
red = json.loads((aqui / 'red_niveis.json').read_text(encoding='utf-8'))

(raiz / 'dados').mkdir(exist_ok=True)
for velho in (raiz / 'dados').glob('enem_*.json'): velho.unlink()
manifesto = []
for ano in anos:
    pac = json.loads((pacotes / f'pacote_{ano}.json').read_text(encoding='utf-8'))
    (raiz / 'dados' / f'enem_{ano}.js').write_text('window.__DADOS=window.__DADOS||{};window.__DADOS[%d]=%s;' % (ano, json.dumps(pac['dados'], ensure_ascii=False, separators=(',', ':'))), encoding='utf-8')
    manifesto.append(dict(ano=ano, areas={a: dict(nome=v['nome'], base=v['base'], dia=v['dia'], lang=v['lang'], classe=v['classe'], band=v.get('band'), pct_dentro_1=v.get('pct_dentro_1'), recuperado=bool(v.get('recuperado'))) for a, v in pac['areas'].items()},
                          cores=pac['cores'], langs=pac['langs'], sem_habilidade=pac['sem_habilidade'], ordem_moderna=pac['ordem_moderna'],
                          links=links.get(str(ano), {}).get('dias', {}), avisos=pac['avisos']))
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
html = (aqui / 'template.html').read_text(encoding='utf-8')
for k, v in (('__MANIFEST__', dump(manifesto)), ('__HABS__', dump(habs)), ('__RED__', dump(red))):
    assert k in html, k
    html = html.replace(k, v)
(raiz / 'index.html').write_text(html, encoding='utf-8')
tam = sum(p.stat().st_size for p in (raiz / 'dados').glob('enem_*.js'))
print('index.html:', len(html.encode('utf-8')), 'bytes | provas:', anos, '| dados/:', tam, 'bytes')
