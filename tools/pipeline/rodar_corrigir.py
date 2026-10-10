"""Roda corrigir_params.py para todas as áreas não exatas, em paralelo (processos independentes).
Uso: python -I rodar_corrigir.py   (lê C:/dev/enem/_work/saida/relatorio2_*.json e pega as áreas com classe != EXATO)
"""
import sys, json, glob, subprocess, pathlib, time
AQUI = pathlib.Path(__file__).parent; W = pathlib.Path('C:/dev/enem/_work')
jobs = []
for f in sorted(glob.glob(str(W / 'saida' / 'relatorio2_*.json'))):
    r = json.load(open(f, encoding='utf-8'))
    for a, v in (r.get('areas') or {}).items():
        if v['classe'] != 'EXATO' and not (W / 'saida' / f'params_{r["ano"]}_{a}.json').exists(): jobs.append((r['ano'], a))
print('áreas a corrigir:', jobs, flush=True)
procs = []
for ano, a in jobs:
    log = open(W / 'saida' / f'log_corrigir_{ano}_{a}.txt', 'w', encoding='utf-8')
    procs.append(((ano, a), subprocess.Popen([sys.executable, '-I', str(AQUI / 'corrigir_params.py'), str(ano), a, '6000'], stdout=log, stderr=subprocess.STDOUT)))
while procs:
    for k, p in list(procs):
        if p.poll() is not None: print(k, 'terminou, código', p.returncode, flush=True); procs.remove((k, p))
    time.sleep(10)
print('FIM', flush=True)
