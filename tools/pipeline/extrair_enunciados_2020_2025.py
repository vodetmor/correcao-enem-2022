"""Extrai enunciados (texto-base, comando, 5 alternativas) do caderno AZUL de cada ano e grava
C:/dev/enem/_work/enunciados/enunciados_{ANO}.json + relatorio_enunciados_{ANO}.json.

Uso: python -I extrair_enunciados_2020_2025.py 2020 2021 ...
Chave estavel = CO_ITEM do ITENS_PROVA. O CO_PROVA azul regular de cada area e escolhido pela
conferencia com o gabarito oficial (PDF) do caderno azul; empate = menor numero.
"""
import sys, re, json, pathlib, collections, zipfile
import fitz
sys.path.insert(0, r'C:\dev\enem\correcao-enem\tools\pipeline')
import enem_pipeline as E

WORK = pathlib.Path(r'C:\dev\enem\_work')
OUT = WORK / 'enunciados'
PDFS = WORK / 'pdfs'
AREA_DIA = {'LC': 1, 'CH': 1, 'CN': 2, 'MT': 2}
WM = re.compile(r'(?:\s*EN[EM][MN]\s*20[\dA-Z]\d)+', re.I)          # marca d'agua ENEM2025ENEM2025...
BARRA = re.compile(r'^\*\d{4,}[A-Z]*\d*\*$')
LINHAJUNK = re.compile(r'^(?:LINGUAGENS, C.DIGOS E SUAS TECNOLOGIAS(?: E REDA..O)?|CI.NCIAS HUMANAS E SUAS TECNOLOGIAS|CI.NCIAS DA NATUREZA E SUAS TECNOLOGIAS'
                       r'|MATEM.TICA E SUAS TECNOLOGIAS|Quest.es de \d+ a \d+.*|(?:LC|CH|CN|MT)\s*[-–]\s*\d.{0,4}dia.*|P.gina\s+\d+)\s*$', re.I)
RODAPE = re.compile(r'CADERNO\s*\d+|P.gina\s+\d+', re.I)
CORTE = re.compile(r'\n\s*(?:REDA[CÇ][AÃ]O\s*$|PROPOSTA DE REDA|RASCUNHO|INSTRU[CÇ][OÕ]ES|FOLHA DE|CART[AÃ]O|AO TERMINAR|[^\n]*\*\d{5,}|Transcreva a sua)', re.M)


# ---------------- gabarito ----------------
def achar_pdf(ano, dia, tipo):
    d = PDFS / str(ano)
    pats = {('cad', 1): ['*P1_CAD_01_DIA_1_AZUL.pdf', f'{ano}_PV_impresso_D1_CD1.pdf'],
            ('cad', 2): ['*P1_CAD_07_DIA_2_AZUL.pdf', f'{ano}_PV_impresso_D2_CD7.pdf'],
            ('gab', 1): ['*P1_GAB_01_DIA_1_AZUL.pdf', f'{ano}_GB_impresso_D1_CD1.pdf'],
            ('gab', 2): ['*P1_GAB_07_DIA_2_AZUL.pdf', f'{ano}_GB_impresso_D2_CD7.pdf']}[(tipo, dia)]
    for p in pats:
        r = list(d.glob(p))
        if r:
            return r[0]
    return None


def ler_gabarito(path):
    """{questao: [valor, ...]} (2 valores nas questoes de idioma 1-5: ingles, espanhol)."""
    if not path:
        return {}
    g, atual = {}, None
    for pg in fitz.open(path):
        for ln in pg.get_text().split('\n'):
            ln = ln.strip()
            if re.fullmatch(r'\d{1,3}', ln):
                atual = int(ln)
                g.setdefault(atual, [])
            elif atual is not None and re.fullmatch(r'[A-E]|anulad[oa]|X', ln, re.I):
                g[atual].append(ln.upper() if len(ln) == 1 else 'X')
    return {k: v for k, v in g.items() if v}


