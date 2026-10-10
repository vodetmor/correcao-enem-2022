"""Etapa 1 do pipeline: baixa em paralelo os zips de microdados do INEP, com retomada e verificação de tamanho.

Uso: python -I baixar.py <pasta_destino> [ano_inicial] [ano_final] [paralelismo]
Os zips ficam FORA do repositório. Depois de processados, podem ser apagados (ver processar.py).
"""
import sys, time, pathlib, threading, concurrent.futures as cf, urllib.request, urllib.error

BASE = "https://download.inep.gov.br/microdados/microdados_enem_{}.zip"
UA = {"User-Agent": "Mozilla/5.0 (download de microdados publicos do INEP)"}
lock = threading.Lock()
feito = {}


def log(msg):
    with lock:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


def tamanho_remoto(url):
    r = urllib.request.Request(url, headers=UA, method="HEAD")
    with urllib.request.urlopen(r, timeout=60) as x:
        return int(x.headers["Content-Length"])


def baixar(ano, destino, tentativas=8):
    url = BASE.format(ano); arq = destino / f"microdados_enem_{ano}.zip"
    for t in range(1, tentativas + 1):
        try:
            total = tamanho_remoto(url)
            ja = arq.stat().st_size if arq.exists() else 0
            if ja == total:
                log(f"{ano}: já completo ({total/1e6:.0f} MB)"); feito[ano] = total; return True
            if ja > total: arq.unlink(); ja = 0
            h = dict(UA)
            if ja: h["Range"] = f"bytes={ja}-"
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=90) as r, open(arq, "ab" if ja else "wb") as f:
                ult = time.time(); lido = ja
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b); lido += len(b)
                    if time.time() - ult > 20:
                        log(f"{ano}: {lido/total*100:5.1f}% ({lido/1e6:.0f}/{total/1e6:.0f} MB)"); ult = time.time()
            if arq.stat().st_size == total:
                log(f"{ano}: OK {total/1e6:.0f} MB"); feito[ano] = total; return True
            log(f"{ano}: tamanho divergente, nova tentativa ({t})")
        except Exception as e:
            log(f"{ano}: erro '{e}', tentativa {t}/{tentativas}")
            time.sleep(min(60, 5 * t))
    log(f"{ano}: FALHOU"); return False


if __name__ == "__main__":
    dest = pathlib.Path(sys.argv[1]); dest.mkdir(parents=True, exist_ok=True)
    a0 = int(sys.argv[2]) if len(sys.argv) > 2 else 2009
    a1 = int(sys.argv[3]) if len(sys.argv) > 3 else 2025
    par = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    anos = list(range(a0, a1 + 1))
    log(f"baixando {len(anos)} anos ({a0}-{a1}) com {par} em paralelo para {dest}")
    with cf.ThreadPoolExecutor(par) as ex:
        ok = list(ex.map(lambda a: baixar(a, dest), anos))
    falhas = [a for a, o in zip(anos, ok) if not o]
    log(f"FIM: {sum(ok)}/{len(anos)} completos | total {sum(feito.values())/1e9:.2f} GB | falhas: {falhas or 'nenhuma'}")
