"""Round-2 harness. See REGISTRATION_round2.md (fixed before running).
Same cost/execution model as harness.py (round 1)."""
import sys

import numpy as np
import pandas as pd

BARS, CAL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

df = pd.read_parquet(BARS)
utc = df["utc"]
ny = utc.dt.tz_convert("America/New_York")
be = utc.dt.tz_convert("Europe/Berlin")
T = utc.values.astype("datetime64[m]").astype(np.int64)
O, H, L, C = (df[k].to_numpy(float) for k in "ohlc")
NYMIN = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
BEMIN = (be.dt.hour * 60 + be.dt.minute).to_numpy()
BEDATE = be.dt.date.to_numpy()
DKEY = (ny + pd.Timedelta(hours=7)).dt.date.to_numpy()  # trading day, 17:00 NY cut
N = len(df)

NORMAL = dict(spread=0.30, slip=0.05, comm=0.07)
ZERO = dict(spread=0.0, slip=0.0, comm=0.0)


def scale(cost, k):
    return {a: b * k for a, b in cost.items()}


def sim(i, d, sl, tp, lim, cost):
    """Returns (pnl_per_oz, risk_per_oz, exit_index) or None."""
    sp, sl_, cm = cost["spread"], cost["slip"], cost["comm"]
    lim = min(lim, N - 1)
    if i >= lim:
        return None
    if d == 1:
        entry = O[i] + sp + sl_
        risk = entry - sl
        if risk <= 0 or tp <= entry:
            return None
        for j in range(i, lim):
            if L[j] <= sl:
                return min(O[j], sl) - sl_ - entry - cm, risk, j
            if H[j] >= tp:
                return tp - entry - cm, risk, j
        return O[lim] - sl_ - entry - cm, risk, lim
    entry = O[i] - sl_
    risk = sl - entry
    if risk <= 0 or tp >= entry:
        return None
    for j in range(i, lim):
        if H[j] + sp >= sl:
            return entry - (max(O[j] + sp, sl) + sl_) - cm, risk, j
        if L[j] + sp <= tp:
            return entry - tp - cm, risk, j
    return entry - (O[lim] + sp + sl_) - cm, risk, lim


trades = []


def record(hyp, i, d, sl, tp, lim, cost=NORMAL, risk_override=None):
    r = sim(i, d, sl, tp, lim, cost)
    g = sim(i, d, sl, tp, lim, ZERO)
    x2 = sim(i, d, sl, tp, lim, scale(cost, 2))
    if r is None or g is None or x2 is None:
        return None
    risk = risk_override or r[1]
    trades.append(dict(hyp=hyp, t=T[i], net=r[0], gross=g[0], x2=x2[0], risk=risk))
    return r[2]


def groups_of(keys):
    return {k: np.asarray(v) for k, v in pd.Series(range(N)).groupby(keys).indices.items()}


def first_at_or_after(g, mins, m):
    k = np.searchsorted(mins[g], m)
    return g[k] if k < len(g) else None


be_groups = groups_of(BEDATE)
d_groups = groups_of(DKEY)

# ---- daily bars (17:00 NY cut) with ATR14 of each completed day
dd = pd.DataFrame({"k": DKEY, "o": O, "h": H, "l": L, "c": C, "i": np.arange(N)})
D = dd.groupby("k").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                        n=("i", "size"))
D = D[D["n"] >= 300].copy()
pc = D["c"].shift(1)
trd = np.maximum(D["h"] - D["l"], np.maximum((D["h"] - pc).abs(), (D["l"] - pc).abs()))
D["atr14"] = trd.rolling(14).mean()
Dprev = D.shift(1)  # values of the previous completed trading day, indexed by today
gapday = pd.Series(pd.to_datetime(D.index), index=D.index).diff().dt.days > 5
Dprev.loc[gapday.values] = np.nan

# ---- R2_1 z-score fade
cs = pd.Series(C)
mu = cs.rolling(60).mean().to_numpy()
sd = cs.rolling(60).std().to_numpy()
cal = pd.read_csv(CAL)
evm = np.sort(pd.to_datetime(cal["timestamp_utc"], utc=True).values
              .astype("datetime64[m]").astype(np.int64))
