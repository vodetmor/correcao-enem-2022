"""Transforma tools/template.html (single-exam) em template multi-prova (manifesto + dados por ano sob demanda)."""
import re, pathlib
p = pathlib.Path('C:/dev/enem/correcao-enem/tools/template.html')
s = p.read_text(encoding='utf-8')


def rep(old, new, cnt=1):
    global s
    assert s.count(old) >= 1, 'âncora não encontrada: ' + old[:90]
    s = s.replace(old, new, cnt)


# ---------- 1) manifesto e dados globais ----------
a = s.index('const EXAMS = {'); b = s.index('const COR_HEX')
s = s[:a] + '''const MANIFEST = __MANIFEST__;
const HABS = __HABS__;
const RED = __RED__;
const LINK_INEP = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos";
const EXAMS = {};
for(const m of MANIFEST){
  EXAMS["enem"+m.ano] = {id:"enem"+m.ano, ano:m.ano, nome:"ENEM "+m.ano, sigla:"ENEM "+m.ano, areas:m.areas,
    cores:{1:(m.cores&&m.cores["1"])||[],2:(m.cores&&m.cores["2"])||[]}, langs:m.langs||[], info:m, dados:null};
}
''' + s[b:]
rep('let store = {v:3, view:"lobby", exam:Object.keys(EXAMS)[0], estados:{}};', 'let store = {v:3, view:"lobby", exam:Object.keys(EXAMS)[0], estados:{}};\nlet DASH_ESC = "all";')
rep('const fmt = (x,d=1)=>x.toFixed(d).replace(".",",");', 'const fmt = (x,d=1)=>(x===null||x===undefined||Number.isNaN(x))?"–":x.toFixed(d).replace(".",",");')
rep('function nota(a,th){ const k=DATA.k[a]; return k[0]+k[1]*th; }', 'function nota(a,th){ const k=DATA.k[a]; return k[0]+k[1]*th; }\nfunction fnota(r){ return r.semTRI||r.nota===null?`${r.acertos}/${r.validas.length}`:fmt(r.nota); }')

# ---------- 2) analisar: sem TRI, estimado, cartão em branco ----------
rep('''  r.theta = r.todosBrancos ? null : eap(par,oks);
  r.nota = r.todosBrancos ? 0 : nota(a,r.theta);
  r.delta = {};
  if(!r.todosBrancos){''', '''  r.semTRI = !DATA.k[a]; r.band = (DATA.band&&DATA.band[a])||null;
  const calc = !r.todosBrancos && !r.semTRI;
  r.theta = calc ? eap(par,oks) : null;
  r.nota = calc ? nota(a,r.theta) : null;
  r.delta = {};
  if(calc){''')

# ---------- 3) abas, dock, pílula, resumo, modal ----------
rep('''for(const a in AREAS){ const r=analisarC(a), ok=r&&r.pronto; h+=`<button type="button" role="tab" class="tab ${ok?"ok":""}"''', '''for(const a in AREAS){ const r=analisarC(a), ok=r&&r.pronto&&r.nota!==null; h+=`<button type="button" role="tab" class="tab ${ok?"ok":""}"''')
rep('''<b>${ok?fmt(r.nota):"–"}</b></button>`; }
  h+=`<button type="button" role="tab" class="tab ${g.rs!==null?"ok":""}"''', '''<b>${ok?fmt(r.nota):(r&&r.pronto?"s/TRI":"–")}</b></button>`; }
  h+=`<button type="button" role="tab" class="tab ${g.rs!==null?"ok":""}"''')
rep('''el.innerHTML=`<div class="dock-in"><div class="info"><span class="nota">${fmt(r.nota)}</span> <span class="hint">${r.acertos}/${r.validas.length} acertos · ${AREAS[a].nome}</span></div>''',
    '''el.innerHTML=`<div class="dock-in"><div class="info"><span class="nota">${r.nota!==null?fmt(r.nota)+(r.band?`<small style="font-size:.7rem;font-weight:600"> ±${Math.round(r.band)}</small>`:""):r.acertos+"/"+r.validas.length}</span> <span class="hint">${r.nota!==null?r.acertos+"/"+r.validas.length+" acertos":"acertos, sem TRI neste ano"} · ${AREAS[a].nome}</span></div>''')
