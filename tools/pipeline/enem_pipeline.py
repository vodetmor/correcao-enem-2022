"""Núcleo do pipeline de calibração por ano.

Para um ano (zip ou pasta do INEP), faz tudo sem intervenção:
  1. lê ITENS_PROVA e o arquivo de resultados (layouts diferentes entre anos);
  2. ajusta por regressão as constantes nota = m + s*theta de cada área (EAP, k=1, prior N(0,1), 40 pontos);
  3. valida em passagem completa contra a nota oficial de todos os participantes presentes;
  4. grava o pacote de dados do ano (itens, cadernos, constantes, contagens) e um relatório honesto.
Nada aqui assume que o ano "deve" bater: o relatório classifica EXATO / APROXIMADO / NAO_VALIDO.
"""
import io, re, csv, json, zipfile, pathlib, collections, sys
import numpy as np

_LIBS = pathlib.Path('C:/dev/enem/_work/libs')   # pip install --target ...: zipfile-deflate64 (zips com Deflate64, ex.: RESULTADOS_2025.csv)
if _LIBS.exists(): sys.path.append(str(_LIBS))
try: import zipfile_deflate64
except ImportError: pass

AREAS = ('CN', 'CH', 'LC', 'MT')
GRID = np.linspace(-4, 4, 40)
csv.field_size_limit(1 << 24)


class _Deflate64(io.RawIOBase):
    """Fluxo descomprimido de uma entrada zip com Deflate64, lido em blocos (usa o pacote inflate64)."""
    def __init__(self, caminho, info):
        import struct, inflate64
        self.f = open(caminho, 'rb'); self.f.seek(info.header_offset)
        h = self.f.read(30); n, m = struct.unpack('<HH', h[26:30])
        self.f.seek(info.header_offset + 30 + n + m)
        self.rest = info.compress_size; self.inf = inflate64.Inflater(); self.buf = b''; self.pos = 0
    def readable(self): return True
    def readinto(self, b):
        while self.pos >= len(self.buf):
            if self.rest <= 0: return 0
            ch = self.f.read(min(1 << 20, self.rest)); self.rest -= len(ch)
            if not ch: return 0
            self.buf = self.inf.inflate(ch); self.pos = 0
        k = min(len(b), len(self.buf) - self.pos); b[:k] = self.buf[self.pos:self.pos + k]; self.pos += k
        return k
    def close(self):
        try: self.f.close()
        finally: super().close()


# ---------- fonte (zip ou pasta) ----------
class Fonte:
    def __init__(self, caminho):
        self.p = pathlib.Path(caminho)
        self.zip = zipfile.ZipFile(self.p) if self.p.suffix.lower() == '.zip' else None

    def nomes(self):
        return self.zip.namelist() if self.zip else [str(x.relative_to(self.p)) for x in self.p.rglob('*') if x.is_file()]

    def abrir(self, nome):
        if not self.zip: return open(self.p / nome, 'rb')
        info = self.zip.getinfo(nome)
        if info.compress_type == 9:   # Deflate64 (ex.: RESULTADOS_2025.csv): o zipfile do Python não lê
            return io.BufferedReader(_Deflate64(self.p, info), buffer_size=1 << 20)
        return self.zip.open(nome)

    def achar(self, padrao, exts=('.csv', '.txt')):
        c = [n for n in self.nomes() if re.search(padrao, n.replace('\\', '/').split('/')[-1], re.I) and n.lower().endswith(exts)]
        if not c: return None
        if self.zip: c.sort(key=lambda n: -self.zip.getinfo(n).file_size)
        return c[0]


def linhas(fonte, nome):
    """Devolve (cabecalho_maiusculo, iterador de listas). Detecta separador e codificação."""
    raw = fonte.abrir(nome)
    f = io.TextIOWrapper(raw, encoding='latin-1', newline='')
    cab = f.readline()
    sep = ';' if cab.count(';') >= cab.count(',') else ','
    h = [c.strip().strip('"').upper() for c in next(csv.reader([cab], delimiter=sep))]
    return h, csv.reader(f, delimiter=sep)


