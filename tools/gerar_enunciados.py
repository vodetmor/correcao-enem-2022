"""Extrai o enunciado de cada questão dos PDFs oficiais (caderno Azul) e grava em dados_enem2022.json['enun'].

Uso (dentro de tools/): python -I gerar_enunciados.py <CAD_DIA1_AZUL.pdf> <CAD_DIA2_AZUL.pdf>
Requer PyMuPDF (pip install pymupdf). O texto das figuras e gráficos não é extraível: só o texto.
Casamento questão x item: posição do caderno Azul (conferido contra o gabarito oficial em PDF).
"""
import fitz, re, json, sys, collections, pathlib

AQUI = pathlib.Path(__file__).parent
BASE = {"LC": 1, "CH": 46, "CN": 91, "MT": 136}


def paginas(path):
    out = []
    for pg in fitz.open(path):
        W, H = pg.rect.width, pg.rect.height
        bl = [b for b in pg.get_text("blocks") if b[6] == 0]
        cols = ([b for b in bl if (b[0] + b[2]) / 2 < W / 2], [b for b in bl if (b[0] + b[2]) / 2 >= W / 2])
        txt = []
        for col in cols:
            for b in sorted(col, key=lambda b: (round(b[1]), b[0])):
                if b[1] < 35 or b[3] > H - 30:
                    continue  # cabeçalho e rodapé
                t = b[4].strip()
                if len(t) < 14 and re.search(r"\*|\d{5,}", t):
                    continue
                txt.append(t)
        out.append("\n".join(txt))
    return out


def questoes(path):
    full = "\n".join(paginas(path))
    parts = re.split(r"\n?\s*QUEST[ÃA]O\s+(\d{2,3})\s*\n", full)
    q = collections.defaultdict(list)
    for i in range(1, len(parts), 2):
        q[int(parts[i])].append(parts[i + 1].strip())
    return q


def reflow(t):
    t = re.sub(r"(?:ENEM\s*2022\s*){2,}", " ", t.replace("\xa0", " ").replace("\t", " "))  # marca d'água
    lines = [re.sub(r" {2,}", " ", l.strip()) for l in t.split("\n")
             if l.strip() and not re.fullmatch(r"(?:ENEM\s*2022\s*)+", l.strip())]
    paras, cur = [], ""
    for l in lines:
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


def montar(texto):
    m = re.search(r"\nA\t\nA\t", "\n" + texto)
    stem_raw, alts_raw = (("\n" + texto)[: m.start()], ("\n" + texto)[m.start():]) if m else (texto, "")
    alts = {k: re.sub(r"\s+", " ", v).strip() for k, v in
            re.findall(r"\n([A-E])\t\n\1\t (.*?)(?=\n[A-E]\t\n[A-E]\t|\Z)", alts_raw, re.S)}
    paras = reflow(stem_raw)
    cmd = paras[-1] if paras else ""
    busca = " ".join(re.sub(r"[“”\"]", "", cmd).split()[:14])
    return {"s": "\n".join(paras), "a": [alts.get(l, "") for l in "ABCDE"], "q": busca}


def main(p1, p2):
    d = json.loads((AQUI / "dados_enem2022.json").read_text(encoding="utf-8"))
    q1, q2 = questoes(p1), questoes(p2)
    enun = {a: {} for a in BASE}
    for a, qq in (("LC", q1), ("CH", q1), ("CN", q2), ("MT", q2)):
        langs = [0, 1] if a == "LC" else [None]
        for lg in langs:
            idx = d["cad"][a]["AZUL"][lg] if a == "LC" else d["cad"][a]["AZUL"]
            for j, k in enumerate(idx):
                n = BASE[a] + j
                lst = qq[n]
                # LC 1-5: primeira ocorrência = inglês, segunda = espanhol
                texto = lst[lg] if (a == "LC" and len(lst) > 1) else lst[0]
                enun[a][str(k)] = montar(texto)
    d["enun"] = enun
    (AQUI / "dados_enem2022.json").write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    tam = len(json.dumps(enun, ensure_ascii=False).encode("utf-8"))
    sem_alt = sum(1 for a in enun for k, v in enun[a].items() if sum(bool(x) for x in v["a"]) < 5)
    print("itens:", sum(len(v) for v in enun.values()), "| bytes enunciados:", tam, "| itens com alternativa sem texto (figura):", sem_alt)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
