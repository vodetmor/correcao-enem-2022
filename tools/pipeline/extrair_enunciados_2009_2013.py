"""Extrai o enunciado (texto) de cada questao dos PDFs oficiais do ENEM 2009-2013 (caderno Azul; 2011: Branco/Cinza).

Uso: python -I extrair_enunciados_2009_2013.py ANO [ANO ...]
Saidas (fora do repo): C:/dev/enem/_work/enunciados/enunciados_{ANO}.json e relatorio_enunciados_{ANO}.json
Adaptado de tools/gerar_enunciados.py (2022). Particularidades por ano:
  2009: texto limpo; alternativas 'A texto' (letra + espaco), 'Questao NN' quebrado em 2 linhas.
  2010: fonte sem ToUnicode (texto deslocado em 29 + glifos Mac Roman) -> decodificado por span;
        alternativas sem letra (a letra e um desenho): detectadas pela linha iniciada por espaco.
  2011-2013: layout igual ao de 2022 ('QUESTAO NN' + 'A<TAB> texto').
"""
import fitz, re, json, sys, io, csv, zipfile, collections, pathlib

RAIZ = pathlib.Path(r"C:\dev\enem\_work")
ZIPS = RAIZ / "zips"
PDFS = RAIZ / "pdfs"
SAIDA = RAIZ / "enunciados"

# ---------------------------------------------------------------- configuracao por ano
# arquivos: (pdf, gabarito_pdf_ou_None, areas, apelido); cores aceitas na escolha do CO_PROVA
CFG = {
    2009: dict(cores=("AZUL",), arqs=[
        ("ENEM_2009_PROVA_DIA_1_AZUL_1.pdf", "ENEM_2009_GAB_DIA_1.pdf", ("CN", "CH"), 0),
        ("ENEM_2009_PROVA_DIA_2_AZUL_7.pdf", "ENEM_2009_GAB_DIA_2.pdf", ("LC", "MT"), 2)]),
    2010: dict(cores=("AZUL",), arqs=[
        ("ENEM_2010_PROVA_GAB_DIA_1_AZUL_1.pdf", None, ("CH", "CN"), {"CH": "85", "CN": "89"}),
        ("ENEM_2010_PROVA_GAB_DIA_2_AZUL_7.pdf", None, ("LC", "MT"), {"LC": "95", "MT": "99"})]),
    2011: dict(cores=("BRANCO", "CINZA", "AZUL"), arqs=[
        ("ENEM_2011_P1_CAD_03_DIA_1_BRANCO_LEDOR.pdf", "ENEM_2011_P1_GAB_03_DIA_1_BRANCO_LEDOR.pdf", ("CH", "CN"), 0),
        ("ENEM_2011_P1_CAD_06_DIA_2_CINZA_LEDOR.pdf", "ENEM_2011_P1_GAB_06_DIA_2_CINZA_LEDOR.pdf", ("LC", "MT"), 0),
        ("ENEM_2011_P2_CAD_03_DIA_1_BRANCO.pdf", "ENEM_2011_P2_GAB_03_DIA_1_BRANCO.pdf", ("CH", "CN"), 0),
        ("ENEM_2011_P2_CAD_06_DIA_2_CINZA.pdf", "ENEM_2011_P2_GAB_06_DIA_2_CINZA.pdf", ("LC", "MT"), 0)]),
    2012: dict(cores=("AZUL",), arqs=[
        ("caderno_enem2012_sab_azul.pdf", "gabarito_dia1_azul.pdf", ("CH", "CN"), 0),
        ("caderno_enem2012_dom_azul.pdf", "gabarito_dia2_azul.pdf", ("LC", "MT"), 0)]),
    2013: dict(cores=("AZUL",), arqs=[
        ("Caderno1_Azul_Sab.pdf", "Gab_Caderno1_Azul_Sab.pdf", ("CH", "CN"), 0),
        ("Caderno7_Azul_Dom.pdf", "Gab_Caderno7_Azul_Dom.pdf", ("LC", "MT"), 0)]),
}