def num(x):
    x = (x or '').strip().replace(',', '.')
    try: return float(x)
    except ValueError: return None


# ---------- itens ----------
def carregar_itens(fonte):
    nome = fonte.achar(r'^itens_prova')
    h, it = linhas(fonte, nome)
    ix = {c: i for i, c in enumerate(h)}
    g = lambda r, c: r[ix[c]].strip() if c in ix and ix[c] < len(r) else ''
    out = []
    for r in it:
        if not r or not g(r, 'SG_AREA'): continue
        out.append(dict(area=g(r, 'SG_AREA'), pos=int(float(g(r, 'CO_POSICAO') or 0)), item=g(r, 'CO_ITEM'), gab=g(r, 'TX_GABARITO'),
                        hab=int(float(g(r, 'CO_HABILIDADE') or 0)), aban=g(r, 'IN_ITEM_ABAN') == '1', motivo=g(r, 'TX_MOTIVO_ABAN').lower(),
                        a=num(g(r, 'NU_PARAM_A')), b=num(g(r, 'NU_PARAM_B')), c=num(g(r, 'NU_PARAM_C')), cor=g(r, 'TX_COR'),
                        prova=g(r, 'CO_PROVA'), lingua=g(r, 'TP_LINGUA'), adapt=g(r, 'IN_ITEM_ADAPTADO') == '1'))
    return out, h


def aplicar_override(itens, ano, saida='C:/dev/enem/_work/saida', minimo=99.5):
    """Substitui os parâmetros de itens cujos valores publicados não reproduzem a nota oficial (ver corrigir_params.py).
    Só vale para a área cujo ajuste passou na validação (mesmo caderno com outros participantes E demais cadernos >= minimo% a menos de 1 ponto)."""
    areas = set()
    for f in pathlib.Path(saida).glob(f'params_{ano}_*.json'):
        d = json.loads(f.read_text(encoding='utf-8')); h = d.get('holdout', {}); outros = list(d.get('validacao_outros_cadernos', {}).values())
        if h.get('dentro_1', 0) < minimo or any(v.get('corrigido_dentro_1', 0) < minimo for v in outros): continue
        a, pr = d['area'], d['params']
        for x in itens:
            if x['area'] == a and x['item'] in pr:
                x['a'], x['b'], x['c'] = pr[x['item']]; x['aban'] = False; x['motivo'] = ''   # inclui itens que o arquivo marcava sem parâmetros mas entraram na nota
        areas.add(a)
    return areas


def montar_cadernos(itens):
    """(area, prova) -> {'cor','adapt','langs': {lingua|'': [itens ordenados por posição]}} """
    por = collections.defaultdict(list)
    for x in itens: por[(x['area'], x['prova'])].append(x)
    cad = {}
    for k, xs in por.items():
        comuns = {x['pos']: x for x in xs if x['lingua'] == ''}
        langs = sorted({x['lingua'] for x in xs if x['lingua'] != ''})
        d = {}
        if not langs: d[''] = [comuns[p] for p in sorted(comuns)]
        else:
            for l in langs:
                m = dict(comuns); m.update({x['pos']: x for x in xs if x['lingua'] == l})
                d[l] = [m[p] for p in sorted(m)]
        cad[k] = dict(cor=xs[0]['cor'], adapt=any(x['adapt'] for x in xs), langs=d)
    return cad


# ---------- resultados ----------
def mapa_resultados(h):
    ix = {c: i for i, c in enumerate(h)}
    m = {}
    for a in AREAS:
        need = [f'TP_PRESENCA_{a}', f'NU_NOTA_{a}', f'TX_RESPOSTAS_{a}']
        if not all(n in ix for n in need): continue
        m[a] = dict(pres=ix[need[0]], nota=ix[need[1]], resp=ix[need[2]], prova=ix.get(f'CO_PROVA_{a}', ix.get('CO_PROVA')))
    return m, ix.get('TP_LINGUA')