k = np.searchsorted(evm, T)
d_next = np.where(k < len(evm), evm[np.minimum(k, len(evm) - 1)] - T, 10**9)
d_prev = np.where(k > 0, T - evm[np.maximum(k - 1, 0)], 10**9)
near_news = (d_next <= 30) | (d_prev <= 30)
contig60 = np.zeros(N, bool)
contig60[60:] = (T[60:] - T[:-60]) == 60
busy_until = -1
for j in np.where((BEMIN >= 480) & (BEMIN < 1200) & (BEMIN % 5 == 4) & contig60 & ~near_news)[0]:
    if j <= busy_until or j + 61 >= N or sd[j] <= 0:
        continue
    z = (C[j] - mu[j]) / sd[j]
    if abs(z) <= 3:
        continue
    dist = abs(C[j] - mu[j])
    lim = np.searchsorted(T, T[j + 1] + 60)
    if z > 3:
        ex = record("R2_1_ZFADE", j + 1, -1, C[j] + dist, mu[j], lim)
    else:
        ex = record("R2_1_ZFADE", j + 1, 1, C[j] - dist, mu[j], lim)
    busy_until = ex if ex is not None else j

# ---- R2_2 compressed London breakout
heights = {}
for kday, g in be_groups.items():
    rng = g[(BEMIN[g] >= 0) & (BEMIN[g] < 420)]
    if len(rng) >= 300:
        heights[kday] = (H[rng].max(), L[rng].min())
hk = sorted(heights)
hs = pd.Series([heights[x][0] - heights[x][1] for x in hk], index=hk)
pct = hs.rolling(61).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)
for kday in hk:
    p = pct.get(kday)
    if p is None or np.isnan(p) or p >= 0.30:
        continue
    g = be_groups[kday]
    hi, lo = heights[kday]
    ht = hi - lo
    lim = first_at_or_after(g, BEMIN, 960)
    if lim is None or ht <= 0:
        continue
    for j in g[(BEMIN[g] >= 420) & (BEMIN[g] < 660) & (BEMIN[g] % 5 == 4)]:
        if j + 1 >= lim:
            break
        if C[j] > hi:
            record("R2_2_LONDON_COMP", j + 1, 1, lo, hi + ht, lim)
            break
        if C[j] < lo:
            record("R2_2_LONDON_COMP", j + 1, -1, hi, lo - ht, lim)
            break

# ---- R2_3 PDH/PDL breakout in NY morning, R2_4 intraday momentum
for kday, g in d_groups.items():
    if kday not in Dprev.index:
        continue
    pv = Dprev.loc[kday]
    if np.isnan(pv["atr14"]):
        continue
    atr = pv["atr14"]
    # R2_3
    flat = g[BEMIN[g] >= 1320]
    flat = flat[(BEMIN[flat] < 1380)]
    if len(flat):
        lim = flat[0]
        for j in g[(BEMIN[g] >= 840) & (BEMIN[g] < 1080) & (BEMIN[g] % 5 == 4)]:
            if j + 1 >= lim:
                break
            ref = O[j + 1]
            if C[j] > pv["h"]:
                record("R2_3_PDH_PDL", j + 1, 1, ref - 0.5 * atr, ref + 1.0 * atr, lim)
                break
            if C[j] < pv["l"]:
                record("R2_3_PDH_PDL", j + 1, -1, ref + 0.5 * atr, ref - 1.0 * atr, lim)
                break
    # R2_4
    e = g[NYMIN[g] == 900]
    x = g[NYMIN[g] >= 1015]
    x = x[NYMIN[x] < 1020]
    if len(e) and len(x) and e[0] > g[0]:
        i = e[0]
        ret = C[i - 1] - O[g[0]]
        if ret != 0:
            dsign = 1 if ret > 0 else -1
            far = 1000.0
            record("R2_4_INTRADAY_MOM", i, dsign, O[i] - dsign * far, O[i] + dsign * far, x[0],
                   risk_override=0.5 * atr)