def faixa(ano, area):
    if ano == 2009:
        return {"CN": (1, 45), "CH": (46, 90), "LC": (91, 135), "MT": (136, 180)}[area]
    return {"CH": (1, 45), "CN": (46, 90), "LC": (91, 135), "MT": (136, 180)}[area]


# ---------------------------------------------------------------- itens
def carregar_itens(ano):
    z = zipfile.ZipFile(ZIPS / f"microdados_enem_{ano}.zip")
    nome = [n for n in z.namelist() if n.endswith(f"ITENS_PROVA_{ano}.csv")][0]
    txt = z.read(nome).decode("latin-1")
    return list(csv.DictReader(io.StringIO(txt), delimiter=";"))


# ---------------------------------------------------------------- gabarito (PDF)
def ler_gabarito(path, ano):
    """-> {n: letra | 'ANULADA'} ; 2009 tem 4 cadernos por linha (Azul = coluna 0 no dia 1, 2 no dia 2)."""
    d = fitz.open(path)
    toks = []
    for p in d:
        toks += [t.strip() for t in p.get_text().split("\n") if t.strip()]
    pares = []
    i = 0
    while i < len(toks) - 1:
        if re.fullmatch(r"\d{1,3}", toks[i]) and re.fullmatch(r"[A-E]|Anulado|ANULADO|anulado", toks[i + 1]):
            pares.append((int(toks[i]), toks[i + 1][0].upper() if len(toks[i + 1]) == 1 else "ANULADA")); i += 2
        else:
            i += 1
    return pares


def gab_azul_2009(path, dia):
    pares = ler_gabarito(path, 2009)
    col = 0 if dia == 1 else 2
    out = {}
    for k, (n, l) in enumerate(pares):
        pass
    # os pares vem em grupos de 4 (um por caderno) por linha; descarta cabecalho
    # reagrupa por linha: ler_gabarito devolve sequencia plana
    for k in range(0, len(pares) - 3, 4):
        grupo = pares[k:k + 4]
        if len({g[0] for g in grupo}) == 1:
            out[grupo[col][0]] = grupo[col][1]
    return out


# ---------------------------------------------------------------- decodificacao 2010 (fonte sem ToUnicode)
def _g(c):
    o = ord(c)
    if o == 0x20:
        return " "
    if 0x03 <= o <= 0x61:
        return chr(o + 29)
    if 0x62 <= o <= 0xB2:
        return bytes([o + 0x1E]).decode("mac_roman")
    if 0xB3 <= o <= 0xD5:
        return bytes([o + 0x1F]).decode("mac_roman")
    return c


def decodifica_2010(t):
    return "".join(_g(c) for c in t)


def span_ofuscado(t):
    if re.search(r"[a-z]{3}", t):
        return False  # texto limpo (o ofuscado so tem minuscula como codigo de acento, nunca 3 seguidas)
    if re.search(r"[\x00-\x08\x0b-\x1f]", t):
        return True
    letras = re.findall(r"[A-Za-z]", t)
    if len(letras) >= 2 and re.fullmatch(r"[\x20-\x7e\xa0-\xff]*", t):
        d = decodifica_2010(t)
        if sum(ch.isalpha() for ch in d) >= 0.6 * len(d.replace(" ", "")):
            return True
    return False


# ---------------------------------------------------------------- leitura das paginas
LIXO = [
    re.compile(r"(Caderno|CADERNO)\s*\d+\s*[-–—]\s*[A-Za-zÀ-ú]+\s*[-–—]\s*P[áaÁA][gG][iI][nN][aA]\s*\d+", re.I),
    re.compile(r"^(CN|CH|LC|MT)\s*[-–—]\s*[12]\s*[º°o]\s*dia\b.*$", re.I),
    re.compile(r"^ENEM\s*20\d\d$", re.I),
    re.compile(r"^20\d\d$"),
    re.compile(r"^\*[A-Za-z0-9]{6,}\*$"),
    re.compile(r"^(?:ENEM\s*20\d\d\s*)+$"),
    re.compile(r"^Rascunho$", re.I),
    re.compile(r"^(LINGUAGENS,? C[ÓO]DIGOS E SUAS TECNOLOGIAS|MATEM[ÁA]TICA E SUAS TECNOLOGIAS|CI[ÊE]NCIAS (HUMANAS|DA NATUREZA) E SUAS TECNOLOGIAS)$", re.I),
    re.compile(r"^Quest(õ|o)es de \d+ a \d+.*$", re.I),
]


