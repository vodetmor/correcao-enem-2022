"""Inspeciona o layout de um ano: arquivos, colunas relevantes, valores distintos de prova/cor/idioma.
Uso: python -I inspecionar.py <zip> [linhas_de_microdados=20000]
"""
import sys, io, re, zipfile, csv, collections


def abrir(zf, padrao):
    for n in zf.namelist():
        if re.search(padrao, n.split('/')[-1], re.I) and n.lower().endswith(('.csv', '.txt')): return n
    return None


def leitor(zf, nome):
    f = io.TextIOWrapper(zf.open(nome), encoding='latin-1', newline='')
    cab = f.readline(); f.seek(0) if f.seekable() else None
    f = io.TextIOWrapper(zf.open(nome), encoding='latin-1', newline='')
    sep = ';' if cab.count(';') >= cab.count(',') else ','
    return csv.DictReader(f, delimiter=sep), sep


def main(caminho, n=20000):
    zf = zipfile.ZipFile(caminho); print('ARQUIVO', caminho)
    it = abrir(zf, r'^itens_prova'); res = abrir(zf, r'^(microdados|resultados)'); part = abrir(zf, r'^participantes')
    print(' itens:', it, '| resultados:', res, '| participantes:', part)
    if it:
        r, sep = leitor(zf, it); rows = list(r)
        print(' ITENS sep=%r colunas=%s' % (sep, list(rows[0].keys())))
        print(' linhas:', len(rows), '| áreas:', collections.Counter(x['SG_AREA'] for x in rows))
        for k in ('TX_COR', 'TP_LINGUA', 'IN_ITEM_ADAPTADO', 'IN_ITEM_ABAN'):
            if k in rows[0]: print(' ', k, dict(collections.Counter(x[k] for x in rows)))
        provas = collections.defaultdict(set)
        for x in rows: provas[x['SG_AREA']].add((x['CO_PROVA'], x.get('TX_COR', '')))
        for a, s in provas.items(): print('  ', a, 'provas(cor):', sorted(s)[:24])
        print(' exemplo de item:', rows[0])
    if res:
        r, sep = leitor(zf, res)
        print(' RESULTADOS sep=%r' % sep)
        cont = collections.Counter(); amostra = []
        for i, row in enumerate(r):
            if i == 0:
                cols = list(row.keys()); print(' n colunas:', len(cols))
                rel = [c for c in cols if re.match(r'(TP_PRESENCA|CO_PROVA|NU_NOTA_(CN|CH|LC|MT)|TX_RESPOSTAS|TX_GABARITO|TP_LINGUA|NU_SEQUENCIAL|NU_INSCRICAO)', c)]
                print(' colunas relevantes:', rel)
            if i >= n: break
            for c in row:
                if c.startswith('CO_PROVA') and row[c]: cont[(c, row[c])] += 1
            if i < 2: amostra.append({c: row[c][:60] for c in row if re.match(r'(TP_PRESENCA|CO_PROVA|NU_NOTA_(CN|CH|LC|MT)|TX_RESPOSTAS|TP_LINGUA|NU_SEQ|NU_INSC)', c)})
        print(' CO_PROVA nas primeiras %d linhas:' % n, dict(sorted(cont.items())[:40]))
        for a in amostra: print(' linha:', a)
    if part:
        r, sep = leitor(zf, part); row = next(iter(r)); print(' PARTICIPANTES colunas:', [c for c in row if not re.match(r'Q\d', c)])


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 20000)
