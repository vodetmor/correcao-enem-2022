import pathlib
p = pathlib.Path('C:/dev/enem/correcao-enem/tools/template.html'); s = p.read_text(encoding='utf-8')
def rep(old, new):
    global s
    assert old in s, 'âncora não encontrada: ' + old[:90]
    s = s.replace(old, new, 1)

# aviso na área: exata com parâmetros recuperados
rep('''function avisoArea(a){
  const A=AREAS[a];''', '''function avisoArea(a){
  const A=AREAS[a];
  if(A.classe==="EXATO"&&A.recuperado) return `<div class="note info" style="margin-bottom:12px"><b>Nota exata, com parâmetros recuperados.</b> No arquivo oficial de itens desta prova, os parâmetros de ${A.nome} de alguns itens estão trocados ou incorretos e, com eles, a nota oficial não é reproduzida. Recuperamos os valores que o INEP de fato usou a partir das notas oficiais dos participantes e conferimos o resultado em cadernos que não entraram no ajuste: a nota calculada aqui bate com a oficial.</div>`;''')
# resumo no hub
rep("let ex=0,es=0,no=0; for(const m of MANIFEST) for(const a of Object.values(m.areas)){ if(a.classe===\"EXATO\") ex++; else if(a.classe===\"ESTIMADO\") es++; else no++; }",
    "let ex=0,es=0,no=0,rc=0; for(const m of MANIFEST) for(const a of Object.values(m.areas)){ if(a.classe===\"EXATO\"){ ex++; if(a.recuperado) rc++; } else if(a.classe===\"ESTIMADO\") es++; else no++; }")
rep("<b>${es}</b> são estimativas com margem de erro e <b>${no}</b> não têm TRI (só acertos). O selo de cada prova mostra o resultado.`;",
    "${rc?`<b>${rc}</b> delas só bateram depois de recuperarmos parâmetros de itens que estão errados no arquivo oficial. `:\"\"}${es?`<b>${es}</b> são estimativas com margem de erro. `:\"\"}${no?`<b>${no}</b> não têm TRI (só acertos). `:\"\"}O selo de cada prova mostra o resultado.`;")
# metodologia
rep('''  <p><b>Provas antigas:</b>''', '''  <p><b>Parâmetros recuperados:</b> em algumas provas e áreas, o arquivo oficial de itens do INEP tem parâmetros de itens fora do lugar ou incorretos, e a nota oficial não pode ser reproduzida com eles. Nesses casos, recuperamos os parâmetros efetivamente usados a partir das notas oficiais dos participantes (busca da combinação que reproduz as notas e ajuste fino) e só adotamos o resultado quando ele também reproduz a nota oficial em cadernos e participantes que não entraram no ajuste. Cada área desse tipo traz um aviso na página da prova.</p>
  <p><b>Provas antigas:</b>''')
p.write_text(s, encoding='utf-8')
m = pathlib.Path('C:/dev/enem/correcao-enem/tools/montar_multi.py'); t = m.read_text(encoding='utf-8')
old = "classe=v['classe'], band=v.get('band'))"
assert old in t
m.write_text(t.replace(old, "classe=v['classe'], band=v.get('band'), recuperado=bool(v.get('recuperado')))", 1), encoding='utf-8')
print('ok')
