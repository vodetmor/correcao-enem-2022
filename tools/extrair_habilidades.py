import re,json
L=open('matriz.txt',encoding='utf-8').read().split('\n')
blocks={'LC':(25,133),'MT':(133,206),'CN':(206,334),'CH':(334,470)}
out={}
for a,(s,e) in blocks.items():
    comp=None; cur=None; d={}; ctitle={}
    for ln in L[s:e]:
        t=ln.strip()
        m=re.match(r'Compet[êe]ncia de [áa]rea (\d+)\s*[-–]\s*(.*)',t)
        h=re.match(r'H(\d+)\s*[-–]\s*(.*)',t)
        if m: comp=int(m.group(1)); ctitle[comp]=m.group(2); cur=('c',comp); continue
        if h: n=int(h.group(1)); d[n]={'c':comp,'t':h.group(2)}; cur=('h',n); continue
        if not t: cur=None if cur and cur[0]=='h' else cur; continue
        if cur and cur[0]=='h': d[cur[1]]['t']+=' '+t
        elif cur and cur[0]=='c': ctitle[cur[1]]+=' '+t
    out[a]={'comp':ctitle,'h':d}
    print(a,len(d),sorted(d)[:3],sorted(d)[-3:],len(ctitle))
json.dump(out,open('habs.json','w'),ensure_ascii=False)
print(out['CH']['h'][1], out['MT']['h'][21],sep='\n')