def eh_lixo(l):
    s = l.strip()
    return any(r.search(s) for r in LIXO)


def paginas(path, ano):
    """-> lista (por pagina) de linhas em ordem de leitura.
    Em 2010 prefixa: \x01 = linha iniciada por espaco (marca de alternativa), \x02 = linha recuada (alternativas)."""
    out = []
    for pg in fitz.open(path):
        W, H = pg.rect.width, pg.rect.height
        blocos = [b for b in pg.get_text("dict")["blocks"] if b["type"] == 0]
        col = ([], [])
        for b in blocos:
            cx = (b["bbox"][0] + b["bbox"][2]) / 2
            col[0 if cx < W / 2 else 1].append(b)
        linhas = []
        for c in col:
            xs = [round(l["bbox"][0]) for b in c for l in b["lines"]
                  if l["spans"] and l["spans"][0]["size"] >= 9 and "Bold" not in l["spans"][0]["font"]
                  and len("".join(s["text"] for s in l["spans"]).strip()) > 20]
            esq = min(xs) if xs else 0
            todas = [l for b in c for l in b["lines"]]
            for l in sorted(todas, key=lambda l: (round(l["bbox"][1] / 3), l["bbox"][0])) if ano == 2010 else                     [l for b in sorted(c, key=lambda b: (round(b["bbox"][1]), b["bbox"][0])) for l in b["lines"]]:
                if True:
                    partes = []
                    for s in l["spans"]:
                        t = s["text"].replace("\x01", "fi").replace("\x02", "fl")
                        if ano == 2010 and not s["font"].lower().startswith("arial-bold") and span_ofuscado(t):
                            t = decodifica_2010(t)
                        partes.append(t)
                    raw = "".join(partes)
                    ini_esp = bool(re.match(r"[ \xa0  \x03]", raw)) if raw.strip() else False
                    t = raw.replace("\xa0", " ").replace(" ", " ").replace("\x03", " ")
                    t = re.sub("([ﬁﬂ]) (?=[a-zà-ú])", r"", t)
                    t = t.replace("ﬁ", "fi").replace("ﬂ", "fl")
                    if not t.strip() or eh_lixo(t):
                        continue
                    pre = ""
                    if ano == 2010:
                        s0 = l["spans"][0]
                        if ini_esp:
                            pre = "\x01"
                        elif s0["size"] >= 9 and "Bold" not in s0["font"] and round(l["bbox"][0]) - esq >= 5:
                            pre = "\x02"
                    linhas.append(pre + t.rstrip())
        out.append(linhas)
    return out


def questoes(path, ano):
    full = "\n".join("\n".join(p) for p in paginas(path, ano))
    partes = re.split(r"(?:^|\n)[\x01\x02]?\s*(?:QUEST[ÃA]O|Quest[ãa]o)\s+(\d{1,3})[ \t]*(?=\n|$)", full)
    q = collections.defaultdict(list)
    for i in range(1, len(partes), 2):
        q[int(partes[i])].append(partes[i + 1].strip("\n"))
    return q


# ---------------------------------------------------------------- montagem do enunciado
def reflow(linhas):
    paras, cur = [], ""
    for l in linhas:
        l = re.sub(r"\s{2,}", " ", l.replace("\t", " ").strip())
        if not l:
            continue
        if not cur:
            cur = l
        elif re.search(r"[.!?:;»”\"…\]]$", cur) and re.match(r"^[A-ZÀ-Ý“\"«\[\(–—]", l):
            paras.append(cur); cur = l
        elif cur.endswith("-"):
            cur += l
        else:
            cur += " " + l
    if cur:
        paras.append(cur)
    return paras