def participantes(fonte, nome_res, areas_ok=None):
    h, it = linhas(fonte, nome_res)
    m, il = mapa_resultados(h)
    for r in it:
        for a, c in m.items():
            if len(r) <= max(c['pres'], c['nota'], c['resp']): continue
            if r[c['pres']].strip() != '1': continue
            nota = num(r[c['nota']])
            if nota is None: continue
            prova = r[c['prova']].strip() if c['prova'] is not None and c['prova'] < len(r) else ''
            lg = r[il].strip() if il is not None and il < len(r) else ''
            yield a, prova, lg, r[c['resp']], nota


# ---------- TRI ----------
def prep_caderno(cad, area, prova, lingua):
    d = cad.get((area, prova))
    if not d: return None
    its = d['langs'].get(lingua) or d['langs'].get('') or (next(iter(d['langs'].values())) if len(d['langs']) == 1 else None)
    if its is None: return None
    n = len(its)
    gab = np.array([x['gab'] for x in its]); aban = np.array([x['a'] is None or x['aban'] for x in its])
    A = np.array([x['a'] or 0 for x in its]); B = np.array([x['b'] or 0 for x in its]); C = np.array([x['c'] or 0 for x in its])
    P = np.clip(C[:, None] + (1 - C[:, None]) / (1 + np.exp(-A[:, None] * (GRID[None, :] - B[:, None]))), 1e-9, 1 - 1e-9)
    return dict(n=n, gab=gab, aban=aban, lP=np.log(P), lQ=np.log(1 - P))


def thetas(pc, resps):
    """EAP vetorizado para participantes de um mesmo (caderno, idioma). resps: lista de strings."""
    L = np.array([list(r.ljust(pc['n'], '.')[:pc['n']]) for r in resps])
    ok = L == pc['gab'][None, :]
    ll = np.zeros((len(resps), len(GRID)))
    for i in range(pc['n']):
        if pc['aban'][i]: continue
        ll += np.where(ok[:, i][:, None], pc['lP'][i][None, :], pc['lQ'][i][None, :])
    lp = ll - 0.5 * GRID[None, :] ** 2
    w = np.exp(lp - lp.max(1, keepdims=True))
    return (w * GRID).sum(1) / w.sum(1)


def em_branco(r): return set(r) <= {'.'}


def normalizar_resp(area, resp, n, lg):
    """LC com 50 caracteres (anos em que a base traz os dois blocos de idioma, o não usado como '99999'):
    escolhe o bloco do idioma (0=inglês: 0:5; 1=espanhol: 5:10) e junta com as 40 comuns (10:50)."""
    if area == 'LC' and len(resp) == n + 5 and lg in ('0', '1'):
        b = 0 if lg == '0' else 5
        return resp[b:b + 5] + resp[10:]
    return resp


class Acumulador:
    """Agrupa participantes por (area, prova, lingua) e calcula theta em lotes."""
    def __init__(self, cad): self.cad, self.buf, self.cache = cad, collections.defaultdict(list), {}

    def add(self, a, prova, lg, resp, nota):
        self.buf[(a, prova, lg)].append((resp, nota))

    def calcular(self):
        for (a, prova, lg), L in self.buf.items():
            key = (a, prova, lg)
            if key not in self.cache: self.cache[key] = prep_caderno(self.cad, a, prova, lg)
            pc = self.cache[key]
            if pc is None:
                yield a, prova, lg, None, None, len(L); continue
            keep = [(r, n) for r, n in L if not em_branco(r)]
            if not keep: continue
            th = thetas(pc, [normalizar_resp(a, r, pc['n'], lg) for r, _ in keep])
            yield a, prova, lg, th, np.array([n for _, n in keep]), len(L)
        self.buf.clear()


