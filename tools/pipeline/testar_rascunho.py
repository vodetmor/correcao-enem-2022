"""Hub mostra 'Simulado em andamento' quando há marcações salvas no navegador (sem nenhuma área corrigida)."""
import json, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/index.html'
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(URL); pg.wait_for_selector('.pcard')
    pg.evaluate("""() => {
      const s = {v:3, view:'lobby', exam:'enem2022', estados:{enem2022:{tab:'LC',cor:{1:null,2:null},lang:null,ans:{LC:Array(45).fill('').map((x,i)=>i<12?'A':''),CH:Array(45).fill(''),CN:Array(45).fill(''),MT:Array(45).fill('')},env:{LC:false,CH:false,CN:false,MT:false},res:{},red:[null,null,null,null,null],hist:[]}}};
      localStorage.setItem('correcao_enem_v3', JSON.stringify(s)); }""")
    pg.reload(); pg.wait_for_selector('.pcard')
    cards = pg.locator('.pcard', has_text='ENEM 2022')
    print('andamento:', cards.locator('.andamento').inner_text().replace('\n', ' | '))
    print('botão:', cards.locator('button.pri').inner_text())
    print('outros cartões sem bloco:', pg.locator('.andamento').count() == 1)
    pg.set_viewport_size({'width': 360, 'height': 800}); print('overflow mobile:', pg.evaluate('document.documentElement.scrollWidth>innerWidth'))
    print('erros:', erros); b.close()
