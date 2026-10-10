import csv,collections,numpy as np,sys
D='C:/dev/enem/2022/DADOS/'
items=collections.defaultdict(dict)  # (area,prova,lingua)->pos->tuple
for r in csv.DictReader(open(D+'ITENS_PROVA_2022.csv',encoding='latin-1'),delimiter=';'):
    ab=r['IN_ITEM_ABAN']=='1'
    t=(r['TX_GABARITO'],None if ab else float(r['NU_PARAM_A']),None if ab else float(r['NU_PARAM_B']),None if ab else float(r['NU_PARAM_C']))
    items[(r['SG_AREA'],r['CO_PROVA'],r['TP_LINGUA'])][int(r['CO_POSICAO'])]=t
def build(area,prova,lg):
    d={}
    if area=='LC':
        d.update(items[(area,prova,'')]); d.update(items[(area,prova,lg)])
    else: d.update(items[(area,prova,'')])
    return [d[i] for i in sorted(d)] if len(d)==45 else None
REG={'CH':['1055','1056','1057','1058'],'CN':['1085','1086','1087','1088'],'LC':['1065','1066','1067','1068'],'MT':['1075','1076','1077','1078']}
rows=list(csv.DictReader(open('amostra.csv',encoding='utf-8'),delimiter=';'))
print(len(rows))
data={a:[] for a in REG}
for r in rows:
    for a in REG:
        if r['TP_PRESENCA_'+a]=='1' and r['CO_PROVA_'+a] in REG[a] and r['NU_NOTA_'+a]:
            data[a].append((r['CO_PROVA_'+a],r['TP_LINGUA'],r['TX_RESPOSTAS_'+a],r['TX_GABARITO_'+a],float(r['NU_NOTA_'+a])))
def prep(a,N=8000):
    out=[]; 
    for pv,lg,resp,gabp,nota in data[a][:N]:
        it=build(a,pv,lg)
        if it is None: continue
        out.append((it,resp,nota))
    return out
Q=np.linspace(-4,4,40)
def loglik(it,resp,k,grid):
    ll=np.zeros_like(grid)
    for (g,A,B,C),x in zip(it,resp):
        if A is None: continue
        p=C+(1-C)/(1+np.exp(-k*A*(grid-B)))
        p=np.clip(p,1e-9,1-1e-9)
        ll+=np.log(p) if x==g else np.log(1-p)
    return ll
def est(it,resp,k,method,grid,prior=(0,1)):
    ll=loglik(it,resp,k,grid)
    if method=='EAP':
        lp=ll-0.5*((grid-prior[0])/prior[1])**2
        w=np.exp(lp-lp.max()); return (w*grid).sum()/w.sum()
    return grid[np.argmax(ll)]
if __name__=='__main__':
    fine=np.linspace(-5,5,401)
    res={}
    for a in REG:
        P=prep(a,3000); nota=np.array([p[2] for p in P])
        print(a,len(P))
        for k in (1.0,1.7):
            for m,grid in (('EAP40',Q),('EAPfino',fine),('ML',fine)):
                meth='ML' if m=='ML' else 'EAP'
                th=np.array([est(it,rs,k,meth,grid) for it,rs,_ in P])
                for nm,conv in (('500+100t',500+100*th),):
                    err=conv-nota
                    print(f'  k={k} {m:8s} {nm} MAE={np.abs(err).mean():6.1f} bias={err.mean():6.1f} corr={np.corrcoef(conv,nota)[0,1]:.4f}')
