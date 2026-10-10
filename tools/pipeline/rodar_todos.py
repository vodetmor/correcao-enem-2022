"""Executor paralelo: processa cada ano assim que o zip termina de baixar.
Uso: python -I rodar_todos.py <pasta_zips> <log_do_download> <pasta_saida> [anos...] [--par N]
Cada ano vira saida/relatorio_<ano>.json (status OK | SEM_RESPOSTAS_OU_NOTAS | ERRO). Não gasta tokens.
"""
import sys, re, json, time, pathlib, traceback, multiprocessing as mp

AQUI = pathlib.Path(__file__).parent
sys.path.insert(0, str(AQUI))


def trabalhar(args):
    zipf, ano, saida, v2 = args
    import enem_pipeline as P
    t0 = time.time()
    try:
        rel = (P.processar_ano2 if v2 else P.processar_ano)(zipf, ano, saida)
    except Exception:
        rel = dict(ano=ano, status='ERRO', erro=traceback.format_exc()[-1800:])
    rel['segundos'] = round(time.time() - t0)
    pathlib.Path(saida, f'relatorio2_{ano}.json' if v2 else f'relatorio_{ano}.json').write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding='utf-8')
    return ano, rel.get('status'), ({a: v.get('classe') for a, v in rel.get('areas', {}).items()} if v2 else rel.get('classificacao')), rel['segundos']


def prontos(log, anos):
    try: txt = pathlib.Path(log).read_bytes().decode('utf-8', 'replace')
    except OSError: return set()
    ok = set(int(a) for a in re.findall(r'(\d{4}): (?:OK|já completo)', txt))
    return ok & set(anos)


if __name__ == '__main__':
    a = sys.argv[1:]; par = 5; v2 = '--v2' in a
    if v2: a.remove('--v2')
    if '--par' in a: i = a.index('--par'); par = int(a[i + 1]); del a[i:i + 2]
    zips, log, saida = pathlib.Path(a[0]), a[1], pathlib.Path(a[2]); saida.mkdir(parents=True, exist_ok=True)
    anos = [int(x) for x in a[3:]] or list(range(2009, 2026))
    pend = set(anos); feitos = {}; ativos = {}
    pool = mp.Pool(par)
    print(time.strftime('%H:%M:%S'), f'executor: {len(anos)} anos, {par} em paralelo', flush=True)
    while pend or ativos:
        for ano in sorted(prontos(log, pend)):
            pend.discard(ano); ativos[ano] = pool.apply_async(trabalhar, ((str(zips / f'microdados_enem_{ano}.zip'), ano, str(saida), v2),))
            print(time.strftime('%H:%M:%S'), f'{ano}: iniciado', flush=True)
        for ano in list(ativos):
            if ativos[ano].ready():
                r = ativos.pop(ano).get(); feitos[ano] = r
                print(time.strftime('%H:%M:%S'), f'{ano}: {r[1]} {r[2]} ({r[3]}s)', flush=True)
        time.sleep(15)
    pool.close(); pool.join()
    (saida / 'resumo.json').write_text(json.dumps({str(k): v for k, v in sorted(feitos.items())}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(time.strftime('%H:%M:%S'), 'FIM', flush=True)
