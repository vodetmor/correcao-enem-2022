import pathlib
p = pathlib.Path('C:/dev/enem/correcao-enem/tools/template.html'); s = p.read_text(encoding='utf-8')
def rep(old, new, cnt=1):
    global s
    assert s.count(old) >= 1, 'âncora não encontrada: ' + old[:90]
    s = s.replace(old, new, cnt)

# ---------- CSS ----------
rep("@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}",
"""@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}
.stats.pan{grid-template-columns:repeat(auto-fit,minmax(138px,1fr))}
.stk{display:flex;height:10px;border-radius:99px;overflow:hidden;background:var(--line);gap:2px;min-width:90px}
.stk i{display:block;height:100%}
.stk i.a{background:var(--ok)}.stk i.e{background:var(--bad)}.stk i.b{background:var(--bubble)}
.pantbl td,.pantbl th{white-space:nowrap}
.pantbl td.bar{min-width:110px;white-space:normal}
.paninfo{margin:10px 0 0}""")

# ---------- res com erros e brancos ----------
rep("e.res[a]={nota:(typeof v.nota===\"number\"&&v.nota>=0&&v.nota<=1000)?v.nota:null,ac:Math.max(0,Math.min(99,Number(v.ac)||0)),tot:Math.max(0,Math.min(99,Number(v.tot)||0)),",
    "e.res[a]={nota:(typeof v.nota===\"number\"&&v.nota>=0&&v.nota<=1000)?v.nota:null,ac:Math.max(0,Math.min(99,Number(v.ac)||0)),er:Math.max(0,Math.min(99,Number(v.er)||0)),br:Math.max(0,Math.min(99,Number(v.br)||0)),tot:Math.max(0,Math.min(99,Number(v.tot)||0)),")
rep("const v={nota:r.nota,ac:r.acertos,tot:r.validas.length,", "const v={nota:r.nota,ac:r.acertos,er:r.erros,br:r.brancos,tot:r.validas.length,")

# ---------- histórico guarda o panorama ----------
rep("    return {id:Number(h.id)||Date.now(),t:Number(h.t)||Date.now(),nn:Number(h.nn)||null,nome:String(h.nome||\"Simulado\").slice(0,60),cor:x.cor,lang:x.lang,ans:x.ans,env:x.env,red:x.red,notas};",
    "    const pn=h.pan, pan=(pn&&typeof pn==='object'&&[pn.ac,pn.er,pn.br,pn.tot].every(v=>Number.isFinite(v)&&v>=0&&v<=400))?{ac:pn.ac,er:pn.er,br:pn.br,tot:pn.tot,n:Math.max(1,Math.min(4,Number(pn.n)||1))}:null;\n    return {id:Number(h.id)||Date.now(),t:Number(h.t)||Date.now(),nn:Number(h.nn)||null,nome:String(h.nome||\"Simulado\").slice(0,60),cor:x.cor,lang:x.lang,ans:x.ans,env:x.env,red:x.red,notas,pan};")
rep("  S.hist.push({id:Date.now(),t:Date.now(),nn:n._n,nome:nome.slice(0,60),...copia,notas});",
    "  const pn=panDe(S); S.hist.push({id:Date.now(),t:Date.now(),nn:n._n,nome:nome.slice(0,60),...copia,notas,pan:pn.n?{ac:pn.ac,er:pn.er,br:pn.br,tot:pn.tot,n:pn.n}:null});")