rep('''${r.pronto?`<div class="nota-pill"><b>${fmt(r.nota)}</b><small>NOTA TRI ESTIMADA</small></div>`:""}</div>''',
    '''${r.pronto?pillHtml(r):""}</div>''')
rep('function renderAreaPane(a){', '''function pillHtml(r){
  if(r.nota===null) return r.todosBrancos?`<div class="nota-pill"><b>–</b><small>SEM RESPOSTAS</small></div>`:`<div class="nota-pill" style="background:var(--soft);color:var(--ink)"><b>${r.acertos}/${r.validas.length}</b><small>ACERTOS · SEM TRI</small></div>`;
  return `<div class="nota-pill"><b>${fmt(r.nota)}</b><small>${r.band?"ESTIMATIVA ±"+Math.round(r.band):"NOTA TRI ESTIMADA"}</small></div>`;
}
function avisoArea(a){
  const A=AREAS[a];
  if(A.classe==="ESTIMADO") return `<div class="note" style="margin-bottom:12px"><b>Estimativa com margem.</b> Nesta prova a nota oficial de ${A.nome} não é reproduzida exatamente pelos dados públicos do INEP. O erro típico fica abaixo de ±${Math.round(A.band||50)} pontos em 95% dos casos testados: trate o número como aproximação, não como a nota oficial.</div>`;
  if(A.classe==="NAO_VALIDO") return `<div class="note" style="margin-bottom:12px"><b>Sem nota TRI nesta área.</b> Para ${A.nome} desta prova, a nota oficial não pôde ser reproduzida a partir dos dados públicos. Você ainda pode marcar o cartão e ver acertos, erros, gabarito e enunciados, mas não calculamos a TRI.</div>`;
  return "";
}
function avisoOrdem(){
  if(EX.info.ordem_moderna) return "";
  const nomes={LC:"Linguagens",CH:"Humanas",CN:"Natureza",MT:"Matemática"};
  const dia=d=>Object.keys(AREAS).filter(x=>AREAS[x].dia===d).map(x=>nomes[x]).join(" + ");
  return `<div class="note info" style="margin-bottom:12px">Atenção à ordem desta prova: o <b>dia 1</b> foi ${dia(1)} e o <b>dia 2</b> foi ${dia(2)}. Nas edições mais recentes (2017 em diante) a ordem é outra (dia 1: Linguagens + Humanas).</div>`;
}
function renderAreaPane(a){''')
rep('  let h=diaSeg(d)+selRow(d);\n  if(!diaLiberado(d)){', '  let h=diaSeg(d)+avisoOrdem()+avisoArea(a)+selRow(d);\n  if(!diaLiberado(d)){')
rep('''<div class="stat main"><b>${fmt(r.nota)}</b><span>nota TRI estimada</span></div>
    <div class="stat"><b>${r.acertos}<span style="font-size:.9rem"> / ${r.validas.length}</span></b><span>acertos · ${pct}%</span></div>''',
    '''${r.nota!==null?`<div class="stat main"><b>${fmt(r.nota)}</b><span>${r.band?"estimativa ±"+Math.round(r.band):"nota TRI estimada"}</span></div>`:`<div class="stat main"><b>${r.acertos}<span style="font-size:.9rem"> / ${r.validas.length}</span></b><span>acertos${r.semTRI?" · sem TRI nesta área":""}</span></div>`}
    <div class="stat"><b>${pct}%</b><span>aproveitamento · ${r.acertos} acertos</span></div>''')
