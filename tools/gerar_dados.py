import csv,json,statistics
D='C:/dev/enem/2022/DADOS/'
rows=list(csv.DictReader(open(D+'ITENS_PROVA_2022.csv',encoding='latin-1'),delimiter=';'))
REG={'CH':{'AZUL':'1055','AMARELA':'1056','BRANCA':'1057','ROSA':'1058'},
     'CN':{'AZUL':'1085','AMARELA':'1086','CINZA':'1087','ROSA':'1088'},
     'LC':{'AZUL':'1065','AMARELA':'1066','ROSA':'1067','BRANCA':'1068'},
     'MT':{'AZUL':'1075','AMARELA':'1076','ROSA':'1077','CINZA':'1078'}}
consts=json.load(open('consts.json'))
out={'items':{},'cad':{},'tert':{},'k':{}}
for a,m in REG.items():
    idx={}; items=[]; cad={}
    for cor,pv in m.items():
        rs=[r for r in rows if r['SG_AREA']==a and r['CO_PROVA']==pv and r['IN_ITEM_ADAPTADO']=='0']
        langs=[''] if a!='LC' else ['0','1']
        lists=[]
        for lg in langs:
            sel={}
            for r in rs:
                if r['TP_LINGUA'] in ('',lg): sel[int(r['CO_POSICAO'])]=r
            assert len(sel)==45,(a,cor,lg,len(sel))
            L=[]
            for p in sorted(sel):
                r=sel[p]; ci=r['CO_ITEM']
                if ci not in idx:
                    ab=r['IN_ITEM_ABAN']=='1'
                    mot=r['TX_MOTIVO_ABAN'].lower()
                    mc=1 if 'pedag' in mot else 2
                    idx[ci]=len(items)
                    items.append([None,None,None,int(r['CO_HABILIDADE']),r['TX_GABARITO'],mc] if ab else
                                 [float(r['NU_PARAM_A']),float(r['NU_PARAM_B']),float(r['NU_PARAM_C']),int(r['CO_HABILIDADE']),r['TX_GABARITO'],0])
                L.append(idx[ci])
            lists.append(L)
        cad[cor]=lists if a=='LC' else lists[0]
    out['items'][a]=items; out['cad'][a]=cad
    bs=sorted(i[1] for i in items if i[1] is not None)
    # tercis sobre as questões efetivamente usadas (únicas)
    out['tert'][a]=[round(bs[len(bs)//3],3),round(bs[2*len(bs)//3],3)]
    out['k'][a]=list(consts[a])
    print(a,len(items),'anuladas:',sum(1 for i in items if i[0] is None),'tercis',out['tert'][a])
json.dump(out,open('dados.json','w'),separators=(',',':'))
import os;print(os.path.getsize('dados.json'),'bytes')