# ---------- funções de panorama ----------
rep("function redSoma(st=S){", """/* panorama de acertos (além da nota TRI): contagens e taxas das áreas corrigidas.
   taxa sobre o que marcou = acertos ÷ (acertos + erros); taxa sobre a prova = acertos ÷ questões válidas (anuladas ficam de fora) */
function taxasDe(ac,er,tot){ const m=ac+er; return {marc:m?100*ac/m:null,prova:tot?100*ac/tot:null}; }
const pct0=v=>v===null||v===undefined?"–":Math.round(v)+"%";
function panDe(st=S){
  const por={}; let ac=0,er=0,br=0,tot=0,n=0;
  for(const a in AREAS){ const r=st===S?analisarC(a):analisar(a,st); if(!r||!r.pronto) continue;
    por[a]={ac:r.acertos,er:r.erros,br:r.brancos,tot:r.validas.length}; ac+=r.acertos; er+=r.erros; br+=r.brancos; tot+=r.validas.length; n++; }
  return {por,ac,er,br,tot,n,...taxasDe(ac,er,tot)};
}
function panTiles(ac,er,br,tot,rotulo){
  const t=taxasDe(ac,er,tot);
  return `<div class="stats pan"><div class="stat"><b>${ac}</b><span>acertos${rotulo?" "+rotulo:" de "+tot}</span></div><div class="stat"><b>${er}</b><span>erros</span></div><div class="stat"><b>${br}</b><span>em branco</span></div>
    <div class="stat"><b>${pct0(t.marc)}</b><span>de acerto sobre o que marcou (${ac} de ${ac+er})</span></div><div class="stat"><b>${pct0(t.prova)}</b><span>de acerto sobre a prova toda (${ac} de ${tot})</span></div></div>`;
}
function stkBar(ac,er,br,tot){
  if(!tot) return "";
  const w=v=>(100*v/tot).toFixed(1);
  return `<div class="stk" role="img" aria-label="${ac} acertos, ${er} erros, ${br} em branco"><i class="a" style="width:${w(ac)}%"></i><i class="e" style="width:${w(er)}%"></i><i class="b" style="width:${w(br)}%"></i></div>`;
}
function panoramaHtml(){
  const pn=panDe(S);
  if(!pn.n) return `<div class="empty">Corrija ao menos uma área para ver o panorama de acertos, erros e questões em branco.</div>`;
  let h=panTiles(pn.ac,pn.er,pn.br,pn.tot,`de ${pn.tot}`);
  h+=`<div class="tblw" style="margin-top:12px"><table class="pantbl" style="min-width:640px"><thead><tr><th>Área</th><th>Acertos</th><th>Erros</th><th>Em branco</th><th>% sobre o que marcou</th><th>% sobre a prova</th><th>Visão geral</th></tr></thead><tbody>`;
  for(const a in AREAS){ const v=pn.por[a], nome=AREAS[a].nome;
    if(!v){ h+=`<tr><td>${nome}</td><td colspan="6" class="hint">ainda não corrigida</td></tr>`; continue; }
    const t=taxasDe(v.ac,v.er,v.tot);
    h+=`<tr><td><b>${nome}</b></td><td>${v.ac}</td><td>${v.er}</td><td>${v.br}</td><td>${pct0(t.marc)}</td><td>${pct0(t.prova)}</td><td class="bar">${stkBar(v.ac,v.er,v.br,v.tot)}</td></tr>`; }
  h+=`<tr><td><b>Total${pn.n<Object.keys(AREAS).length?" (áreas corrigidas)":""}</b></td><td><b>${pn.ac}</b></td><td><b>${pn.er}</b></td><td><b>${pn.br}</b></td><td><b>${pct0(pn.marc)}</b></td><td><b>${pct0(pn.prova)}</b></td><td class="bar">${stkBar(pn.ac,pn.er,pn.br,pn.tot)}</td></tr></tbody></table></div>
    <p class="hint paninfo"><b>% sobre o que marcou</b> = acertos ÷ (acertos + erros): mostra o quanto você acerta quando decide responder. <b>% sobre a prova</b> = acertos ÷ questões válidas (as anuladas ficam fora): é o seu aproveitamento real, contando os brancos como perdidos. Se a primeira é bem maior que a segunda, deixar em branco está custando pontos; se as duas são baixas, o ponto é conteúdo. Verde = acertos, vermelho = erros, cinza = em branco.</p>`;
  return h;
}
function redSoma(st=S){""")

# ---------- resumo da área ----------
old_start = s.index("  let h=`<div class=\"stats\">\n    ${r.nota!==null?`<div class=\"stat main\">")
old_end = s.index("  if(r.todosBrancos) h+=`<div class=\"note\" style=\"margin-top:10px\">Nenhuma questão respondida")
s = s[:old_start] + """  const tx=taxasDe(r.acertos,r.erros,r.validas.length);
  let h=`<div class="stats pan">
    ${r.nota!==null?`<div class="stat main"><b>${fmt(r.nota)}</b><span>${r.band?"estimativa ±"+(r.band<1?fmt(r.band):Math.round(r.band)):"nota TRI estimada"}</span></div>`:`<div class="stat main"><b>${r.acertos}<span style="font-size:.9rem"> / ${r.validas.length}</span></b><span>acertos${r.semTRI?" · sem TRI nesta área":""}</span></div>`}
    <div class="stat"><b>${r.acertos}</b><span>acertos de ${r.validas.length}</span></div>
    <div class="stat"><b>${r.erros}</b><span>erros</span></div>
    <div class="stat"><b>${r.brancos}</b><span>em branco${r.semMarca?` (${r.semMarca} sem marcação)`:""}</span></div>
    <div class="stat"><b>${pct0(tx.marc)}</b><span>de acerto sobre o que marcou (${r.acertos} de ${r.acertos+r.erros})</span></div>
    <div class="stat"><b>${pct0(tx.prova)}</b><span>de acerto sobre a prova toda (${r.acertos} de ${r.validas.length})</span></div></div>`;
""" + s[old_end:]
# pct usado antes? remove variável não usada
rep("const nFora=r.itens.filter(i=>i[0]===null).length, pct=Math.round(100*r.acertos/r.validas.length);", "const nFora=r.itens.filter(i=>i[0]===null).length;")