# ---------- ajuste e validação ----------
def ajustar(fonte, nome_res, cad, regulares, por_area=30000):
    """Regressão nota = m + s*theta com participantes das provas 'regulares' (por área)."""
    acc = Acumulador(cad); cont = collections.Counter()
    for a, prova, lg, resp, nota in participantes(fonte, nome_res):
        if prova in regulares.get(a, ()) and cont[a] < por_area and not em_branco(resp):
            acc.add(a, prova, lg, resp, nota); cont[a] += 1
        if all(cont[x] >= por_area for x in regulares): break
    T = collections.defaultdict(lambda: ([], []))
    for a, prova, lg, th, nota, _ in acc.calcular():
        if th is None: continue
        T[a][0].extend(th); T[a][1].extend(nota)
    consts = {}
    for a, (th, nt) in T.items():
        th, nt = np.array(th), np.array(nt)
        s, m = np.polyfit(th, nt, 1)
        for _ in range(4):
            ok = np.abs(nt - (m + s * th)) < 1
            if ok.sum() < 50: break
            s, m = np.polyfit(th[ok], nt[ok], 1)
        res = nt - (m + s * th)
        consts[a] = dict(m=round(float(m), 3), s=round(float(s), 3), n_ajuste=int(len(th)), mae_ajuste=round(float(np.abs(res).mean()), 4), pct_dentro_1=round(float((np.abs(res) < 1).mean() * 100), 3))
    return consts


def validar_completo(fonte, nome_res, cad, consts, regulares, lote=120000):
    """Passagem completa: compara pred com a nota oficial de TODOS os participantes presentes."""
    est = {a: collections.Counter() for a in AREAS}
    por_prova = {a: collections.defaultdict(collections.Counter) for a in AREAS}
    acc = Acumulador(cad); n = 0

    def fechar():
        for a, prova, lg, th, nota, tot in acc.calcular():
            if th is None:
                est[a]['sem_caderno_nos_itens'] += tot; por_prova[a][prova]['sem_itens'] += tot; continue
            pred = consts[a]['m'] + consts[a]['s'] * th; e = np.abs(pred - nota)
            reg = prova in regulares.get(a, ())
            k = 'regular' if reg else 'outras'
            est[a][k + '_n'] += len(e); est[a][k + '_ate_0_1'] += int((e < 0.1).sum()); est[a][k + '_ate_1'] += int((e < 1).sum())
            est[a][k + '_max'] = max(est[a][k + '_max'], float(e.max())); por_prova[a][prova]['n'] += len(e); por_prova[a][prova]['ok1'] += int((e < 1).sum())
    brancos = {a: collections.Counter() for a in AREAS}
    for a, prova, lg, resp, nota in participantes(fonte, nome_res):
        if a not in consts: continue
        if em_branco(resp):
            brancos[a]['branco'] += 1; brancos[a]['branco_nota0'] += int(nota == 0.0); continue
        acc.add(a, prova, lg, resp, nota); n += 1
        if n % lote == 0: fechar()
    fechar()
    return {a: dict(est[a]) for a in AREAS if est[a]}, {a: dict(brancos[a]) for a in AREAS if brancos[a]}, {a: {p: dict(c) for p, c in d.items()} for a, d in por_prova.items() if d}


def classificar(est):
    """EXATO se >=99.99% das provas regulares ficam a menos de 0,1 ponto; APROXIMADO se a menos de 1 ponto em >=99%."""
    out = {}
    for a, e in est.items():
        n = e.get('regular_n', 0)
        if not n: out[a] = 'SEM_DADOS'; continue
        p01 = e['regular_ate_0_1'] / n; p1 = e['regular_ate_1'] / n
        out[a] = 'EXATO' if p01 >= 0.9999 else ('APROXIMADO' if p1 >= 0.99 else 'NAO_VALIDO')
    return out


