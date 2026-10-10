"""Teste de fluxo de usuário no site multi-prova (servidor local): corrigir, redação, histórico, dashboard, backup, mobile.
Uso: python -I testar_fluxo.py [porta=8765]
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import enem_pipeline as P
from playwright.sync_api import sync_playwright

porta = sys.argv[1] if len(sys.argv) > 1 else '8765'; URL = f'http://127.0.0.1:{porta}/'
W = pathlib.Path('C:/dev/enem/_work'); ANO = 2022
pac = json.loads((W / 'pacotes' / f'pacote_{ANO}.json').read_text(encoding='utf-8'))
am = json.loads((W / 'saida' / f'amostra_teste_{ANO}.json').read_text(encoding='utf-8'))
A = lambda s: s.encode('ascii', 'replace').decode()
fmt = lambda x: f'{x:.1f}'.replace('.', ',')
def pega(a):
    for x in am[a]:
        cor = pac['provas_cor'][a].get(x['prova'])
        if cor and not P.em_branco(x['resp']):
            r = P.normalizar_resp(a, x['resp'], 45, x['lingua'])[:45]
            return cor, (pac['langs_codigos'].index(x['lingua']) if x['lingua'] in pac['langs_codigos'] else 0), ''.join(c if c in 'ABCDE' else '-' for c in r), x['nota']
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True); pg = ctx.new_page(); erros = []
    pg.on('pageerror', lambda e: erros.append(str(e))); pg.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(500)
    print('1) hub:', pg.locator('.pcard').count(), 'provas | resumo de validação:', 'Como saber se confio' in pg.inner_text('#main'))
    pg.click(f'.pcard:has-text("ENEM {ANO}") [data-act=abrirExam]'); pg.wait_for_selector('#tabs .tab')
    res = {}
    for a in ('LC', 'CH', 'CN', 'MT'):
        cor, lang, resp, nota_of = pega(a); d = pac['areas'][a]['dia']
        pg.click(f'.tab[data-t={a}]'); pg.click(f'[data-act=cor][data-d="{d}"][data-c={cor}]')
        if d == 1: pg.click(f'[data-act=lang][data-l="{lang}"]')
        pg.locator(f'#area-{a} details.paste').first.locator('summary').click(); pg.fill(f'#paste-{a}', resp); pg.click(f'[data-act=paste][data-a={a}]')
        pg.click('[data-act=ask]'); pg.click('[data-act=go]'); pg.wait_for_timeout(150)
        modal = pg.inner_text('#modalCard .bignota'); pg.click('#modalCard [data-act=fechar]')
        res[a] = (modal, fmt(nota_of))
    print('2) notas do site x oficial (por área):', {a: f'{s} x {o}' for a, (s, o) in res.items()}, '| todas iguais:', all(s == o for s, o in res.values()))
    pg.click('.tab[data-t=RED]')
    for i, v in enumerate((160, 160, 120, 80, 160)): pg.click(f'.lv[data-i="{i}"][data-v="{v}"]')
    print('3) redação soma:', pg.inner_text('#redSum'), '(680)')
    pg.click('.tab[data-t=RES]'); fin = pg.inner_text('.final').replace('\n', ' ')
    pg.fill('#nomeSim', 'Teste fluxo'); pg.click('[data-act=salvarHist]'); pg.wait_for_timeout(150)
    print('4) média final:', A(fin[:70]), '| histórico (RES):', pg.locator('#dashSec tbody tr').count(), 'linha')
    pg.click('#dock [data-act=hub]'); pg.wait_for_timeout(300)
    print('5) hub com dashboard:', pg.locator('#dashSec tbody tr').count(), 'linha(s) | seletor de escopo:', pg.locator('#escopo').count(), '| gráfico:', pg.locator('.chartbox svg path').count(), 'série(s)')
    pg.select_option('#escopo', f'enem{ANO}'); print('   escopo por prova OK, linhas:', pg.locator('#dashSec tbody tr').count())
    with pg.expect_download() as dl: pg.click('.strip [data-act=bkDown]')
    path = dl.value.path(); bk = json.load(open(path, encoding='utf-8'))
    print('6) backup baixado: versão', bk['versao'], '| provas no backup:', len(bk['store']['estados']), '| histórico na prova:', len(bk['store']['estados'][f'enem{ANO}']['hist']))
    pg.click(f'.pcard:has-text("ENEM {ANO}") [data-act=abrirExam]'); pg.wait_for_selector('#tabs .tab'); pg.click('.tab[data-t=RES]'); pg.click('[data-act=limparTudo]'); pg.wait_for_timeout(300)
    pg.click('#home'); print('   após apagar tudo, histórico:', pg.locator('#dashSec tbody tr').count(), end=' ')
    pg.set_input_files('#bkFile', path); pg.wait_for_timeout(400); pg.click('#home')
    print('| após carregar o backup:', pg.locator('#dashSec tbody tr').count())
    m = ctx.new_page(); m.set_viewport_size({'width': 390, 'height': 844}); m.goto(URL); m.wait_for_timeout(500)
    print('7) mobile: overflow do hub =', m.evaluate('document.documentElement.scrollWidth>innerWidth'))
    m.click(f'.pcard:has-text("ENEM {ANO}") [data-act=abrirExam]'); m.wait_for_selector('#tabs .tab')
    for t in ('LC', 'CH', 'CN', 'MT', 'RED', 'RES'):
        m.click(f'.tab[data-t={t}]'); m.wait_for_timeout(120)
        print(f'   {t}: overflow={m.evaluate("document.documentElement.scrollWidth>innerWidth")}', end=' ')
    print('\nerros de console:', erros); b.close()