# ---- R2_5 Donchian on H4 bars aligned to the trading day
h4key = (ny + pd.Timedelta(hours=7)).dt.floor("4h")
dd4 = pd.DataFrame({"k": h4key.values, "o": O, "h": H, "l": L, "c": C, "i": np.arange(N)})
B = dd4.groupby("k").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                         i0=("i", "first"), n=("i", "size"))
B = B[B["n"] >= 120].copy()
pcb = B["c"].shift(1)
trb = np.maximum(B["h"] - B["l"], np.maximum((B["h"] - pcb).abs(), (B["l"] - pcb).abs()))
B["atr20"] = trb.rolling(20).mean()
B["hh20"] = B["h"].rolling(20).max().shift(1)
B["ll20"] = B["l"].rolling(20).min().shift(1)
B["hh10"] = B["h"].rolling(10).max().shift(1)
B["ll10"] = B["l"].rolling(10).min().shift(1)
B = B.reset_index()
bk = pd.to_datetime(B["k"]).to_numpy()


def donchian(cost, fl, fs):
    out, pos = [], 0
    for t in range(len(B) - 1):
        row = B.iloc[t]
        gap_next = (bk[t + 1] - bk[t]) > np.timedelta64(5, "D")
        if pos == 0:
            if np.isnan(row.atr20) or np.isnan(row.hh20) or gap_next:
                continue
            nxt = B.iloc[t + 1]
            if row.c > row.hh20:
                pos, ent = 1, nxt.o + cost["spread"] + cost["slip"]
            elif row.c < row.ll20:
                pos, ent = -1, nxt.o - cost["slip"]
            else:
                continue
            risk = 2 * row.atr20
            stop, t_in, bars = ent - pos * risk, t + 1, 0
            continue
        if t < t_in:
            continue
        bars += 1
        ex = None
        if pos == 1:
            if row.l <= stop:
                ex = min(row.o, stop) - cost["slip"]
            elif row.c < row.ll10 or gap_next:
                ex = (row.c if gap_next else B.iloc[t + 1].o) - cost["slip"]
        else:
            if row.h + cost["spread"] >= stop:
                ex = max(row.o + cost["spread"], stop) + cost["slip"]
            elif row.c > row.hh10 or gap_next:
                ex = (row.c if gap_next else B.iloc[t + 1].o) + cost["spread"] + cost["slip"]
        if ex is not None:
            fin = (fl if pos == 1 else fs) * ent * (bars / 6) / 365
            out.append((int(B.iloc[t_in].i0), pos * (ex - ent) - cost["comm"] - fin, risk))
            pos = 0
    return out


dn, dg, d2 = donchian(NORMAL, 0.05, 0.01), donchian(ZERO, 0, 0), donchian(scale(NORMAL, 2), 0.10, 0.02)
# cost changes which stops trigger, so the three runs need not match trade for trade:
# gross / 2x values are attached by entry bar where the same entry exists, else NaN
gmap, xmap = {a[0]: a[1] for a in dg}, {a[0]: a[1] for a in d2}
for a in dn:
    trades.append(dict(hyp="R2_5_DONCHIAN_H4", t=T[a[0]], net=a[1], gross=gmap.get(a[0], np.nan),
                       x2=xmap.get(a[0], np.nan), risk=a[2]))
print(f"Donchian H4 trades: net {len(dn)}, gross {len(dg)}, 2x {len(d2)}")

# ---- summary
tr = pd.DataFrame(trades)
tr["date"] = pd.to_datetime(tr["t"], unit="m", utc=True)
for kk in ("net", "gross", "x2"):
    tr["R_" + kk] = tr[kk] / tr["risk"]
cut = [pd.Timestamp(x, tz="UTC") for x in ("2023-01-01", "2024-01-01", "2026-09-01")]
tr["period"] = np.select([tr.date < cut[0], tr.date < cut[1], tr.date < cut[2]],
                         ["DEV", "EXCL", "SEEN"], "FRESH")
tr.to_csv(OUT + "_trades.csv", index=False)


def stats(x):
    r = x["R_net"].to_numpy()
    n = len(r)
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max() if n else 0
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return pd.Series(dict(n=n, win=(r > 0).mean(), R_gross=x["R_gross"].mean(), R_net=r.mean(),
                          t_net=r.mean() / r.std(ddof=1) * np.sqrt(n) if n > 2 else np.nan,
                          R_2x=x["R_x2"].mean(), sumR=r.sum(), PF=pos / neg if neg else np.nan,
                          maxDD_R=dd, usd_oz=x["net"].mean()))


s = tr[tr.period != "EXCL"].groupby(["hyp", "period"]).apply(stats, include_groups=False)
pd.set_option("display.width", 200)
print(s.round(3).to_string())
s.to_csv(OUT + "_summary.csv")
