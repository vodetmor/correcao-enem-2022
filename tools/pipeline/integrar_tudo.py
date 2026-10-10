"""Integração final: empacota todos os anos com relatório v2, monta o site e grava a validação por ano/área.
Uso: python -I integrar_tudo.py [anos...]   (padrão: todos os anos que têm relatorio2_ANO.json com status OK)
Saídas: C:/dev/enem/_work/pacotes/pacote_ANO.json, ../index.html, ../dados/enem_ANO.json, tools/validacao_por_ano.json
"""
import sys, json, pathlib, subprocess
AQUI = pathlib.Path(__file__).parent
sys.path.insert(0, str(AQUI))
import empacotar as E

W = pathlib.Path('C:/dev/enem/_work')
anos = [int(x) for x in sys.argv[1:]] or sorted(int(p.stem.split('_')[1]) for p in (W / 'saida').glob('relatorio2_*.json'))
val = {}; falhas = {}
for ano in anos:
    rel = json.loads((W / 'saida' / f'relatorio2_{ano}.json').read_text(encoding='utf-8'))
    if rel.get('status') != 'OK': falhas[ano] = rel.get('status') or rel.get('erro', '')[:120]; continue
    try:
        pac = E.empacotar(ano, str(W / 'pacotes'))
    except Exception as e:
        falhas[ano] = f'empacotar: {e!r}'; continue
    val[str(ano)] = dict(participantes=rel.get('participantes_nao_brancos'),
                         areas={a: dict(classe=v['classe'], pct_dentro_1=v['pct_dentro_1'], pct_dentro_0_1=v['pct_dentro_0_1'], n=v['n_regulares'],
                                        corr=v.get('ajuste', {}).get('corr'), margem_p95=v.get('ajuste', {}).get('p95'), constantes=v['ajuste'] and [v['ajuste']['m'], v['ajuste']['s']] if v.get('ajuste') else v['constantes'])
                                for a, v in rel['areas'].items()},
                         avisos=pac['avisos'], ordem_moderna=pac['ordem_moderna'], sem_habilidade=pac['sem_habilidade'])
(AQUI.parent / 'validacao_por_ano.json').write_text(json.dumps(val, ensure_ascii=False, indent=1), encoding='utf-8')
subprocess.run([sys.executable, '-I', str(AQUI.parent / 'montar_multi.py')], check=True)
print('\nano   ' + '  '.join(f'{a:<24}' for a in ('CN', 'CH', 'LC', 'MT')))
for ano in sorted(val, reverse=True):
    print(ano, ' ', '  '.join(f'{(val[ano]["areas"].get(a) or {}).get("classe", "-"):<10} {(val[ano]["areas"].get(a) or {}).get("pct_dentro_1", 0):>6.2f}%     ' for a in ('CN', 'CH', 'LC', 'MT')))
if falhas: print('\nFALHAS:', falhas)
