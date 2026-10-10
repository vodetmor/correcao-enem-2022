"""Hub destaca 'Simulado em andamento' (com 'Continuar corrigindo') quando há marcações salvas no navegador."""
import json, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/index.html'
EST = "{tab:'LC',cor:{1:null,2:null},lang:null,ans:{LC:Array(45).fill('').map((x,i)=>i<12?'A':''),CH:Array(45).fill(''),CN:Array(45).fill(''),MT:Array(45).fill('')},env:{LC:false,CH:false,CN:false,MT:false},res:{},red:[null,null,null,null,null],hist:[]}"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(URL); pg.wait_for_selector('.pcard')
    print('sem rascunho, sem destaque:', pg.locator('.retomar').count() == 0)
    pg.evaluate("() => { const e=%s; localStorage.setItem('correcao_enem_v3', JSON.stringify({v:3,view:'lobby',exam:'enem2022',estados:{enem2022:e}})); }" % EST)
    pg.reload(); pg.wait_for_selector('.pcard')
    r = pg.locator('.retomar')
    print('destaque:', r.inner_text().replace('\n', ' | '))
    print('destaque acima do backup:', pg.evaluate("!!(document.querySelector('.retomar').compareDocumentPosition(document.querySelector('.strip'))&4)"))
    print('cartão 2022 sem duplicar:', pg.locator('.pcard', has_text='ENEM 2022').locator('.andamento').count() == 0)
    pg.set_viewport_size({'width': 360, 'height': 800}); print('overflow mobile:', pg.evaluate('document.documentElement.scrollWidth>innerWidth'))
    pg.screenshot(path='C:/dev/enem/_work/hub_retomar.png', clip={'x': 0, 'y': 0, 'width': 360, 'height': 800})
    r.locator('button.pri').click(); pg.wait_for_selector('.tab', timeout=15000)
    print('abriu a prova:', pg.locator('.pcard').count() == 0 and pg.locator('.tab').count() > 0, '| marcações preservadas:', pg.evaluate("JSON.parse(localStorage.getItem('correcao_enem_v3')).estados.enem2022.ans.LC.filter(x=>x).length"))
    pg.evaluate("() => { const s=JSON.parse(localStorage.getItem('correcao_enem_v3')); s.view='lobby'; for (const id of ['enem2024','enem2023','enem2019']) s.estados[id]=%s; localStorage.setItem('correcao_enem_v3', JSON.stringify(s)); }" % EST)
    pg.reload(); pg.wait_for_selector('.pcard')
    print('4 em andamento -> no destaque:', pg.locator('.retomar .rit').count(), '| resto:', pg.locator('.retomar .mais').inner_text())
    print('erros:', erros); b.close()