def achar_alts(linhas, ano):
    """-> (linhas_do_enunciado, {letra: [linhas]}). Sequencia A..E mais ao final do bloco."""
    letras = "ABCDE"
    if ano == 2010:
        n = len(linhas)
        i = n
        while i > 0 and linhas[i - 1][:1] in ("\x01", "\x02"):
            i -= 1
        bloco = linhas[i:]
        if not bloco:
            u = linhas[-5:]
            if len(linhas) > 6 and all(re.match(r"[a-zà-ú0-9]", l) for l in u) and not re.search(r"\.\s*$", linhas[-6]):
                return linhas[:-5], {ch: [l] for ch, l in zip("ABCDE", u)}
            return linhas, {}
        marc = [j for j, l in enumerate(bloco) if l.startswith("\x01")]
        quebras = None
        if len(marc) == 5:
            quebras = marc
            if marc[0] > 0:
                i += marc[0]; bloco = linhas[i:]; quebras = [m - marc[0] for m in marc]
        elif len(marc) == 4 and marc[0] > 0:
            quebras = [0] + marc
        if quebras is None:
            cand = [0] + [j for j in range(1, len(bloco)) if re.search(r"[.?!;:)”\"']\s*$", bloco[j - 1])]
            if len(cand) == 5:
                quebras = cand
            elif len(bloco) == 5:
                quebras = list(range(5))
        if quebras is None or len(quebras) != 5:
            # estilo 'recuo pendente': 1a linha de cada alternativa sem recuo, continuacoes recuadas
            livres = [j for j, l in enumerate(linhas) if l[:1] not in ("", "")]
            if len(livres) >= 6 and any(l[:1] == "" for l in linhas[livres[-5]:]):
                st = livres[-5:]
                return linhas[:st[0]], {ch: linhas[st[k]:(st[k + 1] if k < 4 else len(linhas))] for k, ch in enumerate("ABCDE")}
            return linhas[:i], {}
        alts = {}
        for k, ch in enumerate("ABCDE"):
            fim = quebras[k + 1] if k < 4 else len(bloco)
            alts[ch] = bloco[quebras[k]:fim]
        return linhas[:i], alts
    pad = (lambda ch: re.compile(r"^%s\t" % ch)) if ano >= 2011 else (lambda ch: re.compile(r"^%s(?:\s|$)" % ch))
    pos = {}
    lim = len(linhas)
    for ch in reversed(letras):
        r = pad(ch)
        cand = [i for i in range(lim) if r.match(linhas[i])]
        if not cand:
            break
        pos[ch] = cand[-1]
        lim = cand[-1]
    if len(pos) < 5 and ano >= 2011:
        # alternativas de figura/formula: letra sem tabulacao ('A', 'B s = ...'); exige a sequencia A..E completa
        pos2, lim = {}, len(linhas)
        for ch in reversed(letras):
            r = re.compile(r"^%s(?:\s|$)" % ch)
            cand = [i for i in range(lim) if r.match(linhas[i])]
            if not cand:
                break
            pos2[ch] = cand[-1]
            lim = cand[-1]
        if len(pos2) == 5:
            pos = pos2
    if not pos:
        return linhas, {}
    ordem = sorted(pos.items(), key=lambda kv: kv[1])
    alts = {}
    for k, (ch, i) in enumerate(ordem):
        fim = ordem[k + 1][1] if k + 1 < len(ordem) else len(linhas)
        alts[ch] = linhas[i:fim]
    return linhas[:ordem[0][1]], alts


def limpa_alt(ls, ano):
    t = " ".join(l.lstrip("\x01\x02") for l in ls)
    if ano >= 2011:
        t = re.sub(r"^\s*[A-E]\t\s*", "", t)
    elif ano == 2009:
        t = re.sub(r"^\s*[A-E]\s+", "", t, count=1)
    return re.sub(r"\s+", " ", t).strip()


def montar(texto, ano):
    linhas = [l for l in texto.split("\n") if l.strip()]
    stem, alts = achar_alts(linhas, ano)
    stem = [l.lstrip("\x01\x02") for l in stem]
    paras = reflow(stem)
    cmd = paras[-1] if paras else ""
    busca = " ".join(re.sub(r"[“”\"]", "", cmd).split()[:14])
    al = [limpa_alt(alts.get(ch, []), ano) for ch in "ABCDE"]
    if ano == 2009 and any(re.search(r"\s[B-E]\s+(?=[\d⎛-⎩−-])", a) for a in al):
        al = [""] * 5  # alternativas em 2 colunas intercaladas (formulas): nao confiavel
    return {"s": "\n".join(paras), "a": al, "q": busca}