rep('''if(r.todosBrancos) h+=`<div class="note" style="margin-top:10px">Nenhuma questão respondida: o INEP atribui nota 0 a cartão totalmente em branco.</div>`;''',
    '''if(r.todosBrancos) h+=`<div class="note" style="margin-top:10px">Nenhuma questão respondida: não calculo nota para cartão totalmente em branco (o tratamento desse caso varia de um ano para outro no INEP).</div>`;''')
rep('''<div class="bignota">${fmt(r.nota)}</div><p class="hint" style="margin-top:2px">nota TRI estimada</p>''',
    '''<div class="bignota">${r.nota!==null?fmt(r.nota):r.acertos+"/"+r.validas.length}</div><p class="hint" style="margin-top:2px">${r.nota!==null?(r.band?"estimativa, margem ±"+Math.round(r.band)+" pontos":"nota TRI estimada"):(r.todosBrancos?"nenhuma resposta marcada":"acertos (sem TRI nesta área)")}</p>''')

# ---------- 4) detalhes: habilidades globais, sem raio-X sem habilidade, cálculo ----------
rep('const cor=S.cor[AREAS[a].dia], base=AREAS[a].base, hd=DATA.habs[a], kk=DATA.k[a];', 'const cor=S.cor[AREAS[a].dia], base=AREAS[a].base, hd=HABS[a], kk=DATA.k[a], temHab=!EX.info.sem_habilidade;')
rep("r.validas.forEach(j=>{ const k=r.itens[j][3]; (hab[k]=hab[k]||{t:0,ok:0,q:[]});", "r.validas.forEach(j=>{ const k=r.itens[j][3]; if(!k||!hd.h[k]) return; (hab[k]=hab[k]||{t:0,ok:0,q:[]});")
rep('  let h=`<details class="acc" data-k="rx"><summary>Raio-X: onde melhorar', '  let h=!temHab||!lista.length?"":`<details class="acc" data-k="rx"><summary>Raio-X: onde melhorar')
rep('''h+=`<details class="acc" data-k="cl"><summary>Como esta nota foi calculada</summary><div class="acc-b"><p class="hint" style="margin:0">${r.todosBrancos?"Cartão todo em branco: nota 0, como no INEP.":`Proficiência estimada (EAP): <code>θ = ${fmt(r.theta,4)}</code> com ${r.validas.length} questões.<br>Conversão desta área: <code>nota = ${fmt(kk[0],3)} + ${fmt(kk[1],3)} × θ = ${fmt(r.nota,2)}</code>.<br>Nos testes com as notas oficiais a diferença foi de no máximo 0,1 ponto, desde que o caderno escolhido seja o da sua prova.`}</p></div></details>`;''',
    '''h+=`<details class="acc" data-k="cl"><summary>Como esta nota foi calculada</summary><div class="acc-b"><p class="hint" style="margin:0">${r.semTRI?"Sem TRI nesta área: a nota oficial deste ano não é reproduzível com os dados públicos, então só mostramos os acertos.":r.todosBrancos?"Cartão todo em branco: sem nota calculada.":`Proficiência estimada (EAP): <code>θ = ${fmt(r.theta,4)}</code> com ${r.validas.length} questões.<br>Conversão desta área: <code>nota = ${fmt(kk[0],3)} + ${fmt(kk[1],3)} × θ = ${fmt(r.nota,2)}</code>.<br>${r.band?`Esta área é uma <b>estimativa</b>: nos testes com as notas oficiais o erro ficou abaixo de ±${Math.round(r.band)} pontos em 95% dos casos.`:"Nos testes com as notas oficiais, praticamente todos os participantes ficaram a menos de 1 ponto da nota oficial, desde que o caderno escolhido seja o da sua prova."}`}</p></div></details>`;''')
rep('const R=DATA.red.comp[i], N=DATA.red.nivel;', 'const R=RED.comp[i], N=RED.nivel;')
s = s.replace('DATA.red.comp[', 'RED.comp[').replace('DATA.red.fonte', 'RED.fonte')

