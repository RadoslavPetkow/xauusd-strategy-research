# Round 2 — results (2026-11-23)

Registration: `REGISTRATION_round2.md`. Gate: DEV t > 2.84 (11 cumulative tests), n ≥ 100,
mean net R > 0, and mean net R > 0 in SEEN.
Reproduce: see the repository README.

| Hypothesis | DEV n | DEV R gross | DEV R net | DEV t | SEEN R net | SEEN t | Gate |
|---|---|---|---|---|---|---|---|
| R2_1 z-score fade | 1493 | +0.010 | −0.140 | −6.6 | −0.093 | −3.8 | FAIL |
| R2_2 London BO, compressed Asia | 219 | −0.007 | −0.067 | −1.2 | +0.075 | +1.2 | FAIL |
| R2_3 PDH/PDL NY breakout | 475 | +0.041 | +0.007 | +0.2 | +0.018 | +0.5 | FAIL |
| R2_4 intraday momentum | 737 | +0.008 | −0.030 | −3.2 | −0.007 | −0.6 | FAIL |
| R2_5 Donchian H4 20/10 | 129 | +0.186 | +0.132 | +0.6 | +0.283 | +1.4 | FAIL (not significant) |

Sensitivity of R2_5 (robustness only, no selection), mean net R (t):

| Entry/exit | DEV | SEEN |
|---|---|---|
| 10/5 | +0.047 (0.4) | +0.097 (0.9) |
| 20/10 | +0.132 (0.6) | +0.271 (1.4) |
| 30/15 | +0.036 (0.2) | +0.568 (1.4) |
| 40/20 | −0.094 (−0.4) | +0.312 (0.7) |
| 55/20 | +0.010 (0.0) | +0.263 (0.6) |

Reading: trend following is positive across every channel length in the 2024–2026 rally and
about zero in the 2020–2022 range-bound market. That is the normal profile of trend following
(it earns in trends, bleeds in ranges); it is not evidence of an edge that can be confirmed on
one instrument over ~5.5 years. With ~3–4 trades a month, forward testing would need years,
not months, to reach significance.

After 11 pre-registered tests across rounds 1–2, nothing passes.
