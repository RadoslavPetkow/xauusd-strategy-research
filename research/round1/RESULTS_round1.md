# Round 1 — results (2026-11-23)

Registration: `REGISTRATION_round1.md` (fixed before running). Reproduce: see the repository README.

Sanity checks
- H1 reproduces the September Run 18 sample (732 in-sample trades vs 737) and its finding:
  gross edge ≈ 0 (+0.004R DEV, +0.025R SEEN).
- Calendar/price alignment: median 1m range is 9.81 at the CPI/NFP release minute vs
  1.32 one minute before and 0.62 overall, so release timestamps line up.

| Hypothesis | DEV n | DEV R gross | DEV R net | DEV t | SEEN R net | Gate |
|---|---|---|---|---|---|---|
| H1 ORB NY | 732 | +0.004 | −0.070 | −2.3 | −0.021 | FAIL |
| H2 London breakout | 612 | +0.014 | −0.029 | −0.9 | +0.042 | FAIL |
| H3 News momentum | 68 | −0.094 | −0.337 | −2.9 | −0.244 | FAIL |
| H4 News fade | 46 | +0.086 | −0.527 | −4.1 | −0.367 | FAIL |
| H5 Donchian D1 | 23 | −0.159 | −0.268 | −1.4 | +0.472 | FAIL (n too small) |
| H6 Asia long | 755 | +0.036 | −0.002 | −0.1 | +0.088 | FAIL |

No hypothesis passes the DEV gate (t > 2.64, n ≥ 100, mean net R > 0).

Notes
- H6 looks good in SEEN (t = 3.7), but that period is the 2024–2026 gold rally. Per year,
  the Asia session beats the rest of the day in some years and loses in others (2020, 2022);
  its big gains come from the rally: market exposure (beta), not an edge.
- News trades: 5-minute post-release ranges are small relative to news-time spread and
  slippage, so both directions lose net.
- Costs used: spread 0.30, commission 0.07 RT, slippage 0.05/side ($/oz); news 0.80 / 0.20.