def idioma(t):
    t = " " + t.lower() + " "
    en = len(re.findall(r"\b(the|of|and|is|are|to|in|that|with|for|was|you|it)\b", t))
    es = len(re.findall(r"\b(el|los|las|una|un|es|con|para|que|del|por|se|su|sus|y)\b", t))
    return "en" if en >= es else "es"


# ---------------------------------------------------------------- orquestracao
def processa(ano):
    cfg = CFG[ano]
    itens = carregar_itens(ano)
    cores = cfg["cores"]
    por_prova = collections.defaultdict(list)
    for r in itens:
        if r["TX_COR"].upper().startswith(tuple(c[:5] for c in cores)):
            por_prova[(r["SG_AREA"], r["CO_PROVA"])].append(r)
    rel = {"ano": ano, "arquivos": [], "status": "ok"}
    res = {"CN": {}, "CH": {}, "LC": {}, "MT": {}}
    stats = collections.defaultdict(lambda: dict(extraidas=0, alt5=0, curtos=0, lixo=0, vazias=0, div=[], excl=0, gab_n=0))
    textos_tot = {}
    for pdf, gab, areas, fixo in cfg["arqs"]:
        caminho = PDFS / str(ano) / pdf
        info = {"pdf": pdf, "areas": {}}
        ntexto = sum(len(p.get_text().strip()) for p in fitz.open(caminho))
        if ntexto < 500:
            info["sem_texto"] = True
            rel["arquivos"].append(info); rel["status"] = "sem_texto"
            continue
        qs = questoes(caminho, ano)
        info["questoes_detectadas"] = len(qs)
        gabq = None
        if gab:
            if ano == 2009:
                gabq = gab_azul_2009(PDFS / str(ano) / gab, 1 if "DIA_1" in gab else 2)
            else:
                gabq = dict(ler_gabarito(PDFS / str(ano) / gab, ano))
        for area in areas:
            lo, hi = faixa(ano, area)
            # candidatos de CO_PROVA para a area
            cands = sorted({p for (a, p) in por_prova if a == area}, key=int)
            if not cands:
                info["areas"][area] = {"erro": "sem_co_prova"}; continue
            def pontua(cp):
                if not gabq:
                    return 0
                ok = 0
                for r in por_prova[(area, cp)]:
                    if r.get("TP_LINGUA") in ("0", "1"):
                        continue
                    g = gabq.get(int(r["CO_POSICAO"]))
                    if g and g == r["TX_GABARITO"].strip().upper()[:1]:
                        ok += 1
                return ok
            pontos = {cp: pontua(cp) for cp in cands}
            if isinstance(fixo, dict) and area in fixo:
                melhor = fixo[area]
            elif gabq:
                melhor = max(cands, key=lambda c: (pontos[c], -int(c)))
            else:
                # sem gabarito em PDF: 2010 -> 1a aplicacao (menor CO_PROVA) para o arquivo sem '2'
                melhor = cands[0]
            info["areas"][area] = {"co_prova": melhor, "candidatos_acerto_gab": pontos}
            linhas_item = por_prova[(area, melhor)]
            for r in linhas_item:
                pos = int(r["CO_POSICAO"])
                lg = r.get("TP_LINGUA", "")
                lst = qs.get(pos, [])
                if not lst:
                    stats[area]["vazias"] += 1
                    stats[area]["div"].append(f"q{pos}: nao encontrada no PDF")
                    continue
                if area == "LC" and lg in ("0", "1") and len(lst) > 1:
                    tags = [idioma(t) for t in lst]
                    alvo = "en" if lg == "0" else "es"
                    k = tags.index(alvo) if alvo in tags else int(lg)
                    texto = lst[min(k, len(lst) - 1)]
                else:
                    texto = lst[0]
                co = r["CO_ITEM"]
                if co in res[area]:
                    continue
                if gabq and pos in gabq and not (area == "LC" and lg in ("0", "1")):
                    gi = r["TX_GABARITO"].strip().upper()[:1]
                    if gabq[pos] == "ANULADA":
                        pass
                    elif gabq[pos] != gi:
                        stats[area]["div"].append(f"q{pos} (item {co}): gab PDF={gabq[pos]} itens={gi} -> EXCLUIDA")
                        stats[area]["excl"] += 1
                        continue
                m = montar(texto, ano)
                res[area][co] = m
                st = stats[area]
                st["extraidas"] += 1
                st["alt5"] += all(m["a"])
                st["curtos"] += len(m["s"]) < 60
                _tx = m["s"] + " " + " ".join(m["a"])
                if re.search(r"ENEM\s*20\d\d", _tx, re.I) or re.search(r"P[ÁA]GINA\s*\d|CADERNO\s*\d|\*[A-Z0-9]{5,}\*|[\x00-\x08\x0b-\x1f]", _tx):
                    st["lixo"] += 1
                if gabq and pos in gabq and not (area == "LC" and lg in ("0", "1")):
                    st["gab_n"] += 1
        rel["arquivos"].append(info)
    # resumo
    tot = dict(extraidas=0, alt5=0, curtos=0, lixo=0)
    rel["areas"] = {}
    for a in ("CN", "CH", "LC", "MT"):
        s = stats[a]
        n = max(s["extraidas"], 1)
        rel["areas"][a] = dict(extraidas=s["extraidas"], pct_alt_completas=round(100 * s["alt5"] / n, 1),
                               pct_enunciado_curto=round(100 * s["curtos"] / n, 1), com_lixo=s["lixo"],
                               nao_encontradas=s["vazias"], gab_conferidos=s["gab_n"], gab_divergentes_excluidas=s["excl"],
                               divergencias=s["div"][:40])
        for k in tot:
            tot[k] += s[k]
    n = max(tot["extraidas"], 1)
    rel["total"] = dict(extraidas=tot["extraidas"], pct_alt_completas=round(100 * tot["alt5"] / n, 1),
                        pct_enunciado_curto=round(100 * tot["curtos"] / n, 1), com_lixo=tot["lixo"])
    if rel["status"] == "ok" and rel["total"]["pct_alt_completas"] < 80:
        rel["status"] = "qualidade_baixa"
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"enunciados_{ano}.json").write_text(json.dumps({"ano": ano, "itens": res}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SAIDA / f"relatorio_enunciados_{ano}.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    return rel


def numeracao_impressa(ano):
    """Acrescenta ao relatorio o campo numeracao_impressa (numero impresso no caderno x CO_POSICAO).
    Numero impresso = 'QUESTAO NN' detectado no PDF; casamento com CO_POSICAO confirmado pelo gabarito oficial
    (2009, 2011-2013: 0 divergencias) e por conferencia de conteudo (2010)."""
    rel_p = SAIDA / f"relatorio_enunciados_{ano}.json"
    rel = json.loads(rel_p.read_text(encoding="utf-8"))
    num = {}
    for pdf, gab, areas, fixo in CFG[ano]["arqs"]:
        qs = questoes(PDFS / str(ano) / pdf, ano)
        dia = 1 if "LC" not in areas else 2
        for a in areas:
            if a in num:
                continue
            lo, hi = faixa(ano, a)
            ks = sorted(k for k in qs if lo <= k <= hi)
            num[a] = {"dia": dia, "min": ks[0], "max": ks[-1], "deslocamento_constante": True, "deslocamento": 0}
    rel["numeracao_impressa"] = {a: num[a] for a in ("CN", "CH", "LC", "MT")}
    rel_p.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    return rel["numeracao_impressa"]


if __name__ == "__main__":
    if sys.argv[1] == "--numeracao":
        for a in sys.argv[2:]:
            n = numeracao_impressa(int(a))
            print(a, {k: (v["dia"], v["min"], v["max"]) for k, v in n.items()})
        sys.exit()
    for a in sys.argv[1:]:
        r = processa(int(a))
        print(a, r["status"], json.dumps(r["total"]), {k: (v["extraidas"], v["pct_alt_completas"], v["gab_divergentes_excluidas"]) for k, v in r.get("areas", {}).items()})
