# Round 2 — pre-registration (written 2026-11-23, before any round-2 result was computed)

Same data, periods, costs and execution rules as round 1 (see REGISTRATION_round1.md).
Cumulative tests after this round: 11 → gate t > 2.84 (two-sided p < 0.05/11), n ≥ 100,
mean net R > 0 in DEV; and mean net R > 0 in SEEN.

## Hypotheses (all parameters fixed)
- R2_1 ZSCORE_FADE: on every 5m close between 08:00 and 20:00 Berlin, z = (close − mean of
  last 60 1m closes) / std of the same 60 closes. z > 3 → short, z < −3 → long, next bar.
  TP = the 60-bar mean at signal time; SL = same distance on the other side (≈1R:1R);
  flat after 60 minutes. No new signal while a trade is open. Skipped within ±30 min of any
  calendar event (CPI, NFP, PPI, GDP, FOMC, FOMC minutes).
- R2_2 LONDON_BO_COMPRESSED: round-1 H2 rules, taken only on days whose Asian range height
  is below the 30th percentile of the previous 60 days' heights.
- R2_3 PDH_PDL_NY: previous trading day's (17:00 NY cut) high/low. First 5m close above
  PDH (long) or below PDL (short) between 14:00 and 18:00 Berlin; SL 0.5×ATR14, TP 1.0×ATR14
  (ATR of the previous completed day), from the next bar's open; flat 22:00 Berlin.
- R2_4 INTRADAY_MOMENTUM: per trading day, sign of (close of the 14:59 ET bar − day open at
  18:00 ET previous evening); enter at 15:00 ET in that direction, flat 16:55 ET. No stop.
  1R = 0.5×ATR14 of the previous completed day.
- R2_5 DONCHIAN_H4: round-1 H5 rules on 4h bars (aligned to the 17:00 NY day): 20-bar entry
  channel, 10-bar exit channel, 2×ATR(20) stop; financing charged per day held (6 bars = 1 day).
