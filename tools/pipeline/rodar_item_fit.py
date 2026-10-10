"""Executor paralelo do ajuste de itens: python -I rodar_item_fit.py [anos...] (padrão 2009-2025, 6 em paralelo)."""
import sys, json, time, pathlib, multiprocessing as mp
AQUI = pathlib.Path(__file__).parent


def run(ano):
    sys.path.insert(0, str(AQUI))
    import item_fit as I
    t = time.time(); out = I.item_fit_ano(ano)
    pathlib.Path(f'C:/dev/enem/_work/saida/item_fit_{ano}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    return ano, round(time.time() - t)


if __name__ == '__main__':
    anos = [int(x) for x in sys.argv[1:]] or list(range(2009, 2026))
    with mp.Pool(6) as p:
        for ano, seg in p.imap_unordered(run, anos): print(ano, 'ok', seg, 's', flush=True)
    print('FIM', flush=True)
