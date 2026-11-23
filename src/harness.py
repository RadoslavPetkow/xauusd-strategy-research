"""Round-1 research harness for XAU/USD. See REGISTRATION_round1.md (fixed before running)."""
import sys

import numpy as np
import pandas as pd

BARS = sys.argv[1]
CAL = sys.argv[2]
OUT = sys.argv[3]

df = pd.read_parquet(BARS)
utc = df["utc"]
ny = utc.dt.tz_convert("America/New_York")
be = utc.dt.tz_convert("Europe/Berlin")
T = utc.values.astype("datetime64[m]").astype(np.int64)  # epoch minutes
O, H, L, C = (df[k].to_numpy(float) for k in "ohlc")
NYMIN = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
BEMIN = (be.dt.hour * 60 + be.dt.minute).to_numpy()
NYDATE = ny.dt.date.to_numpy()
BEDATE = be.dt.date.to_numpy()
BEWD = be.dt.weekday.to_numpy()
N = len(df)

NORMAL = dict(spread=0.30, slip=0.05, comm=0.07)
NEWS = dict(spread=0.80, slip=0.20, comm=0.07)
ZERO = dict(spread=0.0, slip=0.0, comm=0.0)


def scale(cost, k):
    return {a: b * k for a, b in cost.items()}


def sim(i, d, sl, tp, lim, cost):
    """Simulate one trade on 1m bars. d=+1 long, -1 short. sl/tp in bid-chart terms.
    Returns (pnl_per_oz, risk_per_oz) or None."""
    sp, sl_, cm = cost["spread"], cost["slip"], cost["comm"]
    lim = min(lim, N - 1)
    if i >= lim:
        return None
    if d == 1:
        entry = O[i] + sp + sl_
        risk = entry - sl
        if risk <= 0 or tp <= entry:
            return None
        ex = None
        for j in range(i, lim):
            if L[j] <= sl:
                ex = min(O[j], sl) - sl_
                break
            if H[j] >= tp:
                ex = tp
                break
        if ex is None:
            ex = O[lim] - sl_
        return ex - entry - cm, risk
    entry = O[i] - sl_
    risk = sl - entry
    if risk <= 0 or tp >= entry:
        return None
    ex = None
    for j in range(i, lim):
        if H[j] + sp >= sl:
            ex = max(O[j] + sp, sl) + sl_
            break
        if L[j] + sp <= tp:
            ex = tp
            break
    if ex is None:
        ex = O[lim] + sp + sl_
    return entry - ex - cm, risk


trades = []  # dicts: hyp, entry_utc, net, gross, x2, risk


def record(hyp, i, d, sl, tp, lim, cost, risk_override=None):
    r = sim(i, d, sl, tp, lim, cost)
    if r is None:
        return
    g = sim(i, d, sl, tp, lim, ZERO)
    x2 = sim(i, d, sl, tp, lim, scale(cost, 2))
    if g is None or x2 is None:
        return
    risk = risk_override if risk_override else r[1]
    trades.append(dict(hyp=hyp, t=T[i], net=r[0], gross=g[0], x2=x2[0], risk=risk))


def first_at_or_after(g, mins, m):
    k = np.searchsorted(mins[g], m)
    return g[k] if k < len(g) else None


def breakout(hyp, groups, mins, r0, r1, e0, e1, flat, tp_mult, min_bars):
    for _, g in groups.items():
        rng = g[(mins[g] >= r0) & (mins[g] < r1)]
        if len(rng) < min_bars:
            continue
        hi, lo = H[rng].max(), L[rng].min()
        ht = hi - lo
        if ht <= 0:
            continue
        lim = first_at_or_after(g, mins, flat)
        if lim is None:
            continue
        for j in g[(mins[g] >= e0) & (mins[g] < e1) & (mins[g] % 5 == 4)]:
            if j + 1 >= N or j + 1 >= lim:
                break
            if C[j] > hi:
                record(hyp, j + 1, 1, lo, hi + tp_mult * ht, lim, NORMAL)
                break
            if C[j] < lo:
                record(hyp, j + 1, -1, hi, lo - tp_mult * ht, lim, NORMAL)
                break


