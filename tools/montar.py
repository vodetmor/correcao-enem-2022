"""Monta ../index.html a partir de template.html + dados_enem2022.json.

Uso: python -I montar.py   (dentro de tools/)
Para uma nova prova: gere o JSON de dados com gerar_dados.py (+ extrair_habilidades.py e
ajustar_constantes.py), adicione uma entrada em EXAMS no template e inclua o JSON aqui.
"""
import json, pathlib

aqui = pathlib.Path(__file__).parent
t = (aqui / "template.html").read_text(encoding="utf-8")
d = json.loads((aqui / "dados_enem2022.json").read_text(encoding="utf-8"))

f = lambda x, n=3: f"{x:.{n}f}".replace(".", ",")
k = d["k"]
consts = "Valores obtidos: " + "; ".join(
    f"{a} = {f(k[a][0])} + {f(k[a][1])} · θ" for a in ("LC", "CH", "CN", "MT")) + "."
val = ("comparamos o cálculo com as notas oficiais de todos os inscritos presentes da aplicação regular "
       "do microdado do ENEM 2022 (LC 2.457.219, CH 2.454.607, CN 2.321.881 e MT 2.321.858 participantes). "
       "100% ficaram a no máximo 0,1 ponto da nota oficial (a diferença média é o arredondamento da própria nota). "
       "A única exceção é o cartão totalmente em branco, para o qual o INEP atribui 0.")
cadernos = "Azul, Amarelo, Branco e Rosa (dia 1) e Azul, Amarelo, Cinza e Rosa (dia 2)"

html = (t.replace("__DATA__", json.dumps(d, separators=(",", ":"), ensure_ascii=False))
         .replace("{{CONSTS}}", consts).replace("{{VAL}}", val).replace("{{CADERNOS}}", cadernos))
out = aqui.parent / "index.html"
out.write_text(html, encoding="utf-8")
print(out, len(html.encode("utf-8")), "bytes")