# ---------- 5) boletim: só áreas com nota entram nas médias ----------
rep('const tile=a=>{ const r=R[a], ok=r&&r.pronto; return `<div class="tile ${ok?"ok":""}"><span>${AREAS[a].nome}</span><b>${ok?fmt(r.nota):"–"}</b>${ok?`<span>${r.acertos}/${r.validas.length} acertos · ${Math.round(100*r.acertos/r.validas.length)}%</span>`',
    'const tile=a=>{ const r=R[a], ok=r&&r.pronto; return `<div class="tile ${ok&&r.nota!==null?"ok":""}"><span>${AREAS[a].nome}</span><b>${ok?(r.nota!==null?fmt(r.nota):"s/TRI"):"–"}</b>${ok?`<span>${r.acertos}/${r.validas.length} acertos · ${Math.round(100*r.acertos/r.validas.length)}%${r.band?" · ±"+Math.round(r.band):""}${r.semTRI?" · sem TRI neste ano":""}</span>`')
rep('''  [1,2].forEach(d=>{
    const as=Object.keys(AREAS).filter(a=>AREAS[a].dia===d);
    as.forEach(a=>h+=tile(a));
    const ok=as.every(a=>R[a]&&R[a].pronto);''', '''  [1,2].forEach(d=>{
    const as=Object.keys(AREAS).filter(a=>AREAS[a].dia===d); if(!as.length) return;
    as.forEach(a=>h+=tile(a));
    const ok=as.every(a=>R[a]&&R[a].pronto&&R[a].nota!==null);''')
rep('...Object.keys(AREAS).filter(a=>!(R[a]&&R[a].pronto)),', '...Object.keys(AREAS).filter(a=>!(R[a]&&R[a].pronto&&R[a].nota!==null)),')

# ---------- 6) seletor de dia dinâmico ----------
a = s.index('function diaSeg(d){'); b = s.index('function pillHtml(r){') if s.index('function pillHtml(r){') > a else None
rep('''function diaSeg(d){
  const nomes={1:"Linguagens e Humanas",2:"Natureza e Matemática"};
  return `<div class="seg" role="group" aria-label="Dia da prova">${[1,2].map(x=>`<button type="button" aria-pressed="${x===d}" data-act="dia" data-d="${x}">Dia ${x}<small>${nomes[x]}</small></button>`).join("")}</div>`;
}''', '''function diaSeg(d){
  const curto={LC:"Linguagens",CH:"Humanas",CN:"Natureza",MT:"Matemática"};
  const dias=[...new Set(Object.keys(AREAS).map(a=>AREAS[a].dia))].sort();
  const nome=x=>Object.keys(AREAS).filter(a=>AREAS[a].dia===x).map(a=>curto[a]).join(" e ");
  return `<div class="seg" role="group" aria-label="Dia da prova">${dias.map(x=>`<button type="button" aria-pressed="${x===d}" data-act="dia" data-d="${x}">Dia ${x}<small>${nome(x)}</small></button>`).join("")}</div>`;
}''')
rep("CORES[d].forEach(c=>{ h+=`<button", "(CORES[d]||[]).forEach(c=>{ h+=`<button")

