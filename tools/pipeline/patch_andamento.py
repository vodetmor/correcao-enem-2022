"""1) dados por prova carregados como <script> (funciona em file://); 2) 'Correção em andamento' no hub (guarda o resumo por área)."""
import pathlib
p = pathlib.Path('C:/dev/enem/correcao-enem/tools/template.html')
s = p.read_text(encoding='utf-8')


def rep(old, new):
    global s
    assert old in s, 'âncora não encontrada: ' + old[:90]
    s = s.replace(old, new, 1)


# ---- 1) carregamento por script (vale em file:// e em http) ----
rep('''  if(!LOADING[id]) LOADING[id] = fetch(`dados/enem_${ex.ano}.json`).then(r=>{ if(!r.ok) throw new Error(r.status); return r.json(); }).then(d=>{ ex.dados=d; return d; }).finally(()=>{ delete LOADING[id]; });''',
    '''  if(!LOADING[id]) LOADING[id] = new Promise((ok,erro)=>{
    const sc=document.createElement("script"); sc.src=`dados/enem_${ex.ano}.js`;
    sc.onload=()=>{ const d=(window.__DADOS||{})[ex.ano]; if(d){ ex.dados=d; ok(d); } else erro(new Error("sem dados")); };
    sc.onerror=()=>erro(new Error("falha ao carregar"));
    document.head.appendChild(sc);
  }).finally(()=>{ delete LOADING[id]; });''')

# ---- 2) resumo por área no estado ----
rep('const e = {tab:Object.keys(ex.areas)[0],cor:{1:null,2:null},lang:null,ans:{},env:{},red:[null,null,null,null,null],hist:[]};',
    'const e = {tab:Object.keys(ex.areas)[0],cor:{1:null,2:null},lang:null,ans:{},env:{},res:{},red:[null,null,null,null,null],hist:[]};')
rep('  if(Array.isArray(o.red)&&o.red.length===5) e.red=o.red.map(x=>NIVEIS.includes(x)?x:null);\n}',
    '''  if(Array.isArray(o.red)&&o.red.length===5) e.red=o.red.map(x=>NIVEIS.includes(x)?x:null);
  if(o.res&&typeof o.res==="object") for(const a in ex.areas){ const v=o.res[a];
    if(v&&typeof v==="object") e.res[a]={nota:(typeof v.nota==="number"&&v.nota>=0&&v.nota<=1000)?v.nota:null,ac:Math.max(0,Math.min(99,Number(v.ac)||0)),tot:Math.max(0,Math.min(99,Number(v.tot)||0)),band:typeof v.band==="number"?v.band:null,sem:v.sem?1:0}; }
}''')
rep('function renderPane(){\n  const t=S.tab;', '''/* resumo por área corrigida: o hub mostra "Correção em andamento" sem precisar carregar os dados da prova */
function sincRes(){
  let mudou=false;
  for(const a in AREAS){
    const r=analisarC(a);
    if(r&&r.pronto){ const v={nota:r.nota,ac:r.acertos,tot:r.validas.length,band:r.band||null,sem:r.semTRI?1:0}; if(JSON.stringify(S.res[a])!==JSON.stringify(v)){ S.res[a]=v; mudou=true; } }
    else if(S.res[a]){ delete S.res[a]; mudou=true; }
  }
  if(mudou) salvar();
}
function renderPane(){
  sincRes();
  const t=S.tab;''')

# ---- 3) faixa no cartão da prova ----
rep('''      ${nh?`<p class="hint" style="margin:8px 0 0">${nh} simulado${nh>1?"s":""} salvo${nh>1?"s":""}</p>`:""}</section>`;''',
    '''      ${andamento(m,st)}
      ${nh?`<p class="hint" style="margin:8px 0 0">${nh} simulado${nh>1?"s":""} salvo${nh>1?"s":""}</p>`:""}</section>`;''')
rep('function selo(m){', '''function andamento(m,st){
  if(!st||!st.res) return "";
  const as=Object.keys(m.areas), feitas=as.filter(a=>st.res[a]); if(!feitas.length) return "";
  const curto={LC:"Linguagens",CH:"Humanas",CN:"Natureza",MT:"Matemática"};
  const notas=feitas.map(a=>st.res[a].nota).filter(v=>v!==null); const rs=redSoma(st); const todas=[...notas,...(rs!==null?[rs]:[])];
  const media=todas.length?todas.reduce((x,y)=>x+y,0)/todas.length:null;
  const chips=as.map(a=>{ const v=st.res[a]; return v?`<span class="chipn ok">${curto[a]} <b>${v.nota!==null?fmt(v.nota)+(v.band?" ±"+Math.round(v.band):""):v.ac+"/"+v.tot+" acertos"}</b></span>`:`<span class="chipn">${curto[a]} <b>a corrigir</b></span>`; }).join("")+(rs!==null?`<span class="chipn ok">Redação <b>${rs}</b></span>`:"");
  return `<div class="andamento"><b>${feitas.length===as.length?"Correção completa":"Correção em andamento"}</b> · ${feitas.length} de ${as.length} áreas<div class="row" style="gap:6px;margin-top:6px">${chips}</div>${media!==null?`<div class="hint" style="margin-top:6px">Média simples do que já foi corrigido: <b>${fmt(media)}</b>${todas.length<as.length+1?" (parcial)":""}</div>`:""}</div>`;
}
function selo(m){''')
rep('/* seletor de dia */', '''.andamento{margin-top:10px;padding:10px 12px;border-radius:12px;background:var(--bluebg);font-size:.9rem}
.chipn{display:inline-block;padding:2px 10px;border-radius:999px;background:var(--card);border:1px solid var(--line);font-size:.8rem;color:var(--muted)}
.chipn b{color:var(--ink)}.chipn.ok{border-color:var(--green)}.chipn.ok b{color:var(--green)}
/* seletor de dia */''')
p.write_text(s, encoding='utf-8')

# ---- montar_multi: dados como .js ----
m = pathlib.Path('C:/dev/enem/correcao-enem/tools/montar_multi.py'); t = m.read_text(encoding='utf-8')
old = "    (raiz / 'dados' / f'enem_{ano}.json').write_text(json.dumps(pac['dados'], ensure_ascii=False, separators=(',', ':')), encoding='utf-8')"
assert old in t
t = t.replace(old, "    (raiz / 'dados' / f'enem_{ano}.js').write_text('window.__DADOS=window.__DADOS||{};window.__DADOS[%d]=%s;' % (ano, json.dumps(pac['dados'], ensure_ascii=False, separators=(',', ':'))), encoding='utf-8')", 1)
t = t.replace("(raiz / 'dados').mkdir(exist_ok=True)", "(raiz / 'dados').mkdir(exist_ok=True)\nfor velho in (raiz / 'dados').glob('enem_*.json'): velho.unlink()", 1)
t = t.replace("(raiz / 'dados').glob('enem_*.json')", "(raiz / 'dados').glob('enem_*.js')").replace("for velho in (raiz / 'dados').glob('enem_*.js'): velho.unlink()", "for velho in (raiz / 'dados').glob('enem_*.json'): velho.unlink()")
m.write_text(t, encoding='utf-8')
sw = pathlib.Path('C:/dev/enem/correcao-enem/sw.js'); u = sw.read_text(encoding='utf-8'); sw.write_text(u.replace('correcao-enem-v1', 'correcao-enem-v2').replace('dados/enem_ANO.json', 'dados/enem_ANO.js'), encoding='utf-8')
print('ok')
