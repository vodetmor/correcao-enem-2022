"""Etapa 0 do pipeline: sonda os zips de microdados do INEP SEM baixá-los inteiros.

Lê só o índice de cada zip (diretório central) e o começo dos arquivos de dados, via requisições
parciais (HTTP Range). Responde: tamanho do zip, arquivos presentes e colunas de cada ano.
Uso: python -I probe_inep.py [ano_inicial] [ano_final]   -> grava probe_inep.json ao lado.
"""
import json, struct, sys, zlib, urllib.request, concurrent.futures as cf, pathlib

BASE = "https://download.inep.gov.br/microdados/microdados_enem_{}.zip"
UA = {"User-Agent": "Mozilla/5.0 (probe de metadados; leitura parcial)"}


def req(url, rng=None, method="GET", timeout=60):
    h = dict(UA)
    if rng: h["Range"] = f"bytes={rng[0]}-{rng[1]}"
    r = urllib.request.Request(url, headers=h, method=method)
    return urllib.request.urlopen(r, timeout=timeout)


def tamanho(url):
    with req(url, method="HEAD") as r:
        return int(r.headers["Content-Length"]), r.headers.get("Accept-Ranges", "")


def ler(url, ini, fim):
    with req(url, (ini, fim)) as r:
        return r.read()


def diretorio_central(url, total):
    cauda = ler(url, max(0, total - 70000), total - 1)
    i = cauda.rfind(b"PK\x05\x06")
    if i < 0: raise RuntimeError("EOCD não encontrado")
    n_ent, tam_cd, off_cd = struct.unpack("<HII", cauda[i + 10:i + 20])
    if off_cd == 0xFFFFFFFF or n_ent == 0xFFFF:  # zip64
        j = cauda.rfind(b"PK\x06\x07")
        off64 = struct.unpack("<Q", cauda[j + 8:j + 16])[0]
        reg = ler(url, off64, off64 + 55)
        n_ent, tam_cd, off_cd = struct.unpack("<QQQ", reg[32:56])
    cd = ler(url, off_cd, off_cd + tam_cd - 1)
    ents, p = [], 0
    while p + 46 <= len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        met, = struct.unpack("<H", cd[p + 10:p + 12])
        csz, usz = struct.unpack("<II", cd[p + 20:p + 28])
        nl, el, cl = struct.unpack("<HHH", cd[p + 28:p + 34])
        off, = struct.unpack("<I", cd[p + 42:p + 46])
        nome = cd[p + 46:p + 46 + nl].decode("cp437", "replace")
        ex = cd[p + 46 + nl:p + 46 + nl + el]
        q = 0
        while q + 4 <= len(ex):
            hid, hs = struct.unpack("<HH", ex[q:q + 4])
            if hid == 1:  # zip64 extra
                v = list(struct.unpack("<" + "Q" * (hs // 8), ex[q + 4:q + 4 + hs]))
                if usz == 0xFFFFFFFF: usz = v.pop(0)
                if csz == 0xFFFFFFFF: csz = v.pop(0)
                if off == 0xFFFFFFFF and v: off = v.pop(0)
            q += 4 + hs
        ents.append({"nome": nome, "comp": csz, "tam": usz, "off": off, "met": met})
        p += 46 + nl + el + cl
    return ents


def cabecalho(url, e, linhas=2, quanto=48000):
    """Primeiras linhas de um arquivo de texto dentro do zip (deflate ou stored), por Range."""
    lh = ler(url, e["off"], e["off"] + 29)
    nl, el = struct.unpack("<HH", lh[26:30])
    ini = e["off"] + 30 + nl + el
    raw = ler(url, ini, min(ini + quanto, ini + e["comp"] - 1))
    txt = zlib.decompressobj(-15).decompress(raw) if e["met"] == 8 else raw
    return txt.decode("latin-1", "replace").splitlines()[:linhas]


def sondar(ano):
    url = BASE.format(ano)
    out = {"ano": ano, "url": url}
    try:
        total, ar = tamanho(url)
        out.update(zip_bytes=total, ranges=ar)
        ents = diretorio_central(url, total)
        out["n_arquivos"] = len(ents)
        out["arquivos"] = [{"nome": e["nome"], "mb": round(e["tam"] / 1e6, 1)} for e in ents if e["tam"] > 0]
        txts = [e for e in ents if e["nome"].lower().endswith((".csv", ".txt")) and e["tam"] > 50000]
        cab = {}
        for e in sorted(txts, key=lambda e: -e["tam"])[:6]:
            try: cab[e["nome"]] = cabecalho(url, e)
            except Exception as x: cab[e["nome"]] = [f"erro: {x}"]
        out["cabecalhos"] = cab
    except Exception as x:
        out["erro"] = str(x)
    return out


if __name__ == "__main__":
    a0 = int(sys.argv[1]) if len(sys.argv) > 1 else 1998
    a1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(sondar, range(a0, a1 + 1)))
    pathlib.Path(__file__).with_name("probe_inep.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in res:
        print(r["ano"], "ERRO " + r["erro"] if "erro" in r else f'{r["zip_bytes"]/1e9:.2f} GB | {r["n_arquivos"]} arquivos | ranges={r["ranges"]}')