# ---------- 7) carregamento sob demanda + abrir exame ----------
rep('/* ---------- navegação ---------- */', '''/* ---------- dados por prova (carregados quando a pessoa abre a prova) ---------- */
const LOADING = {};
function carregarDados(id){
  const ex = EXAMS[id]; if(ex.dados) return Promise.resolve(ex.dados);
  if(!LOADING[id]) LOADING[id] = fetch(`dados/enem_${ex.ano}.json`).then(r=>{ if(!r.ok) throw new Error(r.status); return r.json(); }).then(d=>{ ex.dados=d; return d; }).finally(()=>{ delete LOADING[id]; });
  return LOADING[id];
}
function abrirExame(id){
  setExam(id); const main=$("main");
  main.innerHTML=`<section class="panel"><div class="empty">Carregando ${EX.nome}…</div></section>`; $("dock").classList.add("hidden"); $("tabs").classList.add("hidden");
  return carregarDados(id).then(()=>{ setExam(id); store.view="exam"; salvar(); renderAll(); window.scrollTo({top:0,behavior:"auto"}); }).catch(()=>{
    main.innerHTML=`<section class="panel"><h2>Não consegui carregar ${EX.nome}</h2><p class="hint" style="margin:6px 0 12px">Os dados desta prova são baixados na primeira vez que você a abre. Verifique a conexão e tente de novo.</p><div class="row"><button class="btn pri" type="button" data-act="abrirExam" data-ex="${id}">Tentar de novo</button><button class="btn" type="button" data-act="hub">Voltar ao hub</button></div></section>`;
  });
}

/* ---------- navegação ---------- */''')
rep('    case "abrirExam": setExam(t.dataset.ex); store.view="exam"; salvar(); renderAll(); window.scrollTo({top:0,behavior:"auto"}); break;', '    case "abrirExam": abrirExame(t.dataset.ex); break;')
rep('    case "abrirHist": setExam(t.dataset.ex); abrirHist(+t.dataset.id); break;', '    case "abrirHist": { const id=t.dataset.ex; setExam(id); carregarDados(id).then(()=>{ setExam(id); abrirHist(+t.dataset.id); }); break; }')
rep('carregar(); renderAll();\n</script>', '''carregar();
if(store.view==="exam") abrirExame(store.exam); else renderAll();
</script>''')

# ---------- 8) metodologia ----------
a = s.index('const TRANSP=`'); b = s.index('function renderLobby(){')
s = s[:a] + '''const TRANSP=`<p><b>Aviso:</b> é uma <b>estimativa</b> feita com dados públicos, não a nota oficial emitida pelo INEP.</p>
  <ol>
    <li>Cada questão tem três parâmetros públicos do INEP: <b>a</b> (discriminação), <b>b</b> (dificuldade) e <b>c</b> (acerto ao acaso). A chance de acertar é <code>P(θ) = c + (1 − c) / (1 + e^(−a·(θ − b)))</code>.</li>
    <li>Com seus acertos e erros, calculamos a proficiência θ pelo método <b>EAP</b> (média a posteriori), com distribuição a priori normal padrão e 40 pontos de quadratura entre −4 e 4, como descreve o documento "Procedimentos de Análise" do INEP. Questões sem marcação contam como em branco. Questões anuladas ou sem calibração podem ser marcadas para estudo, mas ficam fora da nota.</li>
    <li>θ vira nota por uma conversão linear própria de cada área, a mesma em todos os anos validados: <code>nota = m + s · θ</code>, com Ciências da Natureza 501,144 + 113,102·θ, Ciências Humanas 501,489 + 112,310·θ, Linguagens 499,978 + 108,086·θ e Matemática 500,020 + 129,646·θ. O INEP não publica essas constantes; nós as obtivemos por regressão contra as notas oficiais.</li>
    <li>A "coerência das respostas" que o INEP cita é um efeito do próprio modelo: acertar questões difíceis e errar fáceis reduz a nota naturalmente. Não há regra extra.</li>
  </ol>
  <p><b>Validação por prova e área</b> (comparação com a nota oficial de todos os participantes da aplicação regular nos microdados):</p>
  <ul>
    <li><b>Exata</b>: pelo menos 99,9% dos participantes ficam a menos de 1 ponto da nota oficial (na grande maioria, a menos de 0,1). Os poucos restantes são cartões atípicos, como caderno marcado errado.</li>
    <li><b>Estimativa</b>: a nota oficial acompanha o cálculo, mas com ruído (correlação acima de 0,94). Mostramos a nota com a margem de erro típica, e ela <b>não</b> deve ser tratada como a nota oficial.</li>
    <li><b>Sem TRI</b>: a nota oficial não pôde ser reproduzida com os dados públicos daquela prova e área. Nesse caso mostramos só acertos, gabarito e enunciados.</li>
  </ul>
  <p><b>Provas antigas:</b> a TRI só existe no ENEM a partir de 2009, e só esses anos estão aqui. Entre 2009 e 2016 o dia 1 foi Ciências Humanas e da Natureza e o dia 2 foi Linguagens e Matemática; de 2017 em diante, o dia 1 é Linguagens e Humanas. A página mostra a ordem de cada ano. Alguns anos têm limites próprios descritos no cartão de cada prova.</p>
  <p><b>Limites:</b> vale para a aplicação regular (cadernos Azul, Amarelo, Branco, Rosa e Cinza, conforme o ano). Não vale para reaplicação, PPL nem provas adaptadas. Se escolher o caderno errado, a nota sai errada, sem aviso. O INEP não publica o assunto de cada questão, só a habilidade da Matriz de Referência; é isso que o raio-X mostra (anos sem habilidade nos dados não têm raio-X). A orientação de redação segue os níveis oficiais do INEP. "Ver" mostra o enunciado extraído da prova oficial, só texto (figuras, gráficos e fórmulas podem faltar); "Pesquisar" busca na internet pela frase da questão.</p>`;
''' + s[b:]

