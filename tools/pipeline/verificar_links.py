"""Reverifica (HEAD) todos os links de links_provas.json: exige HTTP 200 e content-type PDF.
Uso: python -I verificar_links.py  -> imprime resumo por ano e grava links_provas.verificado.json (só os que passaram).
"""
import json, pathlib, urllib.request, concurrent.futures as cf, time

AQUI = pathlib.Path(__file__).parent
d = json.loads((AQUI / 'links_provas.json').read_text(encoding='utf-8'))
UA = {'User-Agent': 'Mozilla/5.0 (verificacao de links publicos)'}


def head(u):
    for t in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method='HEAD'), timeout=30)
            ct = r.headers.get('Content-Type', '')
            tam = int(r.headers.get('Content-Length', 0) or 0)
            return r.status == 200 and 'pdf' in ct.lower() and tam > 100000, r.status, ct, tam
        except urllib.error.HTTPError as e:
            return False, e.code, '', 0
        except Exception:
            time.sleep(2 * (t + 1))
    return False, 0, 'erro de rede', 0


alvos = [(ano, dia, cor, url) for ano, v in d.items() if isinstance(v, dict) for dia, cs in v.get('dias', {}).items() for cor, url in cs.items()]
with cf.ThreadPoolExecutor(4) as ex:
    res = list(ex.map(lambda a: head(a[3]), alvos))
bom = {}; ruim = []
for (ano, dia, cor, url), (ok, st, ct, tam) in zip(alvos, res):
    if ok: bom.setdefault(ano, {'fonte': d[ano].get('fonte'), 'dias': {}})['dias'].setdefault(dia, {})[cor] = url
    else: ruim.append((ano, dia, cor, st, url))
bom['pagina_fallback'] = d.get('pagina_fallback')
(AQUI / 'links_provas.verificado.json').write_text(json.dumps(bom, ensure_ascii=False, indent=1), encoding='utf-8')
print('verificados OK: %d de %d | falharam: %d' % (len(alvos) - len(ruim), len(alvos), len(ruim)))
for a in sorted(k for k in bom if k.isdigit()):
    print(a, bom[a]['fonte'], {dia: sorted(c) for dia, c in bom[a]['dias'].items()})
for r in ruim: print('FALHOU', r)
