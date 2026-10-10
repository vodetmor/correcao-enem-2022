"""Teste de ponta a ponta de um ano no site (servidor local): nota do site x nota oficial de participantes reais + smoke de interface.
Uso: python -I testar_ano.py <ano> [porta=8765] [n_por_area=150]
Requer: servidor estático servindo C:/dev/enem/correcao-enem, pacote_ANO.json e amostra_teste_ANO.json.
"""
import sys, json, pathlib, statistics
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import enem_pipeline as P
from playwright.sync_api import sync_playwright

ano = int(sys.argv[1]); porta = sys.argv[2] if len(sys.argv) > 2 else '8765'; N = int(sys.argv[3]) if len(sys.argv) > 3 else 150
W = pathlib.Path('C:/dev/enem/_work')
pac = json.loads((W / 'pacotes' / f'pacote_{ano}.json').read_text(encoding='utf-8'))
cands = [W / 'saida' / f'amostra_teste_{ano}.json', W / 'smoke' / f'amostra_teste_{ano}.json']
amostra = json.loads(next(c for c in cands if c.exists()).read_text(encoding='utf-8'))
cod = pac['langs_codigos']

casos = {}
for a, v in pac['areas'].items():
    out = []
    for x in amostra.get(a, []):
        cor = pac['provas_cor'].get(a, {}).get(x['prova'])
        if not cor or P.em_branco(x['resp']): continue
        r = P.normalizar_resp(a, x['resp'], 45, x['lingua'])
        r = r[:45].ljust(45, '.')
        lang = cod.index(x['lingua']) if x['lingua'] in cod else (0 if cod else None)
        out.append(dict(cor=cor, lang=lang, ans=[c if c in 'ABCDE' else '-' for c in r], nota=x['nota']))
        if len(out) >= N: break
    casos[a] = out

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 900}); erros = []
    pg.on('pageerror', lambda e: erros.append(str(e))); pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.goto(f'http://127.0.0.1:{porta}/'); pg.wait_for_timeout(300)
    lobby_cards = pg.locator('.pcard').count()
    card = pg.locator(f'.pcard:has-text("ENEM {ano}")')
    links = card.locator('details.fazer a').count()
    selo = card.locator('.selo').first.inner_text()
    pg.evaluate(f'abrirExame("enem{ano}")'); pg.wait_for_selector('#tabs .tab', timeout=20000)
    abas = pg.locator('#tabs .tab').count(); dias = [t.replace('\n', ' ') for t in pg.locator('.seg button').all_inner_texts()]
    ordem_aviso = 'Atenção à ordem desta prova' in pg.inner_text('#main')
    res = pg.evaluate('''(casos)=>{
      const out={};
      for(const a in casos){
        const d=AREAS[a].dia; out[a]=casos[a].map(c=>{
          S.cor[d]=c.cor; if(c.lang!==null) S.lang=c.lang; S.ans[a]=c.ans.slice(); S.env[a]=true;
          const r=analisar(a); return r? [r.nota, r.acertos, r.semTRI?1:0] : null; });
      } return out; }''', casos)
    print(f'ANO {ano} | lobby: {lobby_cards} cartões, selo "{selo}", {links} links de prova | abas={abas} | dias={dias} | aviso de ordem={ordem_aviso}')
    for a, v in pac['areas'].items():
        L = [(r[0], c['nota']) for r, c in zip(res[a], casos[a]) if r]
        com = [(s, o) for s, o in L if s is not None]
        if not com:
            print(f'  {a} [{v["classe"]}] n={len(L)}: sem TRI no site (esperado para NAO_VALIDO) | acertos de exemplo={res[a][0][1] if res[a] else "-"}'); continue
        e = [abs(s - o) for s, o in com]
        print(f'  {a} [{v["classe"]}] n={len(com)} | MAE={statistics.mean(e):.3f} | dentro de 1 pt={sum(x<1 for x in e)/len(e)*100:.1f}% | p95={sorted(e)[int(len(e)*.95)-1]:.1f} | máx={max(e):.1f}' + (f' | margem anunciada ±{v["band"]}' if v.get('band') else ''))
    print('  erros de console:', erros)
    b.close()