# ---------- 9) dashboard por escopo + lobby novo ----------
a = s.index('function dashHtml(id){'); b = s.index('function chartSvg(hist,uid){')
s = s[:a] + '''function histDe(esc){
  const ids = esc==="all" ? Object.keys(EXAMS) : [esc], out=[];
  for(const id of ids){ const st=store.estados[id]; if(!st) continue; for(const h of st.hist) out.push({...h,_ex:id,nome:(esc==="all"?EXAMS[id].sigla+" · ":"")+h.nome}); }
  return out.sort((a,b)=>a.t-b.t);
}
function dashHtml(esc,comEscopo){
  const hist=histDe(esc);
  if(!hist.length) return `<div class="empty">Nenhum simulado salvo ainda. Corrija as áreas, vá em <b>Resultado</b> e clique em <b>Salvar no histórico</b>: aqui você acompanha se a nota está subindo.</div>`;
  const meds=hist.map(h=>h.notas.MED).filter(v=>v!==null);
  const best=meds.length?Math.max(...meds):null, last=meds.length?meds[meds.length-1]:null, first=meds.length?meds[0]:null;
  const dv=meds.length>1?last-first:null;
  let h="";
  if(comEscopo){ const comHist=Object.keys(EXAMS).filter(id=>store.estados[id]&&store.estados[id].hist.length);
    h+=`<div class="row" style="margin-bottom:10px"><label class="hint" for="escopo">Mostrar:</label><select id="escopo" data-act="escopo"><option value="all" ${esc==="all"?"selected":""}>Todas as provas</option>${comHist.map(id=>`<option value="${id}" ${esc===id?"selected":""}>${EXAMS[id].nome}</option>`).join("")}</select></div>`; }
  h+=`<div class="kpis"><div class="tile"><span>Simulados salvos</span><b>${hist.length}</b></div>
    <div class="tile ok"><span>Melhor média</span><b>${best!==null?fmt(best):"–"}</b></div>
    <div class="tile"><span>Última média</span><b>${last!==null?fmt(last):"–"}</b></div>
    <div class="tile"><span>Evolução (última vs primeira)</span><b class="${dv===null?"":dv>=0?"delta up":"delta dn"}">${dv===null?"–":(dv>=0?"▲ +":"▼ ")+fmt(dv)}</b></div></div>`;
  h+=`<div class="sers" role="group" aria-label="Séries do gráfico">`+SERIES.map(s=>`<button type="button" class="chip" aria-pressed="${CH_SEL.has(s[0])}" data-act="ser" data-s="${s[0]}"><span class="dot" style="background:var(${s[2]})"></span>${s[1]}</button>`).join("")+`</div>`;
  h+=`<div class="chartbox" id="cb-${esc}">${chartSvg(hist,esc)}</div>`;
  h+=`<div class="tblw" style="margin-top:12px"><table style="min-width:560px"><thead><tr><th>Simulado</th><th>Data</th><th>LC</th><th>CH</th><th>CN</th><th>MT</th><th>RED</th><th>Média</th><th>Δ média</th><th></th></tr></thead><tbody>`;
  let prev=null;
  hist.forEach(x=>{
    const n=x.notas, m=n.MED, dl=(m!==null&&prev!==null)?m-prev:null; if(m!==null) prev=m;
    const f=v=>v===null?"–":fmt(v);
    h+=`<tr><td><b>${esc_(x.nome)}</b></td><td>${new Date(x.t).toLocaleDateString("pt-BR")}</td><td>${f(n.LC)}</td><td>${f(n.CH)}</td><td>${f(n.CN)}</td><td>${f(n.MT)}</td><td>${n.RED===null?"–":n.RED}</td><td><b>${f(m)}${x.nn&&x.nn<5?"*":""}</b></td><td>${dl===null?"–":`<span class="delta ${dl>=0?"up":"dn"}">${dl>=0?"▲ +":"▼ "}${fmt(dl)}</span>`}</td><td><button class="btn sm" type="button" data-act="abrirHist" data-id="${x.id}" data-ex="${x._ex}">Abrir</button> <button class="btn sm danger" type="button" data-act="delHist" data-id="${x.id}" data-ex="${x._ex}">Excluir</button></td></tr>`;
  });
  return h+`</tbody></table></div><p class="hint" style="margin-top:8px">* Simulado parcial: a média usa só as notas que existiam (menos de 5). Não compare diretamente com um simulado completo. Provas diferentes têm dificuldades diferentes: compare a evolução com cautela entre anos.</p>`;
}
''' + s[b:]
s = s.replace('${esc(x.nome)}', '${esc_(x.nome)}')
rep('function esc(t){ return String(t).replace', 'function esc_(t){ return esc(t); }\nfunction esc(t){ return String(t).replace')
rep('<td class="par">–</td><td>${lk}</td></tr>`;\n      return;', '<td class="par">–</td><td>${lk}</td></tr>`;\n      return;')
# render do dashboard na RES pane
rep('<section class="panel" id="dashSec"><h2>Sua evolução</h2>${dashHtml(EX.id)}</section>', '<section class="panel" id="dashSec"><h2>Sua evolução</h2>${dashHtml(EX.id,false)}</section>')
# chartSvg usa 'uid' só para CHARTS; initCharts lê box.id: manter

