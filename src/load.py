"""Load HistData XAUUSD M1 bars into a single UTC-indexed parquet.

Accepts HistData "ASCII M1" files (*.txt as downloaded, or renamed *.csv).
Vendor clock rule (checked against 370 release times):
naive HistData timestamp + 6h = Europe/Berlin wall time.
Prices are treated as BID.
"""
import glob
import sys

import pandas as pd

SRC = sys.argv[1]
OUT = sys.argv[2]

frames = []
for f in sorted(glob.glob(f"{SRC}/*.csv") + glob.glob(f"{SRC}/*.txt")):
    df = pd.read_csv(f, sep=";", header=None, names=["ts", "o", "h", "l", "c", "v"],
                     dtype={"ts": str})
    frames.append(df)
raw = pd.concat(frames, ignore_index=True)
naive = pd.to_datetime(raw["ts"], format="%Y%m%d %H%M%S") + pd.Timedelta(hours=6)
berlin = naive.dt.tz_localize("Europe/Berlin", ambiguous="NaT", nonexistent="NaT")
raw["utc"] = berlin.dt.tz_convert("UTC")
raw = raw.dropna(subset=["utc"])
n0 = len(raw)
raw = raw.drop_duplicates(subset=["utc"], keep="first").sort_values("utc")
print(f"rows {n0} -> {len(raw)} after dedupe (keep-first)")
raw = raw[["utc", "o", "h", "l", "c"]].reset_index(drop=True)
raw.to_parquet(OUT)
print(raw["utc"].min(), raw["utc"].max())
cov = raw.groupby(raw["utc"].dt.to_period("M")).size()
print(cov.to_string())
