# Round 1 — pre-registration (written 2026-11-23, before any result was computed)

All parameters below are fixed. No tuning in this round. A hypothesis that fails is
dropped or replaced by a *different* idea in round 2, not re-tuned on the same data.

## Data
HistData XAUUSD M1 (bid), 2020-01 .. 2026-09-04. Clock: vendor ts + 6h = Europe/Berlin.
2023 excluded (vendor gaps, per trading-bot README).

## Periods
- DEV   2020-01-01 .. 2022-12-31 — the only period used for the pass/fail gate.
- SEEN  2024-01-01 .. 2026-08-31 — already looked at in the September news-blackout
  experiment, so it is *not* a clean out-of-sample. Used only as a kill check:
  a hypothesis that is negative here is dead.
- FRESH 2026-09-01 .. — 4 days only; the real holdout is Oct–Nov 2026 data still to be
  downloaded, then forward paper trading.

## Costs (realistic retail ECN, per ounce)
- normal: spread 0.30, commission 0.07 round trip, slippage 0.05 per side
- news entries (H3, H4): spread 0.80, slippage 0.20 per side
- overnight financing for H5: long 5%/yr, short 1%/yr of notional
- every result is also reported gross (zero costs) and at 2x costs.
Long entries pay the spread (prices are bid); shorts pay it on exit.

## Execution rules
Signal on a bar close, fill on the next 1m bar open. Exits simulated on 1m bars.
If SL and TP are both touched in one bar, SL counts. Gap through SL fills at the bar open.

## Hypotheses
- H1 ORB_NY (re-test of Run 18 with realistic costs): range = 10:00–10:30 ET;
  entry on the first 5m close beyond the range in 10:30–16:00 ET; SL opposite bound;
  TP bound ± 2×range height; flat at 16:00 ET.
- H2 LONDON_BREAKOUT: range = 00:00–07:00 Europe/Berlin; entry on first 5m close beyond
  it in 07:00–11:00 Berlin; SL opposite bound; TP bound ± 1×range height; flat 16:00 Berlin.
- H3 NEWS_MOMENTUM (CPI, NFP): move = close(T+4m) − close(T−1m) where T = release minute;
  enter at T+5m in the move's direction; SL = opposite extreme of the T..T+4 bars; TP 2R;
  flat at T+120m.
- H4 NEWS_FADE (CPI, NFP): same setup, opposite direction; SL = extreme on the move side
  of T..T+4; TP 1R; flat at T+120m.
- H5 DONCHIAN_D1: daily bars cut at 17:00 New York. Long when close > highest high of the
  previous 20 days, short when close < lowest low of previous 20; fill next day open;
  exit on close beyond the 10-day opposite channel (next open) or 2×ATR(20) stop; one
  position at a time.
- H6 ASIA_DRIFT_LONG: long at the first bar at/after 00:00 Berlin (Mon–Fri), flat at 07:00
  Berlin. No stop. Reported in $/oz and as R where 1R = 0.5×ATR14(daily).

## Gate (DEV)
n ≥ 100 trades, mean net R > 0, and t-stat > 2.64 (two-sided p < 0.05 / 6 hypotheses,
Bonferroni). Passing hypotheses must also have mean net R > 0 in SEEN.