# ---------------- texto do PDF ----------------
TABNL = '\t\n\r'

def _decod(c):
    g = ord(c)
    if 3 <= g <= 97:
        return chr(g + 29)
    if 98 <= g <= 225:
        return bytes([g + 30]).decode('mac_roman', 'replace')
    return ''


def _span_txt(sp):
    t = ''.join(c['c'] for c in sp['chars'])
    if sp['font'].startswith('Arial') and any(ord(c) < 32 and c not in TABNL for c in t):
        return ''.join(_decod(c) for c in t)  # fonte Identity-H sem ToUnicode: gid -> MacRoman/ASCII
    return t


def blocos(pg):
    """Como get_text('blocks'), mas decodifica spans Arial com glifos sem mapeamento Unicode (2023 dia 2)."""
    if sum(1 for c in pg.get_text() if ord(c) < 32 and c not in TABNL) < 5:
        return [b for b in pg.get_text('blocks') if b[6] == 0]
    out = []
    for b in pg.get_text('rawdict')['blocks']:
        if b['type'] != 0:
            continue
        lin = [''.join(_span_txt(sp) for sp in l['spans']) for l in b['lines']]
        txt = '\n'.join(lin) + '\n'
        out.append((b['bbox'][0], b['bbox'][1], b['bbox'][2], b['bbox'][3], txt, 0, 0))
    return out

def paginas(path):
    out = []
    for pg in fitz.open(path):
        W, H = pg.rect.width, pg.rect.height
        bl = blocos(pg)
        keep = []
        for b in bl:
            t = b[4].strip()
            if not t:
                continue
            if (b[1] > H - 45 or b[3] < 30) and RODAPE.search(t):
                continue
            if BARRA.match(t) or (t.upper().count('ENE') >= 3 and len(WM.sub('', t).strip()) < 6) or (t[:2].upper() == 'EN' and t.upper().count('ENE') >= 8):
                continue
            ls = [l for l in b[4].split('\n') if not LINHAJUNK.match(l.strip())]
            if not any(l.strip() for l in ls):
                continue
            keep.append((b[0], b[1], b[2], b[3], '\n'.join(ls)))
        largo = any((b[2] - b[0]) > 0.6 * W and len(b[4]) >= 100 for b in keep)
        if largo:
            ordem = sorted(keep, key=lambda b: (round(b[1]), b[0]))
        else:
            mid = W / 2
            esq = [b for b in keep if (b[0] + b[2]) / 2 < mid]
            dire = [b for b in keep if (b[0] + b[2]) / 2 >= mid]
            ordem = sorted(esq, key=lambda b: (round(b[1]), b[0])) + sorted(dire, key=lambda b: (round(b[1]), b[0]))
        out.append('\n'.join(b[4].strip('\n') for b in ordem))
    return out


QRE = re.compile(r'^[ \t\xa0]*QUEST[ÃA]O[ \t\xa0]+(\d{1,3})[ \t\xa0]*(?:[-–][^\n]*)?$', re.I | re.M)


def questoes(path):
    full = '\n'.join(paginas(path))
    full = re.sub(r'[\x00\x0b-\x1f]', '', full.replace('\xa0', ' '))
    ms = list(QRE.finditer(full))
    q = collections.defaultdict(list)
    for i, m in enumerate(ms):
        fim = ms[i + 1].start() if i + 1 < len(ms) else len(full)
        q[int(m.group(1))].append(full[m.end():fim].strip('\n'))
    return q, len(full)


EN = set('the of and is to that with are was for this which not as on by from it be have has an their'.split())
ES = set('el los las del una es y por con su sus al lo pero más está también esta este hay se un para como'.split())


def idioma(t):
    w = re.findall(r"[a-zA-Záéíóúñ]+", t.lower())
    e = sum(x in EN for x in w)
    s = sum(x in ES for x in w)
    return 0 if e >= s else 1


