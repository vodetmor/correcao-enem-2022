from calib import *
import collections,json
G=np.linspace(-4,4,40)
def thetas(a,S,k=1.0,method='EAP',grid=G):
    out=np.full(len(S),np.nan); grp=collections.defaultdict(list)
    for j,(pv,lg,resp,gabp,nota) in enumerate(S): grp[(pv,lg)].append(j)
    for (pv,lg),idx in grp.items():
        it=build(a,pv,lg); n=len(idx)
        ll=np.zeros((n,len(grid)))
        resps=np.array([list(S[j][2]) for j in idx])
        for i,(g,A,B,C) in enumerate(it):
            if A is None: continue
            p=np.clip(C+(1-C)/(1+np.exp(-k*A*(grid-B))),1e-9,1-1e-9)
            ok=(resps[:,i]==g)[:,None]
            ll+=np.where(ok,np.log(p)[None,:],np.log(1-p)[None,:])
        if method=='EAP':
            lp=ll-0.5*grid[None,:]**2; w=np.exp(lp-lp.max(1,keepdims=True))
            out[idx]=(w*grid).sum(1)/w.sum(1)
        else: out[idx]=grid[ll.argmax(1)]
    return out
consts={}
for a in REG:
    S=[s for s in data[a] if not all(c=='.' for c in s[2])]
    fit=S[:30000]; val=S[30000:42000]
    th=thetas(a,fit); nota=np.array([s[4] for s in fit])
    s,m=np.polyfit(th,nota,1)
    for _ in range(3):
        ok=np.abs(nota-(m+s*th))<1; s,m=np.polyfit(th[ok],nota[ok],1)
    consts[a]=(round(m,3),round(s,3))
    tv=thetas(a,val); nv=np.array([x[4] for x in val]); pred=m+s*tv
    e=pred-nv
    print(f'{a}: nota={m:.3f}+{s:.3f}*theta | validação n={len(val)} MAE={np.abs(e).mean():.3f} corr={np.corrcoef(pred,nv)[0,1]:.5f} max={np.abs(e).max():.2f} dentro de 1pt={np.mean(np.abs(e)<1)*100:.2f}%')
    # variantes com transformação linear própria ajustada
    for k,meth in ((1.0,'ML'),(1.7,'EAP'),(1.7,'ML')):
        t2=thetas(a,val,k,meth,np.linspace(-5,5,201) if meth=='ML' else G)
        s2,m2=np.polyfit(t2,nv,1); e2=m2+s2*t2-nv
        print(f'    variante k={k} {meth} (com ajuste linear próprio): MAE={np.abs(e2).mean():.2f} corr={np.corrcoef(t2,nv)[0,1]:.4f}')
json.dump(consts,open('consts.json','w'))
print(consts)
