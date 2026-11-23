"""Sensitivity of R2_5 Donchian H4 to channel lengths (robustness check, not selection)."""
import os, sys, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harness2.py')).read()
pre = src.split('# ---- R2_1 z-score fade')[0]
sys.argv = ['x', 'bars.parquet', sys.argv[1], 'tmp']
exec(pre)
h4 = src.split('# ---- R2_5 Donchian on H4 bars aligned to the trading day')[1].split('# ---- summary')[0]
h4 = h4.split('dn, dg, d2 =')[0]
rows = []
for ent_n, ex_n in [(10, 5), (20, 10), (30, 15), (40, 20), (55, 20)]:
    code = h4.replace('rolling(20).max().shift(1)', f'rolling({ent_n}).max().shift(1)') \
             .replace('rolling(20).min().shift(1)', f'rolling({ent_n}).min().shift(1)') \
             .replace('rolling(10).max().shift(1)', f'rolling({ex_n}).max().shift(1)') \
             .replace('rolling(10).min().shift(1)', f'rolling({ex_n}).min().shift(1)')
    exec(code)
    res = donchian(NORMAL, 0.05, 0.01)
    t = pd.DataFrame(res, columns=['i', 'pnl', 'risk']); t['R'] = t.pnl / t.risk
    t['dev'] = T[t.i.values] < pd.Timestamp('2023-01-01').value // 60_000_000_000
    for per, x in t.groupby('dev'):
        rows.append(dict(entry=ent_n, exit=ex_n, period='DEV' if per else 'SEEN+', n=len(x),
                         R=x.R.mean(), t=x.R.mean() / x.R.std() * np.sqrt(len(x))))
print(pd.DataFrame(rows).round(3).to_string(index=False))