def reflow(t):
    t = WM.sub(' ', t.replace('\t', ' '))
    lines = [re.sub(r' {2,}', ' ', l.strip()) for l in t.split('\n') if l.strip()]
    paras, cur = [], ''
    for l in lines:
        if not cur:
            cur = l
        elif re.search(r'[.!?:;»”"…\]]$', cur) and re.match(r'^[A-ZÀ-Ý“"«\[\(–—]', l):
            paras.append(cur); cur = l
        elif cur.endswith('-'):
            cur += l
        else:
            cur += ' ' + l
    if cur:
        paras.append(cur)
    return paras


ALT = re.compile(r'^([A-E])(?:[ ]*\t[ ]*|[ ]{2,})(\S.*)?$')
ALT_LONE = re.compile(r'^([A-E])[ ]*()$')


def achar_cadeia(lines, rx):
    marc = [(i, rx.match(l)) for i, l in enumerate(lines)]
    marc = [(i, mm) for i, mm in marc if mm]
    for ia, (i0, m0) in reversed(list(enumerate(marc))):
        if m0.group(1) != 'A':
            continue
        ch, prox = [(i0, 'A')], 'B'
        for (i, mm) in marc[ia + 1:]:
            if mm.group(1) == prox:
                ch.append((i, prox))
                if prox == 'E':
                    break
                prox = chr(ord(prox) + 1)
        if len(ch) == 5:
            return ch
    return None


def montar(texto):
    texto = re.sub(r'(?m)^([A-E])[ ]*\t[ ]*\n\1[ ]*\t', r'\1\t', texto)  # formato 2022 'A\t\nA\t texto'
    texto = re.sub(r'(?m)^([A-E])[ \t]*\n\1[ ]+(?=\S)', r'\1\t', texto)  # formato 2023 dia 2 'A \nA texto'
    m = CORTE.search('\n' + texto)
    if m:
        texto = ('\n' + texto)[:m.start()]
    lines = texto.split('\n')
    cadeia, rx = achar_cadeia(lines, ALT), ALT
    if not cadeia:
        # alternativas com letra isolada (fracoes, expressoes): letra numa linha, conteudo nas seguintes
        class Either:
            @staticmethod
            def match(l):
                return ALT.match(l) or ALT_LONE.match(l)
        cadeia, rx = achar_cadeia(lines, Either), Either
    alts = {k: '' for k in 'ABCDE'}
    if cadeia:
        stem_lines = lines[:cadeia[0][0]]
        for j, (i, k) in enumerate(cadeia):
            fim = cadeia[j + 1][0] if j + 1 < 5 else len(lines)
            first = rx.match(lines[i]).group(2) or ''
            alts[k] = re.sub(r'\s+', ' ', ' '.join([first] + lines[i + 1:fim])).strip()
    else:
        stem_lines = lines
        # fallback: alternativas so figuras; corta depois da ultima linha de comando
        idx = [i for i, l in enumerate(lines) if re.search(r'[?:]\s*$', l.strip()) and len(l.strip()) >= 30]
        if idx:
            stem_lines = lines[:idx[-1] + 1]
    paras = reflow('\n'.join(stem_lines))
    cmd = paras[-1] if paras else ''
    busca = ' '.join(re.sub(r'[“”"]', '', cmd).split()[:14])
    lim = lambda t: re.sub(r'[\x00-\x08]', '', t)
    paras = [lim(x) for x in paras]
    busca = lim(busca)
    return {'s': '\n'.join(paras), 'a': [lim(WM.sub('', alts[k])).strip() for k in 'ABCDE'], 'q': busca}