ny_groups = pd.Series(range(N)).groupby(NYDATE).indices
be_groups = pd.Series(range(N)).groupby(BEDATE).indices
ny_groups = {k: np.asarray(v) for k, v in ny_groups.items()}
be_groups = {k: np.asarray(v) for k, v in be_groups.items()}

# H1 ORB NY
breakout("H1_ORB_NY", ny_groups, NYMIN, 600, 630, 630, 960, 960, 2.0, 25)
# H2 London breakout
breakout("H2_LONDON_BO", be_groups, BEMIN, 0, 420, 420, 660, 960, 1.0, 300)

# H3/H4 news
cal = pd.read_csv(CAL)
cal = cal[cal["code"].isin(["CPI", "NFP"])]
ev = pd.to_datetime(cal["timestamp_utc"], utc=True).values.astype("datetime64[m]").astype(np.int64)
news_ok = 0
for t in ev:
    r = np.searchsorted(T, t)
    if r < 1 or r + 6 >= N or T[r] != t or T[r - 1] != t - 1 or T[r + 5] != t + 5:
        continue
    news_ok += 1
    move = C[r + 4] - C[r - 1]
    if move == 0:
        continue
    hi5, lo5 = H[r:r + 5].max(), L[r:r + 5].min()
    ref = O[r + 5]
    lim = np.searchsorted(T, t + 120)
    up = move > 0
    # momentum
    if up:
        record("H3_NEWS_MOM", r + 5, 1, lo5, ref + 2 * (ref - lo5), lim, NEWS)
        record("H4_NEWS_FADE", r + 5, -1, hi5, ref - 1 * (hi5 - ref), lim, NEWS)
    else:
        record("H3_NEWS_MOM", r + 5, -1, hi5, ref - 2 * (hi5 - ref), lim, NEWS)
        record("H4_NEWS_FADE", r + 5, 1, lo5, ref + 1 * (ref - lo5), lim, NEWS)
print(f"news events usable: {news_ok} of {len(ev)}")

# Daily bars cut at 17:00 New York
dkey = (ny + pd.Timedelta(hours=7)).dt.date.to_numpy()
dd = pd.DataFrame({"k": dkey, "o": O, "h": H, "l": L, "c": C, "i": np.arange(N)})
D = dd.groupby("k").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                        i0=("i", "first"), n=("i", "size"))
D = D[D["n"] >= 300].copy()
prev_c = D["c"].shift(1)
tr = np.maximum(D["h"] - D["l"], np.maximum((D["h"] - prev_c).abs(), (D["l"] - prev_c).abs()))
D["atr20"] = tr.rolling(20).mean()
D["atr14"] = tr.rolling(14).mean()
D["hh20"] = D["h"].rolling(20).max().shift(1)
D["ll20"] = D["l"].rolling(20).min().shift(1)
D["hh10"] = D["h"].rolling(10).max().shift(1)
D["ll10"] = D["l"].rolling(10).min().shift(1)
# break the series across the excluded 2023 gap: no position spans it
D = D.reset_index()