a = s.index('function renderLobby(){'); b = s.index('/* ---------- interação ---------- */')
s = s[:a] + '''function linksProva(m){
  const curto={LC:"Linguagens",CH:"Humanas",CN:"Natureza",MT:"Matemática"};
  const nomeDia=d=>Object.keys(m.areas).filter(a=>m.areas[a].dia===d).map(a=>curto[a]).join(" e ");
  const L=m.links||{}; const dias=Object.keys(L).sort();
  if(!dias.length) return `<a class="btn sm" href="${LINK_INEP}" target="_blank" rel="noopener">Abrir a página de provas do INEP</a>`;
  return dias.map(d=>`<div style="margin-top:8px"><div class="hint" style="margin-bottom:4px"><b>Dia ${d}</b> · ${nomeDia(+d)}</div><div class="row">${Object.keys(L[d]).map(c=>`<a class="btn sm" href="${L[d][c]}" target="_blank" rel="noopener"><span class="dot" style="background:${COR_HEX[c]||"#ccc"}"></span>${COR_NOME[c]||c}</a>`).join("")}</div></div>`).join("");
}
function selo(m){
  const cs=Object.values(m.areas).map(a=>a.classe), tot=Object.keys(m.areas).length;
  const ex=cs.filter(c=>c==="EXATO").length, es=cs.filter(c=>c==="ESTIMADO").length, no=tot-ex-es;
  if(ex===tot) return `<span class="selo ok">TRI exata nas 4 áreas</span>`;
  const p=[]; if(ex) p.push(ex+" exata"+(ex>1?"s":"")); if(es) p.push(es+" estimada"+(es>1?"s":"")); if(no) p.push(no+" sem TRI");
  return `<span class="selo ${no?"no":"es"}">TRI: ${p.join(" · ")}</span>`;
}
function renderLobby(){
  const main=$("main"); let h=`<header class="hero"><h1>Correção <em>ENEM</em></h1>
    <p class="sub">Escolha a prova, faça o simulado e corrija aqui: nota TRI estimada, gabarito, enunciado e onde melhorar. Do ENEM 2025 ao 2009, só as provas que têm TRI.</p></header>
    <div class="strip"><span class="hint">Seu preenchimento fica salvo neste navegador. Perdeu tudo? Carregue o seu backup.</span><div class="row"><button class="btn sm" data-act="bkDown" type="button">Baixar backup</button><button class="btn sm" data-act="bkUp" type="button">Carregar backup</button></div></div>
    <h2 style="margin:6px 0 10px">Escolha a prova</h2><div class="provas">`;
  for(const m of MANIFEST){
    const id="enem"+m.ano, st=store.estados[id];
    const draft=st&&(Object.values(st.ans).some(v=>v.some(x=>x!==""))||Object.values(st.env).some(Boolean));
    const nh=st?st.hist.length:0;
    h+=`<section class="panel pcard"><div class="row" style="justify-content:space-between"><h3 style="margin:0;font-size:1.25rem">ENEM ${m.ano}</h3>${selo(m)}</div>
      ${m.ordem_moderna?"":`<p class="hint" style="margin:6px 0 0">Dia 1: ${Object.keys(m.areas).filter(a=>m.areas[a].dia===1).map(a=>({LC:"Linguagens",CH:"Humanas",CN:"Natureza",MT:"Matemática"})[a]).join(" + ")} (ordem diferente das edições recentes)</p>`}
      <div class="row" style="margin-top:12px"><button class="btn pri" type="button" data-act="abrirExam" data-ex="${id}">${draft?"Continuar o simulado":"Corrigir meu simulado"}</button></div>
      <details class="fazer"><summary class="btn sm" style="margin-top:8px">Fazer a prova (PDF do INEP)</summary>${linksProva(m)}<p class="hint" style="margin:8px 0 0">Abre o caderno oficial em outra aba. Faça a prova no papel e depois corrija aqui, escolhendo a mesma cor do caderno.</p></details>
      ${nh?`<p class="hint" style="margin:8px 0 0">${nh} simulado${nh>1?"s":""} salvo${nh>1?"s":""}</p>`:""}</section>`;
  }
  h+=`</div><section class="panel" id="dashSec" style="margin-top:8px"><h2>Seu desempenho</h2>${dashHtml(DASH_ESC,true)}</section>
    <details class="panel acc foot" style="padding:0"><summary>Como a nota é calculada e validação</summary><div class="acc-b">${TRANSP}</div></details>`;
  main.innerHTML=h;
}

''' + s[b:]
rep('    case "bkDown": baixarBackup(); break;', '    case "bkDown": baixarBackup(); break;')
rep('  if(t.dataset.act==="soerros")', '  if(t.dataset.act==="escopo"){ DASH_ESC=t.value; renderLobby(); initCharts(); return; }\n  if(t.dataset.act==="soerros")')
# o clique em SELECT é ignorado no handler de click; o change cobre o escopo.

# ---------- 10) css ----------
rep('/* seletor de dia */', '''.provas{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
.pcard{margin:0}
.selo{font-size:.78rem;font-weight:700;padding:3px 10px;border-radius:999px;background:var(--greenbg);color:var(--green);white-space:nowrap}
.selo.es{background:var(--warnbg);color:var(--warn)}.selo.no{background:var(--badbg);color:var(--bad)}
details.fazer>summary{list-style:none;cursor:pointer;display:inline-flex}details.fazer>summary::-webkit-details-marker{display:none}
/* seletor de dia */''')
p.write_text(s, encoding='utf-8')
print('ok', len(s))