# ---------- modal ao corrigir ----------
rep("""<div class="stats" style="margin-top:12px"><div class="stat"><b>${r.acertos}</b><span>acertos de ${r.validas.length}</span></div><div class="stat"><b>${r.erros}</b><span>erros</span></div><div class="stat"><b>${r.brancos}</b><span>em branco</span></div><div class="stat"><b>${Math.round(100*r.acertos/r.validas.length)}%</b><span>aproveitamento</span></div></div>""",
    """<div style="margin-top:12px">${panTiles(r.acertos,r.erros,r.brancos,r.validas.length)}</div>""")

# ---------- aba Resultado ----------
rep("""${resHtmlBoletim()}</section>
    <section class="panel"><h2>Guardar no histórico</h2>""", """${resHtmlBoletim()}</section>
    <section class="panel"><h2>Panorama de acertos</h2><p class="hint" style="margin:4px 0 0">Além da nota TRI: quantas questões você acertou, errou e deixou em branco, e as taxas de acerto.</p><div style="margin-top:12px">${panoramaHtml()}</div></section>
    <section class="panel"><h2>Guardar no histórico</h2>""")

# ---------- dashboard ----------
rep("""  h+=`<div class="sers" role="group" aria-label="Séries do gráfico">`""", """  const comPan=hist.filter(x=>x.pan&&x.pan.tot), lp=comPan.length?comPan[comPan.length-1].pan:null;
  if(lp){
    const tl=taxasDe(lp.ac,lp.er,lp.tot), melhor=Math.max(...comPan.map(x=>taxasDe(x.pan.ac,x.pan.er,x.pan.tot).prova));
    h+=`<div class="kpis" style="margin-top:10px"><div class="tile"><span>Último: acertos</span><b>${lp.ac}</b><span>de ${lp.tot} questões</span></div>
      <div class="tile"><span>Último: erros</span><b>${lp.er}</b></div><div class="tile"><span>Último: em branco</span><b>${lp.br}</b></div>
      <div class="tile ok"><span>Acerto sobre o que marcou</span><b>${pct0(tl.marc)}</b></div>
      <div class="tile ok"><span>Acerto sobre a prova toda</span><b>${pct0(tl.prova)}</b><span>melhor: ${pct0(melhor)}</span></div></div>`;
  }
  h+=`<div class="sers" role="group" aria-label="Séries do gráfico">`""")
rep("""<table style="min-width:560px"><thead><tr><th>Simulado</th><th>Data</th><th>LC</th><th>CH</th><th>CN</th><th>MT</th><th>RED</th><th>Média</th><th>Δ média</th><th></th></tr></thead>""",
    """<table style="min-width:900px"><thead><tr><th>Simulado</th><th>Data</th><th>LC</th><th>CH</th><th>CN</th><th>MT</th><th>RED</th><th>Média</th><th>Δ média</th><th>Acertos</th><th>Erros</th><th>Branco</th><th>% marcou</th><th>% prova</th><th></th></tr></thead>""")
rep("""<td>${dl===null?"–":`<span class="delta ${dl>=0?"up":"dn"}">${dl>=0?"▲ +":"▼ "}${fmt(dl)}</span>`}</td><td><button""",
    """<td>${dl===null?"–":`<span class="delta ${dl>=0?"up":"dn"}">${dl>=0?"▲ +":"▼ "}${fmt(dl)}</span>`}</td>${pn_(x)}<td><button""")
rep("function dashHtml(esc,comEscopo){", """function pn_(x){
  const p=x.pan; if(!p||!p.tot) return `<td>–</td><td>–</td><td>–</td><td>–</td><td>–</td>`;
  const t=taxasDe(p.ac,p.er,p.tot); return `<td>${p.ac}</td><td>${p.er}</td><td>${p.br}</td><td>${pct0(t.marc)}</td><td>${pct0(t.prova)}</td>`;
}
function dashHtml(esc,comEscopo){""")
rep("""* Simulado parcial: a média usa só as notas que existiam (menos de 5).""", """* Simulado parcial: a média usa só as notas que existiam (menos de 5). Acertos, erros e brancos somam só as áreas corrigidas.""")

# ---------- completa histórico antigo quando a prova é aberta ----------
rep("return carregarDados(id).then(()=>{ setExam(id); store.view=\"exam\"; salvar(); renderAll();",
    "return carregarDados(id).then(()=>{ setExam(id); completarPan(); store.view=\"exam\"; salvar(); renderAll();")
rep("function abrirExame(id){", """/* simulados salvos antes do panorama: recalcula acertos/erros/brancos pelas respostas guardadas */
function completarPan(){
  for(const h of S.hist){ if(h.pan) continue;
    try{ const pn=panDe(h); if(pn.n) h.pan={ac:pn.ac,er:pn.er,br:pn.br,tot:pn.tot,n:pn.n}; }catch(e){} }
}
function abrirExame(id){""")
p.write_text(s, encoding='utf-8')
print('ok')
