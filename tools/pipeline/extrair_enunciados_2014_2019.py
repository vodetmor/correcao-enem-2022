"""Extrai enunciados (texto-base + comando + 5 alternativas) dos cadernos AZUL de 2014 a 2019 (PyMuPDF).

Uso: python -I extrair_enunciados_2014_2019.py ANO [ANO ...]
Saidas: C:/dev/enem/_work/enunciados/enunciados_{ANO}.json e relatorio_enunciados_{ANO}.json

Particularidades tratadas:
- fontes sem ToUnicode (2014, 2015, 2016, 2018): trechos com glifos "deslocados" (gid = codigo do caractere);
  decodificados por tabela (ASCII = gid + 29; acentos pela ordem Mac Roman do Arial).
- letra da alternativa vem numa fonte propria (BundesbahnPiStd), usada como marcador.
- casamento questao -> CO_ITEM pela ordem (CO_POSICAO) do caderno AZUL regular; conferido com o gabarito oficial.
"""
import sys, re, json, glob, os, collections, pathlib
import fitz

sys.path.insert(0, r"C:\dev\enem\correcao-enem\tools\pipeline")
import enem_pipeline as P

ZIPS = "C:/dev/enem/_work/zips"
PDFS = "C:/dev/enem/_work/pdfs"
OUT = "C:/dev/enem/_work/enunciados"

# area -> numero da primeira questao no caderno
BASES = {
    2014: {"CH": 1, "CN": 46, "LC": 91, "MT": 136},
    2015: {"CH": 1, "CN": 46, "LC": 91, "MT": 136},
    2016: {"CH": 1, "CN": 46, "LC": 91, "MT": 136},  # 2016: dia 1 = CH+CN (ITENS tem CO_POSICAO rotacionado)
}
for _a in (2017, 2018, 2019):
    BASES[_a] = {"LC": 1, "CH": 46, "CN": 91, "MT": 136}
DIA1 = {2014: ("CH", "CN"), 2015: ("CH", "CN"), 2016: ("CH", "CN")}
for _a in (2017, 2018, 2019):
    DIA1[_a] = ("LC", "CH")

# ---------------------------------------------------------------- decodificacao de glifos deslocados
GID = {}
for i, ch in enumerate("ÄÅÇÉÑÖÜáàâäãåçéèêëíìîïñóòôöõúùûü"):
    GID[98 + i] = ch
GID.update({131: "°", 135: "•", 158: "º", 172: "À", 173: "Ã", 174: "Õ", 177: "–", 178: "—", 179: "“", 180: "”",
            181: "‘", 182: "’", 191: "fi", 192: "fl", 198: "Â", 199: "Ê", 200: "Á", 201: "Ë", 203: "Í", 207: "Ó",
            208: "Ô", 211: "Ú", 213: "Ù"})


def decodifica(t):
    out = []
    for c in t:
        o = ord(c)
        if o == 32:  # espaco de justificacao dentro do trecho deslocado (gid 32 seria "=", raro no texto corrido)
            out.append(" ")
        elif 3 <= o <= 97:
            out.append(chr(o + 29))
        elif o in GID:
            out.append(GID[o])
        else:
            out.append(c)
    return "".join(out)


def span_garbled(t):
    return any(ord(c) < 32 and c not in "\t\n\r" for c in t)


# ---------------------------------------------------------------- leitura de paginas
RUIDO = re.compile(r"^\s*(\*[A-Z0-9]{4,}\*|(CH|CN|LC|MT)\s*-\s*\d.\s*dia.*|ENEM\s*20\d\d|20\d\d)\s*$", re.I)
CABEC = re.compile(r"(Caderno\s+\d+\s*-\s*(AZUL|AMARELO|BRANCO|ROSA|CINZA)\b.*P[áa]gina|^\s*P[áa]gina\s+\d+\s*$)", re.I)
AREA_TIT = re.compile(r"^\s*((CI[ÊE]NCIAS|LINGUAGENS|MATEM[ÁA]TICA).{0,40}TECNOLOGIAS|QUEST[ÕO]ES\s+DE\s+\d+\s+A\s+\d+.*|"
                      r"Quest[õo]es\s+de\s+\d+\s+a\s+\d+.*)\s*$", re.I)