def descobrir_regulares(fonte, nome_res, cad, amostra=400000):
    """Provas 'regulares' = as mais populares por área (cobrem >= 80% dos presentes, até 8 códigos)."""
    c = {a: collections.Counter() for a in AREAS}; n = 0
    for a, prova, lg, resp, nota in participantes(fonte, nome_res):
        c[a][prova] += 1; n += 1
        if n >= amostra: break
    reg = {}
    for a, cnt in c.items():
        tot = sum(cnt.values()); acum = 0; sel = []
        for prova, k in cnt.most_common(8):
            if (a, prova) not in cad: continue
            cad_ad = cad[(a, prova)]['adapt']
            if cad_ad: continue
            if k < 0.02 * tot and acum >= 0.8 * tot: break
            sel.append(prova); acum += k
            if acum >= 0.97 * tot: break
        reg[a] = sel
    return reg, {a: dict(v.most_common(12)) for a, v in c.items()}


def processar_ano(caminho, ano, saida):
    fonte = Fonte(caminho)
    rel = dict(ano=ano, fonte=str(caminho))
    nome_res = fonte.achar(r'^(microdados|resultados)')
    rel['arquivo_resultados'] = nome_res
    itens, hitens = carregar_itens(fonte)
    cad = montar_cadernos(itens)
    rel['itens_linhas'] = len(itens); rel['colunas_itens'] = hitens
    h, _ = linhas(fonte, nome_res); m, il = mapa_resultados(h)
    rel['areas_com_respostas_e_notas'] = sorted(m); rel['tem_TP_LINGUA'] = il is not None
    if not m:
        rel['status'] = 'SEM_RESPOSTAS_OU_NOTAS'; return rel
    regulares, populares = descobrir_regulares(fonte, nome_res, cad)
    rel['regulares'] = regulares; rel['provas_mais_populares'] = populares
    consts = ajustar(fonte, nome_res, cad, regulares)
    rel['constantes'] = consts
    est, brancos, por_prova = validar_completo(fonte, nome_res, cad, consts, regulares)
    rel['validacao'] = est; rel['cartoes_em_branco'] = brancos; rel['por_prova'] = por_prova
    rel['classificacao'] = classificar(est)
    rel['status'] = 'OK'
    return rel


K0 = {'CN': (501.144, 113.102), 'CH': (501.489, 112.310), 'LC': (499.978, 108.086), 'MT': (500.020, 129.646)}