def donchian(cost, fin_long, fin_short):
    out = []
    pos = 0
    for t in range(len(D) - 1):
        row = D.iloc[t]
        if pos == 0:
            if np.isnan(row.atr20) or np.isnan(row.hh20):
                continue
            nxt = D.iloc[t + 1]
            if (pd.Timestamp(nxt.k) - pd.Timestamp(row.k)).days > 5:
                continue
            if row.c > row.hh20:
                pos, ent = 1, nxt.o + cost["spread"] + cost["slip"]
            elif row.c < row.ll20:
                pos, ent = -1, nxt.o - cost["slip"]
            else:
                continue
            risk = 2 * row.atr20
            stop = ent - pos * risk
            t_in, days = t + 1, 0
            continue
        # in position: evaluate day t (t > t_in-1)
        if t < t_in:
            continue
        days += 1
        ex = None
        gap = t + 1 < len(D) and (pd.Timestamp(D.iloc[t + 1].k) - pd.Timestamp(row.k)).days > 5
        if pos == 1:
            if row.l <= stop:
                ex = min(row.o, stop) - cost["slip"]
            elif row.c < row.ll10 or gap:
                ex = (row.c if gap else D.iloc[t + 1].o) - cost["slip"]
        else:
            if row.h + cost["spread"] >= stop:
                ex = max(row.o + cost["spread"], stop) + cost["slip"]
            elif row.c > row.hh10 or gap:
                ex = (row.c if gap else D.iloc[t + 1].o) + cost["spread"] + cost["slip"]
        if ex is not None:
            fin = (fin_long if pos == 1 else fin_short) * ent * days / 252
            pnl = pos * (ex - ent) - cost["comm"] - fin
            out.append((int(D.iloc[t_in].i0), pnl, risk))
            pos = 0
    return out


dn = donchian(NORMAL, 0.05, 0.01)
dg = donchian(ZERO, 0.0, 0.0)
d2 = donchian(scale(NORMAL, 2), 0.10, 0.02)
assert len(dn) == len(dg) == len(d2), (len(dn), len(dg), len(d2))
for a, b, c in zip(dn, dg, d2):
    trades.append(dict(hyp="H5_DONCHIAN_D1", t=T[a[0]], net=a[1], gross=b[1], x2=c[1], risk=a[2]))

# H6 Asia drift long
Dk = D.set_index("k")
dkeys = np.array([pd.Timestamp(k).value for k in D["k"]])
for k, g in be_groups.items():
    i = g[0]
    if BEWD[i] > 4 or BEMIN[i] > 15:
        continue
    lim = first_at_or_after(g, BEMIN, 420)
    if lim is None:
        continue
    # ATR of the last completed NY trading day before entry
    pos = np.searchsorted(dkeys, pd.Timestamp(dkey[i]).value) - 1
    if pos < 14 or np.isnan(D.iloc[pos].atr14):
        continue
    risk = 0.5 * D.iloc[pos].atr14
    vals = []
    for cost in (NORMAL, ZERO, scale(NORMAL, 2)):
        entry = O[i] + cost["spread"] + cost["slip"]
        vals.append(O[lim] - cost["slip"] - entry - cost["comm"])
    trades.append(dict(hyp="H6_ASIA_LONG", t=T[i], net=vals[0], gross=vals[1], x2=vals[2], risk=risk))

tr_df = pd.DataFrame(trades)
tr_df["date"] = pd.to_datetime(tr_df["t"], unit="m", utc=True)
for k in ("net", "gross", "x2"):
    tr_df["R_" + k] = tr_df[k] / tr_df["risk"]


def period(ts):
    if ts < pd.Timestamp("2023-01-01", tz="UTC"):
        return "DEV"
    if ts < pd.Timestamp("2024-01-01", tz="UTC"):
        return "EXCL"
    if ts < pd.Timestamp("2026-09-01", tz="UTC"):
        return "SEEN"
    return "FRESH"


tr_df["period"] = tr_df["date"].map(period)
tr_df.to_csv(OUT + "_trades.csv", index=False)


def stats(x):
    r = x["R_net"].to_numpy()
    n = len(r)
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max() if n else 0
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return pd.Series(dict(
        n=n,
        win=(r > 0).mean() if n else np.nan,
        R_gross=x["R_gross"].mean(),
        R_net=r.mean() if n else np.nan,
        t_net=r.mean() / r.std(ddof=1) * np.sqrt(n) if n > 2 else np.nan,
        R_2x=x["R_x2"].mean(),
        sumR=r.sum(),
        PF=pos / neg if neg > 0 else np.nan,
        maxDD_R=dd,
        usd_oz=x["net"].mean(),
    ))


summary = tr_df[tr_df["period"] != "EXCL"].groupby(["hyp", "period"]).apply(stats, include_groups=False)
pd.set_option("display.width", 200)
print(summary.round(3).to_string())
summary.to_csv(OUT + "_summary.csv")