# ---------------- itens / cadernos ----------------
def escolher_prova(itens, area, gab):
    cand = collections.defaultdict(list)
    for x in itens:
        if x['area'] == area and x['cor'].upper().startswith('AZUL'):
            cand[x['prova']].append(x)
    res = []
    for p, xs in cand.items():
        tot = ok = 0
        for x in xs:
            if x['gab'] not in 'ABCDE' or x['gab'] == '':
                continue
            v = gab.get(x['pos'])
            if not v:
                continue
            idx = 1 if (x['lingua'] == '1' and len(v) > 1) else 0
            tot += 1
            ok += (v[idx] == x['gab'])
        res.append((-(ok / tot if tot else 0), int(p), p, ok, tot, len(xs)))
    res.sort()
    return res


DIGITAL = {2021}  # anos cujo caderno impresso tem texto ilegivel -> usa o caderno digital azul


def carregar_dia(ano, dia):
    """(questoes, n_caracteres, gabarito, nomes dos PDFs). Impresso por padrao; digital em DIGITAL."""
    if ano not in DIGITAL:
        pdf, gpdf = achar_pdf(ano, dia, 'cad'), achar_pdf(ano, dia, 'gab')
        if not pdf:
            raise FileNotFoundError('caderno')
        q, n = questoes(pdf)
        return q, n, ler_gabarito(gpdf), [pdf.name, gpdf.name if gpdf else None]
    d = PDFS / str(ano)
    if dia == 2:
        cad, gab = d / f'ENEM_{ano}_DIGITAL_CAD_07_DIA_2_AZUL.pdf', d / f'ENEM_{ano}_DIGITAL_GAB_07_DIA_2_AZUL.pdf'
        q, n = questoes(cad)
        return q, n, ler_gabarito(gab), [cad.name, gab.name]
    ce, ces = d / f'ENEM_{ano}_DIGITAL_CAD_01_DIA_1_AZUL_INGLES.pdf', d / f'ENEM_{ano}_DIGITAL_CAD_01_DIA_1_AZUL_ESPANHOL.pdf'
    ge, ges = d / f'ENEM_{ano}_DIGITAL_GAB_01_DIA_1_AZUL_INGLES.pdf', d / f'ENEM_{ano}_DIGITAL_GAB_01_DIA_1_AZUL_ESPANHOL.pdf'
    qe, n1 = questoes(ce)
    qs_, n2 = questoes(ces)
    q = {k: list(v) for k, v in qe.items()}
    for k in range(1, 6):
        q[k] = (qe.get(k, [])[:1]) + (qs_.get(k, [])[:1])
    gen, ges_ = ler_gabarito(ge), ler_gabarito(ges)
    gab = {k: list(v) for k, v in gen.items()}
    for k in range(1, 6):
        if k in gen and k in ges_:
            gab[k] = [gen[k][0], ges_[k][0]]
    return q, n1 + n2, gab, [ce.name, ces.name, ge.name, ges.name]