def processar_ano2(caminho, ano, saida, lote=120000, p_amostra=0.012, cap_amostra=40000, limite=None):
    """Passagem única: valida com as constantes universais e guarda amostra aleatória para ajuste onde falhar."""
    import random
    random.seed(ano)
    fonte = Fonte(caminho); rel = dict(ano=ano, versao=2)
    nome_res = fonte.achar(r'^(microdados|resultados)'); rel['arquivo_resultados'] = nome_res
    itens, hitens = carregar_itens(fonte); rel['areas_parametros_recuperados'] = sorted(aplicar_override(itens, ano)); cad = montar_cadernos(itens)
    h, _ = linhas(fonte, nome_res); m, il = mapa_resultados(h)
    rel['areas_com_respostas_e_notas'] = sorted(m); rel['tem_TP_LINGUA'] = il is not None
    if not m: rel['status'] = 'SEM_RESPOSTAS_OU_NOTAS'; return rel
    st = {a: collections.defaultdict(lambda: collections.Counter()) for a in AREAS}
    amostra = {a: [] for a in AREAS}; maxerr = collections.defaultdict(float)
    acc = Acumulador(cad); n = 0

    def fechar():
        for a, prova, lg, th, nota, tot in acc.calcular():
            s_ = st[a][prova]
            if th is None: s_['sem_caderno'] += tot; continue
            pred = K0[a][0] + K0[a][1] * th; e = np.abs(pred - nota)
            s_['n'] += len(e); s_['ok01'] += int((e < 0.1).sum()); s_['ok1'] += int((e < 1).sum()); maxerr[(a, prova)] = max(maxerr[(a, prova)], float(e.max()))

    for a, prova, lg, resp, nota in participantes(fonte, nome_res):
        if a not in K0 or em_branco(resp): continue
        acc.add(a, prova, lg, resp, nota); n += 1
        if len(amostra[a]) < cap_amostra and random.random() < p_amostra: amostra[a].append((prova, lg, resp, nota))
        if n % lote == 0: fechar()
        if limite and n >= limite: break
    fechar()
    rel['participantes_nao_brancos'] = n
    areas = {}
    for a in AREAS:
        pp = st[a]; tot = sum(c['n'] for c in pp.values())
        if not tot: continue
        reg = {p: c for p, c in pp.items() if c['n'] >= 0.02 * tot and not cad.get((a, p), {}).get('adapt')}
        nr = sum(c['n'] for c in reg.values()); ok1 = sum(c['ok1'] for c in reg.values()); ok01 = sum(c['ok01'] for c in reg.values())
        pct1 = ok1 / nr * 100 if nr else 0
        info = dict(provas_regulares=sorted(reg), n_regulares=nr, pct_dentro_0_1=round(ok01 / nr * 100, 3) if nr else 0, pct_dentro_1=round(pct1, 3),
                    erro_max_regulares=round(max([maxerr[(a, p)] for p in reg] or [0]), 2),
                    por_prova={p: dict(n=c['n'], ok1=c['ok1'], ok01=c['ok01']) for p, c in pp.items()}, constantes=list(K0[a]))
        if pct1 >= 99.9: info['classe'] = 'EXATO'
        else:
            acc2 = Acumulador(cad)
            for prova, lg, resp, nota in amostra[a]:
                if prova in reg: acc2.add(a, prova, lg, resp, nota)
            T, N = [], []
            for a_, prova, lg, th, nota, _ in acc2.calcular():
                if th is None: continue
                T.extend(th); N.extend(nota)
            T, N = np.array(T), np.array(N)
            if len(T) > 200:
                s_, m_ = np.polyfit(T, N, 1)
                for _ in range(3):
                    r = N - (m_ + s_ * T); keep = np.abs(r) < 3 * max(r.std(), 0.05); s_, m_ = np.polyfit(T[keep], N[keep], 1)
                r = N - (m_ + s_ * T); corr = float(np.corrcoef(T, N)[0, 1])
                info['ajuste'] = dict(m=round(float(m_), 3), s=round(float(s_), 3), n=int(len(T)), corr=round(corr, 4), mae=round(float(np.abs(r).mean()), 2),
                                      p90=round(float(np.percentile(np.abs(r), 90)), 1), p95=round(float(np.percentile(np.abs(r), 95)), 1))
                info['classe'] = 'ESTIMADO' if (corr >= 0.94 and np.percentile(np.abs(r), 95) <= 70) else 'NAO_VALIDO'
            else: info['classe'] = 'NAO_VALIDO'
        areas[a] = info
    rel['areas'] = areas; rel['status'] = 'OK'
    # participantes de exemplo (provas regulares) para testar o site contra a nota oficial
    ex = {}
    for a in AREAS:
        regs = set(areas.get(a, {}).get('provas_regulares', []))
        pool_ = [x for x in amostra[a] if x[0] in regs]; random.shuffle(pool_)
        ex[a] = [dict(prova=p_, lingua=lg_, resp=r_, nota=n_) for p_, lg_, r_, n_ in pool_[:400]]
    pathlib.Path(saida, f'amostra_teste_{ano}.json').write_text(json.dumps(ex, ensure_ascii=False), encoding='utf-8')
    return rel


if __name__ == '__main__':
    caminho, ano, saida = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3]); saida.mkdir(parents=True, exist_ok=True)
    rel = processar_ano(caminho, ano, saida)
    (saida / f'relatorio_{ano}.json').write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding='utf-8')
    print(ano, rel.get('status'), rel.get('classificacao'), rel.get('constantes'))