def linhas_pagina(pg):
    W, H = pg.rect.width, pg.rect.height
    blocos = [b for b in pg.get_text("dict")["blocks"] if b["type"] == 0]
    cols = ([b for b in blocos if (b["bbox"][0] + b["bbox"][2]) / 2 < W / 2],
            [b for b in blocos if (b["bbox"][0] + b["bbox"][2]) / 2 >= W / 2])
    out = []
    for col in cols:
        for b in sorted(col, key=lambda b: (round(b["bbox"][1]), b["bbox"][0])):
            if b["bbox"][1] < 50 or b["bbox"][3] > H - 28:
                continue
            for l in b["lines"]:
                partes = []
                for s in l["spans"]:
                    t = s["text"]
                    if "Bundesbahn" in s["font"] and t.strip() in list("ABCDE"):
                        partes.append("\x01" + t.strip() + "\x01 ")
                        continue
                    if span_garbled(t):
                        t = decodifica(t)
                    partes.append(t)
                txt = "".join(partes).replace("\xa0", " ").replace("\t", " ")
                txt = re.sub(r"[ ]{2,}", " ", txt).strip()
                if not txt or RUIDO.match(txt) or CABEC.search(txt) or AREA_TIT.match(txt):
                    continue
                out.append(txt)
    return out


MARC = re.compile(r"^QUEST[ÃA]O\s+(\d{1,3})\s*$", re.I)


def questoes(path):
    """-> {numero: [lista de ocorrencias (lista de linhas)]}, na ordem do caderno"""
    q = collections.defaultdict(list)
    atual = None
    for pg in fitz.open(path):
        for ln in linhas_pagina(pg):
            m = MARC.match(ln)
            if m:
                atual = []
                q[int(m.group(1))].append(atual)
            elif atual is not None:
                atual.append(ln)
    return q


# ---------------------------------------------------------------- montagem do enunciado
LIXO_FIM = re.compile(r"^(RASCUNHO|LEIA ATENTAMENTE|INSTRU[ÇC][ÕO]ES)", re.I)


def reflow(linhas):
    paras, cur = [], ""
    for l in linhas:
        if not cur:
            cur = l
        elif l.startswith("•"):
            paras.append(cur); cur = l
        elif re.search(r"[.!?:;»”\"…\]]$", cur) and re.match(r"^[A-ZÀ-Ý“\"«\[\(–—]", l):
            paras.append(cur); cur = l
        elif cur.endswith("-") and l.startswith("-"):
            cur += l[1:]
        elif cur.endswith("-"):
            cur += l
        else:
            cur += " " + l
    if cur:
        paras.append(cur)
    return paras


def montar(linhas):
    for i, l in enumerate(linhas):
        if LIXO_FIM.match(l):
            linhas = linhas[:i]
            break
    # acha a ultima sequencia A,B,C,D,E de marcadores
    idx = {k: [i for i, l in enumerate(linhas) if l.startswith("\x01" + k + "\x01")] for k in "ABCDE"}
    pos = None
    for a in reversed(idx["A"]):
        seq, ult = [a], a
        for k in "BCDE":
            nx = [i for i in idx[k] if i > ult]
            if not nx:
                break
            ult = nx[0]; seq.append(ult)
        if len(seq) == 5:
            pos = seq; break
    if pos is None:
        stem, alts = linhas, [""] * 5
    else:
        stem = linhas[:pos[0]]
        alts = []
        for j in range(5):
            fim = pos[j + 1] if j < 4 else len(linhas)
            seg = linhas[pos[j]:fim]
            seg[0] = re.sub(r"^\x01[A-E]\x01 ?", "", seg[0])
            alts.append(re.sub(r"\s+", " ", " ".join(seg)).strip())
            alts[-1] = alts[-1].replace("\x01", "")
    stem = [re.sub(r"\x01[A-E]\x01 ?", "", l) for l in stem]
    paras = reflow(stem)
    cmd = paras[-1] if paras else ""
    busca = " ".join(re.sub(r"[“”\"]", "", cmd).split()[:14])
    return {"s": "\n".join(paras), "a": alts, "q": busca}


ES = set("el los las del una que por para con es se su sus como más pero también muy fue sobre entre".split())
EN = set("the of and to in is that for with as was are by this from or which be it his her they their".split())


def lingua(txt):
    w = re.findall(r"[a-záéíóúñ]+", txt.lower())
    return "es" if sum(x in ES for x in w) > sum(x in EN for x in w) else "en"


# ---------------------------------------------------------------- gabarito
def gabarito(path):
    toks = []
    for pg in fitz.open(path):
        toks += [t.strip() for t in pg.get_text().split("\n") if t.strip()]
    g, i = {}, 0
    while i < len(toks):
        if re.fullmatch(r"\d{1,3}", toks[i]):
            n = int(toks[i]); j = i + 1; v = []
            while j < len(toks) and len(v) < 2 and re.fullmatch(r"[A-E]|anulad[oa]|\*", toks[j], re.I):
                v.append(toks[j].upper()); j += 1
            if v and 1 <= n <= 180:
                g.setdefault(n, v)
            i = j
        else:
            i += 1
    return g