def processar(ano):
    zip_ = WORK / 'zips' / f'microdados_enem_{ano}.zip'
    itens, _ = E.carregar_itens(E.Fonte(zip_))
    rel = {'ano': ano, 'areas': {}, 'divergencias': [], 'obs': []}
    saida = {}
    gabs, qs, nchars = {}, {}, {}
    for dia in (1, 2):
        try:
            qs[dia], nchars[dia], gabs[dia], nomes = carregar_dia(ano, dia)
        except FileNotFoundError as e:
            rel['obs'].append(f'sem PDF dia {dia}: {e}'); continue
        if nchars[dia] < 20000:
            rel['obs'].append(f'sem_texto dia {dia}')
            rel['sem_texto'] = True
        rel[f'pdf_dia{dia}'] = nomes
    if ano in DIGITAL:
        rel['obs'].append('PDF impresso com fontes sem mapeamento Unicode (texto ilegivel); usado o caderno DIGITAL azul (mesmos itens, ordem propria)')
    lixo_re = re.compile(r'P.gina\s+\d|Caderno\s*\d+\s*[-|]|EN[EM]{1,2}\s*20\d\d|\*\d{5,}|RASCUNHO|\bAZUL\b.{0,3}\d', re.I)
    tot = comp = curtos = lixo = 0
    for area in ('LC', 'CH', 'CN', 'MT'):
        dia = AREA_DIA[area]
        if dia not in qs:
            continue
        gab = gabs.get(dia, {})
        esc = escolher_prova(itens, area, gab)
        if not esc:
            rel['obs'].append(f'{area}: sem prova azul'); continue
        _, _, prova, ok, nt, nit = esc[0]
        rel['areas'][area] = {'co_prova': prova, 'gab_confere': f'{ok}/{nt}', 'itens_prova': nit,
                              'candidatas': [(e[2], f'{e[3]}/{e[4]}') for e in esc]}
        if nt and ok / nt < 0.95:
            rel['divergencias'].append(f'{area}: gabarito do PDF vs ITENS so confere {ok}/{nt} (CO_PROVA {prova})')
        xs = [x for x in itens if x['area'] == area and x['prova'] == prova]
        q = qs[dia]
        d = {}
        posq = collections.Counter(x['pos'] for x in xs)
        faltam = []
        for x in sorted(xs, key=lambda x: (x['pos'], x['lingua'])):
            lst = q.get(x['pos'])
            if not lst:
                faltam.append(x['pos']); continue
            if x['lingua'] in ('0', '1') and len(lst) > 1:
                alvo = int(x['lingua'])
                m = [t for t in lst if idioma(t) == alvo]
                texto = max(m, key=len) if m else lst[alvo if alvo < len(lst) else 0]
            else:
                texto = max(lst, key=len)
            it = montar(texto)
            it['_pos'] = x['pos']; it['_lg'] = x['lingua']
            it['_aban'] = x['aban']
            d[x['item']] = it
        if faltam:
            rel['divergencias'].append(f'{area}: questoes sem texto no PDF para posicoes {faltam}')
        base = {'LC': 1, 'CH': 46, 'CN': 91, 'MT': 136}[area]
        extras = sorted(n for n in q if base <= n < base + 45 and n not in posq)
        if extras:
            rel['divergencias'].append(f'{area}: numeros no PDF sem item no ITENS (dia {dia}): {extras[:20]}')
        saida[area] = d
        n = len(d)
        c = sum(1 for v in d.values() if all(v['a']))
        cu = sum(1 for v in d.values() if len(v['s']) < 60)
        lx = sum(1 for v in d.values() if lixo_re.search(v['s'] + ' ' + ' '.join(v['a'])))
        rel['areas'][area].update({'extraidas': n, 'esperado_itens': len(xs), 'alt_completas': c, 'enunciado_curto': cu, 'com_lixo': lx})
        tot += n; comp += c; curtos += cu; lixo += lx
    rel['total'] = tot
    rel['pct_alt_completas'] = round(100 * comp / tot, 1) if tot else 0
    rel['pct_enunciado_curto'] = round(100 * curtos / tot, 1) if tot else 0
    rel['pct_com_lixo'] = round(100 * lixo / tot, 1) if tot else 0
    if rel['pct_alt_completas'] < 80:
        rel['qualidade_baixa'] = True
    # extras para comparacao (nao vao ao JSON final)
    final = {'ano': ano, 'itens': {a: {k: {'s': v['s'], 'a': v['a'], 'q': v['q']} for k, v in d.items()} for a, d in saida.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'enunciados_{ano}.json').write_text(json.dumps(final, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    if ano == 2022:
        comparar_2022(saida, rel)
    (OUT / f'relatorio_enunciados_{ano}.json').write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding='utf-8')
    return rel


def norm(t):
    return re.sub(r'\W+', '', t.lower())


def comparar_2022(saida, rel):
    d = json.loads(pathlib.Path(r'C:\dev\enem\correcao-enem\tools\dados_enem2022.json').read_text(encoding='utf-8'))
    por_pos = {}
    for a, dd in saida.items():
        for k, v in dd.items():
            por_pos[(a, v['_pos'], v['_lg'])] = v
    BASE = {'LC': 1, 'CH': 46, 'CN': 91, 'MT': 136}
    r = {'comparados': 0, 's_igual': 0, 'alt_igual': 0, 'exemplos_dif': []}
    for a in BASE:
        cad = d['cad'][a]['AZUL']
        listas = cad if a == 'LC' else [cad]
        for lg, idx in enumerate(listas):
            for j, k in enumerate(idx):
                ref = d['enun'][a].get(str(k))
                v = por_pos.get((a, BASE[a] + j, str(lg) if a == 'LC' and BASE[a] + j <= 5 else ''))
                if not ref or not v:
                    continue
                r['comparados'] += 1
                if norm(ref['s']) == norm(v['s']):
                    r['s_igual'] += 1
                elif norm(ref['s']) in norm(v['s']):
                    r['s_ref_contido_no_novo'] = r.get('s_ref_contido_no_novo', 0) + 1
                elif len(r['exemplos_dif']) < 5:
                    r['exemplos_dif'].append(f"{a} pos{BASE[a] + j}")
                if [norm(x) for x in ref['a']] == [norm(x) for x in v['a']]:
                    r['alt_igual'] += 1
    rel['comparacao_dados_enem2022'] = r


if __name__ == '__main__':
    for a in [x for x in sys.argv[1:] if x != '--numeracao']:
        r = processar(int(a))
        print(a, 'total', r['total'], 'alt%', r['pct_alt_completas'], 'curto%', r['pct_enunciado_curto'], 'lixo%', r['pct_com_lixo'])
        for k, v in r['areas'].items():
            print('  ', k, {kk: vv for kk, vv in v.items() if kk != 'candidatas'})
        for x in r['divergencias']:
            print('  DIV', x.encode('ascii', 'replace').decode())
        if 'comparacao_dados_enem2022' in r:
            print('  CMP', r['comparacao_dados_enem2022'])


def numeracao_impressa(ano):
    """Acrescenta 'numeracao_impressa' ao relatorio do ano (nao refaz a extracao dos enunciados).
    Numero impresso = numero do cabecalho 'Questao NN' do caderno azul que casou com o item (conferido
    tambem pelo gabarito oficial); deslocamento = impresso - CO_POSICAO."""
    rp = OUT / f'relatorio_enunciados_{ano}.json'
    rel = json.loads(rp.read_text(encoding='utf-8'))
    itens, _ = E.carregar_itens(E.Fonte(WORK / 'zips' / f'microdados_enem_{ano}.zip'))
    qs = {dia: carregar_dia(ano, dia)[0] for dia in (1, 2)}
    out = {}
    for area in ('CN', 'CH', 'LC', 'MT'):
        prova = rel['areas'][area]['co_prova']
        dia = AREA_DIA[area]
        xs = [x for x in itens if x['area'] == area and x['prova'] == prova and x['lingua'] in ('', '0')]
        desl = set()
        for x in xs:
            # numero impresso: a posicao so vale se o cabecalho existe no caderno; senao tenta pos +/- deslocamento
            desl.add(0 if x['pos'] in qs[dia] else None)
        const = desl == {0}
        imp = sorted(x['pos'] for x in xs)
        out[area] = {'dia': dia, 'min': imp[0], 'max': imp[-1], 'n_itens': len(xs),
                     'deslocamento_constante': const, 'deslocamento': 0 if const else None}
    rel['numeracao_impressa'] = out
    rp.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding='utf-8')
    return out


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--numeracao':
    for a in range(2020, 2026):
        n = numeracao_impressa(a)
        print(a, {k: (v['dia'], v['min'], v['max'], v['n_itens'], v['deslocamento_constante'], v['deslocamento']) for k, v in n.items()})
