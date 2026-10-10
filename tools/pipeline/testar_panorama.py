"""Panorama de acertos: área, resultado, histórico (com migração de histórico antigo) e dashboard do hub."""
import sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/index.html'
ok_all = True
def chk(nome, cond, extra=''):
    global ok_all; ok_all &= bool(cond); print(('OK  ' if cond else 'FALHA'), nome, extra)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1200, 'height': 900}); erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(URL); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_selector('.pcard')
    pg.locator('.pcard', has_text='ENEM 2022').locator('button.pri').click(); pg.wait_for_selector('.tab', timeout=20000)
    esperado = pg.evaluate("""() => {
      S.cor[1]=EX.cores[1][0]; S.cor[2]=EX.cores[2][0]; S.lang=0;
      const out={};
      for(const a of ['LC','CN']){
        const idx=caderno(a), v=[]; let ac=0,er=0,br=0,j=0;
        idx.forEach((k,pos)=>{ const it=DATA.items[a][k]; if(it[0]===null) return; j++;
          if(j<=28){ S.ans[a][pos]=it[4]; ac++; } else if(j<=38){ S.ans[a][pos]=it[4]==='A'?'B':'A'; er++; } else { S.ans[a][pos]=''; br++; } });
        S.env[a]=true; out[a]={ac,er,br,tot:j};
      }
      S.tab='LC'; salvar(); renderAll(); return out; }""")
    print('esperado', esperado)
    txt = pg.inner_text('#sum-LC')
    e = esperado['LC']; tm = round(100 * e['ac'] / (e['ac'] + e['er'])); tp = round(100 * e['ac'] / e['tot'])
    chk('área LC: contagens', f"{e['ac']}" in txt and 'em branco' in txt and 'erros' in txt)
    chk('área LC: taxa sobre o que marcou', f"{tm}%" in txt and 'sobre o que marcou' in txt, f'{tm}%')
    chk('área LC: taxa sobre a prova', f"{tp}%" in txt and 'sobre a prova toda' in txt, f'{tp}%')
    pg.evaluate("S.tab='RES'; renderAll()"); pg.wait_for_selector('.pantbl')
    t = pg.inner_text('.pantbl')
    tot_ac = esperado['LC']['ac'] + esperado['CN']['ac']; tot_er = esperado['LC']['er'] + esperado['CN']['er']; tot_tot = esperado['LC']['tot'] + esperado['CN']['tot']
    chk('Resultado: tabela com total das 2 áreas', f"Total (áreas corrigidas)\t{tot_ac}\t{tot_er}" in t, t.replace('\n', ' | ')[-170:])
    chk('Resultado: taxa total sobre a prova', f"{round(100*tot_ac/tot_tot)}%" in t)
    chk('Resultado: áreas não corrigidas marcadas', t.count('ainda não corrigida') == 2)
    pg.screenshot(path='C:/dev/enem/_work/panorama_res.png', full_page=True)
    pg.evaluate("document.getElementById('nomeSim').value='Teste panorama'"); pg.locator('[data-act=salvarHist]').click(); pg.wait_for_timeout(300)
    h0 = pg.evaluate("S.hist[0].pan"); chk('histórico guarda panorama', h0 and h0['ac'] == tot_ac and h0['er'] == tot_er and h0['tot'] == tot_tot, str(h0))
    dt = pg.inner_text('#dashSec'); chk('dashboard da prova mostra panorama', 'Acerto sobre o que marcou' in dt and 'Último: acertos' in dt)
    # histórico antigo (sem pan) recebe o panorama ao abrir a prova
    pg.evaluate("() => { const s=JSON.parse(localStorage.getItem('correcao_enem_v3')); delete s.estados.enem2022.hist[0].pan; s.view='lobby'; localStorage.setItem('correcao_enem_v3', JSON.stringify(s)); }")
    pg.reload(); pg.wait_for_selector('.pcard')
    chk('hub sem pan: dashboard não quebra', pg.locator('#dashSec table').count() == 1)
    pg.locator('.pcard', has_text='ENEM 2022').locator('button.pri').click(); pg.wait_for_selector('.tab', timeout=20000); pg.wait_for_timeout(300)
    h1 = pg.evaluate("S.hist[0].pan"); chk('histórico antigo migrado ao abrir a prova', h1 and h1['ac'] == tot_ac, str(h1))
    # hub: dashboard geral com colunas novas
    pg.evaluate("store.view='lobby'; renderAll()"); pg.wait_for_selector('.pcard')
    hd = pg.inner_text('#dashSec'); chk('hub: dashboard com panorama', 'Último: acertos' in hd and '% prova' in hd)
    pg.screenshot(path='C:/dev/enem/_work/panorama_hub.png', full_page=True)
    # mobile
    pg.set_viewport_size({'width': 360, 'height': 800})
    chk('mobile hub sem overflow', not pg.evaluate('document.documentElement.scrollWidth>innerWidth'))
    pg.locator('.pcard', has_text='ENEM 2022').locator('button.pri').click(); pg.wait_for_selector('.tab', timeout=20000)
    for tab in ['LC', 'RES']:
        pg.evaluate("t => { S.tab=t; renderAll(); }", tab); pg.wait_for_timeout(200)
        chk(f'mobile {tab} sem overflow', not pg.evaluate('document.documentElement.scrollWidth>innerWidth'))
    pg.screenshot(path='C:/dev/enem/_work/panorama_mobile.png', full_page=True)
    chk('sem erros de console', not erros, str(erros)); b.close()
print('TUDO OK' if ok_all else 'HÁ FALHAS')