# ---------------------------------------------------------------- por ano
def achar(ano, dia, gab):
    fs = glob.glob(f"{PDFS}/{ano}/*.pdf")
    ok = []
    for f in fs:
        b = os.path.basename(f).upper()
        is_gab = "GAB" in b
        d1 = ("DIA_1" in b) or ("SAB" in b)
        d2 = ("DIA_2" in b) or ("DOM" in b)
        if is_gab == gab and ((dia == 1 and d1) or (dia == 2 and d2)):
            ok.append(f)
    return ok[0] if ok else None


def processar(ano):
    it, _ = P.carregar_itens(P.Fonte(f"{ZIPS}/microdados_enem_{ano}.zip"))
    cad = P.montar_cadernos(it)
    bases = BASES[ano]
    rel = {"ano": ano, "areas": {}, "avisos": []}
    itens = {a: {} for a in bases}
    pdf_q = {1: questoes(achar(ano, 1, False)), 2: questoes(achar(ano, 2, False))}
    gab = {1: gabarito(achar(ano, 1, True)), 2: gabarito(achar(ano, 2, True))}
    for area, base in bases.items():
        dia = 1 if area in DIA1[ano] else 2
        qq, gg = pdf_q[dia], gab[dia]
        # candidatos azul (menor CO_PROVA primeiro); escolhe o de menos divergencia no gabarito
        cands = sorted([(int(p), c) for (a, p), c in cad.items() if a == area and c["cor"].lower() == "azul"], key=lambda x: x[0])
        melhor = None
        for prova, c in cands:
            diverg, ocorr = [], collections.Counter()
            comp_n = 0
            res = {}
            for lg, lst in c["langs"].items():
                for j, x in enumerate(lst):
                    n = base + j
                    oc = qq.get(n, [])
                    if area == "LC" and j < 5:
                        k = 0 if lg == "0" else 1
                        if len(oc) < 2:
                            k = 0
                        sel = oc[k] if len(oc) > k else None
                        gcol = k if len(gg.get(n, [])) > 1 else 0
                    else:
                        sel = oc[0] if oc else None
                        gcol = 0
                    res[(lg, j)] = (n, x, sel, gcol)
                    gl = gg.get(n)
                    if gl is not None and gcol < len(gl):
                        esp = gl[gcol]
                        comp_n += 1
                        if esp[:1] in "ABCDE" and len(esp) == 1 and x["gab"] and esp != x["gab"]:
                            diverg.append((n, esp, x["gab"], x["aban"]))
            if melhor is None or len(diverg) < len(melhor[2]):
                melhor = (prova, res, diverg, c, comp_n)
        prova, res, diverg, c, comp_n = melhor
        rel["areas"][area] = {"co_prova_azul": prova, "candidatas": [p for p, _ in cands]}
        n_ext = 0
        trocas = 0
        for (lg, j), (n, x, sel, gcol) in sorted(res.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if sel is None:
                rel["avisos"].append(f"{area} questao {n} nao encontrada no PDF")
                continue
            m = montar(sel)
            if area == "LC" and j < 5:  # confere idioma do texto
                esperado = "en" if lg == "0" else "es"
                if lingua(m["s"]) != esperado:
                    oc = qq[n]
                    outro = oc[1 - (0 if lg == "0" else 1)] if len(oc) > 1 else None
                    if outro is not None and lingua(montar(outro)["s"]) == esperado:
                        m = montar(outro); trocas += 1
                        rel["avisos"].append(f"LC q{n} idioma {esperado} corrigido por troca de ocorrencia")
            itens[area][x["item"]] = m
            n_ext += 1
        # numeros extraidos no PDF dentro da faixa da area
        faixa = range(base, base + 45)
        rel["areas"][area].update({
            "questoes_no_pdf": sum(1 for n in faixa if n in qq),
            "itens_gravados": len(itens[area]),
            "divergencias_gabarito": [{"q": a, "pdf": b, "itens": cc, "abandonado": d} for a, b, cc, d in melhor[2]],
            "trocas_idioma": trocas, "comparados_gabarito": comp_n,
        })
        # conferencia posicao: CO_POSICAO do ITENS vs numero da questao
        dp = 0
        for (lg, j), (n, x, sel, gcol) in res.items():
            if ano != 2017 and x["pos"] != n:
                dp += 1
        rel["areas"][area]["divergencias_posicao"] = dp
    # pos-passo: palavras MAIUSCULAS isoladas que sao glifos deslocados sem caractere de controle (ex.: JRVSHO = gospel)
    voc = collections.Counter(w for a in itens for v in itens[a].values()
                              for w in re.findall(r"[a-zà-ú]{4,}", v["s"] + " " + " ".join(v["a"])))

    def conserta(t):
        def sub(m):
            w = m.group(0)
            if voc[w.lower()] == 0:
                d = decodifica(w).lower()
                if d != w.lower() and voc[d] >= 2:
                    return decodifica(w)
            return w
        return re.sub(r"[A-Z]{4,}", sub, t)
    nconserto = 0
    for a in itens:
        for v in itens[a].values():
            novo = conserta(v["s"]); nconserto += novo != v["s"]; v["s"] = novo
            v["a"] = [conserta(x) for x in v["a"]]
    rel["palavras_deslocadas_corrigidas_pos"] = nconserto
    # qualidade
    todos = [(a, k, v) for a in itens for k, v in itens[a].items()]
    N = len(todos)
    comp = sum(1 for _, _, v in todos if all(v["a"]))
    curto = sum(1 for _, _, v in todos if len(v["s"]) < 60)
    sujo_re = re.compile(r"ENEM\s*20\d\d|Caderno\s+\d|P[áa]gina\s+\d|\*[A-Z0-9]{5,}\*|[\x00-\x08\x0b-\x1f]|\x01")
    sujo = sum(1 for _, _, v in todos if sujo_re.search(v["s"] + " ".join(v["a"])))
    garb = sum(1 for _, _, v in todos if re.search(r"\b[A-Z]{3,}[a-z]?[A-Z]{2,}\b", v["s"] + " ".join(v["a"]))
               and not re.search(r"[a-z]{3,}", v["s"]))
    rel["total"] = N
    rel["por_area"] = {a: len(itens[a]) for a in itens}
    rel["pct_alternativas_completas"] = round(100 * comp / N, 1) if N else 0
    rel["pct_enunciado_curto_lt60"] = round(100 * curto / N, 1) if N else 0
    rel["pct_com_lixo"] = round(100 * sujo / N, 1) if N else 0
    rel["qualidade_baixa"] = bool(N == 0 or comp / N < 0.8)
    rel["divergencias_gabarito_total"] = sum(len(v["divergencias_gabarito"]) for v in rel["areas"].values())
    os.makedirs(OUT, exist_ok=True)
    pathlib.Path(f"{OUT}/enunciados_{ano}.json").write_text(
        json.dumps({"ano": ano, "itens": itens}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pathlib.Path(f"{OUT}/relatorio_enunciados_{ano}.json").write_text(
        json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(ano, "total", N, "alt_completas %", rel["pct_alternativas_completas"], "curtos %", rel["pct_enunciado_curto_lt60"],
          "lixo %", rel["pct_com_lixo"], "div_gab", rel["divergencias_gabarito_total"], "avisos", len(rel["avisos"]))


def numeracao(ano):
    """Acrescenta 'numeracao_impressa' ao relatorio (nao refaz a extracao). Numero impresso = base + indice na ordem do caderno."""
    rp = pathlib.Path(f"{OUT}/relatorio_enunciados_{ano}.json")
    rel = json.loads(rp.read_text(encoding="utf-8"))
    it, _ = P.carregar_itens(P.Fonte(f"{ZIPS}/microdados_enem_{ano}.zip"))
    cad = P.montar_cadernos(it)
    res = {}
    for area, base in BASES[ano].items():
        prova = str(rel["areas"][area]["co_prova_azul"])
        langs = cad[(area, prova)]["langs"]
        lst = langs["0"] if area == "LC" else langs[""]
        desl = {(base + j) - x["pos"] for j, x in enumerate(lst)}
        const = len(desl) == 1
        res[area] = {"dia": 1 if area in DIA1[ano] else 2, "min": base, "max": base + len(lst) - 1,
                     "deslocamento_constante": const, "deslocamento": desl.pop() if const else None}
    rel["numeracao_impressa"] = res
    rp.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    if sys.argv[1] == "--numeracao":
        for a in sys.argv[2:]:
            r = numeracao(int(a))
            print(a, {k: (v["dia"], f'{v["min"]}-{v["max"]}', v["deslocamento_constante"], v["deslocamento"]) for k, v in r.items()})
    else:
        for a in sys.argv[1:]:
            processar(int(a))
