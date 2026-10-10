# -*- coding: utf-8 -*-
"""Descobre e VERIFICA (HEAD-only) os links do PDF oficial do caderno de prova
(aplicacao regular, impresso) do ENEM 2009-2025 no download.inep.gov.br.
Gera links_provas.json ao lado deste script. Nunca baixa PDF.
Uso: python -I descobrir_links.py
"""
import json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "links_provas.json")
EB = "https://download.inep.gov.br/educacao_basica/enem/provas/{y}/"
PG = "https://download.inep.gov.br/enem/provas_e_gabaritos/"
FALLBACK = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos"

# numero do caderno -> (dia, cor, rotulo de dia da semana usado em nomes antigos)
# layout padrao 2009-2021 (conferido nos nomes dos PDFs dentro dos zips de microdados)
LAYOUT = {1: (1, "AZUL", "sab"), 2: (1, "AMARELA", "sab"), 3: (1, "BRANCA", "sab"), 4: (1, "ROSA", "sab"),
          5: (2, "AMARELA", "dom"), 6: (2, "CINZA", "dom"), 7: (2, "AZUL", "dom"), 8: (2, "ROSA", "dom")}
# 2022-2025: layout de cores conferido por leitura da capa de cada PDF (ver relatorio); sobrescreve se diferente
LAYOUT_NEW = {2022: LAYOUT, 2023: LAYOUT, 2024: LAYOUT, 2025: LAYOUT}
COR_FEM = {"AZUL": "azul", "AMARELA": "amarelo", "BRANCA": "branco", "ROSA": "rosa", "CINZA": "cinza"}


def head(u):
    for i in range(4):
        try:
            r = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, timeout=30) as f:
                return f.status == 200 and "pdf" in (f.headers.get("content-type") or "").lower()
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410):
                return False
            time.sleep(2)
        except Exception:
            time.sleep(2 + i * 2)
    return False


def candidatos(y, n, dia, cor, sem):
    c = COR_FEM[cor]
    pv = "%d_PV_impresso_D%d_CD%d.pdf" % (y, dia, n)
    if y >= 2020:
        return [("padrao_A", PG + pv)]
    base = EB.format(y=y)
    out = []
    if y >= 2014:
        out.append(("padrao_B", base + pv))
    if y <= 2013:
        out.append(("padrao_C", base + "dia%d_caderno%d_%s.pdf" % (dia, n, c)))
        out.append(("padrao_D", base + "caderno_enem%d_%s_%s.pdf" % (y, "sab" if dia == 1 else "dom", c)))
    if y == 2016:
        out.append(("padrao_E", base + "CAD_ENEM_2016_DIA_%d_%02d_%s.pdf" % (dia, n, cor.replace("AMARELA", "AMARELO").replace("BRANCA", "BRANCO"))))
    if y == 2018:
        out.append(("padrao_F", base + "%dDIA_%02d_%s_BAIXA.pdf" % (dia, n, cor.replace("AMARELA", "AMARELO").replace("BRANCA", "BRANCO"))))
    if y == 2019:
        out.append(("padrao_G", base + "caderno_de_questoes_%d_dia_caderno_%d_%s_aplicacao_regular.pdf" % (dia, n, c)))
    return out


def resolve(args):
    y, n = args
    dia, cor, sem = LAYOUT_NEW.get(y, LAYOUT)[n]
    for nome, u in candidatos(y, n, dia, cor, sem):
        if head(u):
            return y, n, dia, cor, nome, u
        time.sleep(0.2)
    return y, n, dia, cor, None, None


def main():
    tarefas = [(y, n) for y in range(2009, 2026) for n in range(1, 9)]
    res = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for y, n, dia, cor, nome, u in ex.map(resolve, tarefas):
            res.setdefault(y, []).append((n, dia, cor, nome, u))
    out = {}
    for y in range(2009, 2026):
        dias, fontes = {}, set()
        for n, dia, cor, nome, u in res[y]:
            if u:
                dias.setdefault(str(dia), {})[cor] = u
                fontes.add(nome)
        out[str(y)] = {"fonte": "+".join(sorted(fontes)) or "nao_encontrado", "dias": dias}
        print(y, out[str(y)]["fonte"], sum(len(v) for v in dias.values()), "/ 8")
    out["pagina_fallback"] = FALLBACK
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
