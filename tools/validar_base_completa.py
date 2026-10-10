import csv,collections,json,numpy as np,sys
sys.path.insert(0,'.')
from calib import items,build,REG
consts=json.load(open('consts.json'))
G=np.linspace(-4,4,40)
cache={}
def itm(a,pv,lg):
    k=(a,pv,lg)
    if k not in cache:
        it=build(a,pv,lg)
        if it is None: cache[k]=None
        else:
            g=np.array([x[0] for x in it]); ab=np.array([x[1] is None for x in it])
            A=np.array([x[1] or 0 for x in it]); B=np.array([x[2] or 0 for x in it]); C=np.array([x[3] or 0 for x in it])
            P=np.clip(C[:,None]+(1-C[:,None])/(1+np.exp(-A[:,None]*(G[None,:]-B[:,None]))),1e-9,1-1e-9)
            cache[k]=(g,ab,np.log(P),np.log(1-P))
    return cache[k]
stats={a:collections.Counter() for a in REG}; worst={a:[] for a in REG}
buf={a:collections.defaultdict(list) for a in REG}
def flush(a):
    m,s=consts[a]
    for (pv,lg),L in buf[a].items():
        d=itm(a,pv,lg)
        if d is None: stats[a]['sem_caderno_regular']+=len(L); continue
        g,ab,lP,lQ=d
        R=np.array([[ord(c) for c in x[0]] for x in L]); ok=(R==np.array([ord(c) for c in g])[None,:])
        ll=np.zeros((len(L),len(G)))
        for i in range(45):
            if ab[i]: continue
            ll+=np.where(ok[:,i][:,None],lP[i][None,:],lQ[i][None,:])
        lp=ll-0.5*G[None,:]**2; w=np.exp(lp-lp.max(1,keepdims=True)); th=(w*G).sum(1)/w.sum(1)
        pred=m+s*th
        for j,x in enumerate(L):
            nota=x[1]; e=abs(pred[j]-nota)
            blank=all(c in '.' for c in x[0])
            key='todo_branco' if blank else 'normal'
            stats[a][key+'_n']+=1
            if e<1: stats[a][key+'_ok1']+=1
            elif len(worst[a])<8: worst[a].append((pv,lg,x[0],round(pred[j],1),nota))
            if e<0.1: stats[a][key+'_ok01']+=1
    buf[a].clear()
f=open('C:/dev/enem/2022/DADOS/MICRODADOS_ENEM_2022.csv',encoding='latin-1',newline='')
r=csv.DictReader(f,delimiter=';'); n=0
for row in r:
    n+=1
    for a in REG:
        if row['TP_PRESENCA_'+a]=='1' and row['NU_NOTA_'+a] and row['CO_PROVA_'+a] in REG[a]:
            buf[a][(row['CO_PROVA_'+a],row['TP_LINGUA'])].append((row['TX_RESPOSTAS_'+a],float(row['NU_NOTA_'+a])))
        elif row['TP_PRESENCA_'+a]=='1' and row['NU_NOTA_'+a]: stats[a]['outro_caderno_com_nota']+=1
    if n%150000==0:
        for a in REG: flush(a)
        print(n,flush=True)
for a in REG: flush(a)
out={a:dict(stats[a]) for a in REG}; out['worst']={a:worst[a] for a in REG}
json.dump(out,open('full_result.json','w'),indent=1); print('FIM')
