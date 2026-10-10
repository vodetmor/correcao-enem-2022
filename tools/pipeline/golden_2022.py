"""Teste de regressão do pipeline: o 2022 precisa reproduzir as constantes achadas à mão.
Uso: python -I golden_2022.py <pasta_DADOS_2022>
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import enem_pipeline as P

ESPERADO = {'CH': (501.489, 112.310), 'CN': (501.144, 113.102), 'LC': (499.978, 108.086), 'MT': (500.020, 129.646)}
f = P.Fonte(sys.argv[1])
nome = f.achar(r'^(microdados|resultados)')
itens, _ = P.carregar_itens(f); cad = P.montar_cadernos(itens)
reg, pop = P.descobrir_regulares(f, nome, cad)
print('regulares descobertas:', reg)
c = P.ajustar(f, nome, cad, reg)
ok = True
for a, (m, s) in ESPERADO.items():
    got = c[a]; d = max(abs(got['m'] - m), abs(got['s'] - s))
    print(a, 'pipeline m=%.3f s=%.3f | esperado m=%.3f s=%.3f | dif máx=%.3f | MAE ajuste=%s | n=%s' % (got['m'], got['s'], m, s, d, got['mae_ajuste'], got['n_ajuste']))
    ok &= d < 0.05
print('GOLDEN', 'PASSOU' if ok else 'FALHOU')
