#!/usr/bin/env python3
"""Sanity checks for web/data/institutions.json (built by
data_pipeline/build_app_dataset.py). Run after the build script.

Verifies: record count == legacy count, every legacy VA field survives the
join, new canonical metrics are present, the latest-value provenance is
consistent, and a couple of known-school spot checks are sane.
"""

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "data", "institutions.json")
LEGACY = os.path.join(ROOT, "web", "data", "university_data.json")
MASTER = os.path.join(ROOT, "data", "institutions_master.csv")

LEGACY_METRIC_KEYS = [
    "vaRetention", "vaGraduation", "vaDistance",
    "usNewsRank", "retentionRate", "graduationRate",
]
NEW_METRIC_SAMPLE = [
    "net_price_0_30k", "sat75_math", "acceptance_rate",
    "grad_rate_6yr", "pct_pell",
]

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


recs = json.load(open(OUT, encoding="utf-8"))
legacy = {int(r["UNITID"]): r for r in json.load(open(LEGACY, encoding="utf-8"))}

# 1. record count matches in-scope legacy count
check(len(recs) == len(legacy), f"count {len(recs)} != legacy {len(legacy)}")

by_id = {r["unitid"]: r for r in recs}
check(set(by_id) == set(legacy), "unitid sets differ between output and legacy")

# 2. every legacy VA field is preserved verbatim
for u, leg in legacy.items():
    m = by_id[u]["metrics"]
    for k in LEGACY_METRIC_KEYS:
        check(k in m, f"{u} missing legacy metric {k}")
    # spot-check verbatim preservation of the residual VA fields
    if leg.get("VA Retention") is not None:
        check(m["vaRetention"] == leg["VA Retention"], f"{u} vaRetention drifted")

# 3. new canonical metrics exist as keys (value may be None if no data)
for r in recs:
    for k in NEW_METRIC_SAMPLE:
        check(k in r["metrics"], f"{r['unitid']} missing new metric {k}")

# 4. provenance: every non-null new metric has a source year in metricYears
for r in recs:
    years = r.get("metricYears", {})
    for k, v in r["metrics"].items():
        if k in NEW_METRIC_SAMPLE and v is not None:
            check(k in years, f"{r['unitid']} {k} has value but no metricYear")

# 4b. coordinates: every record carries latitude/longitude/city keys, most have
#     real coords (the ~21 schools absent from the directory are null), and a
#     known school's coordinates are sane.
for r in recs:
    for k in ("latitude", "longitude", "city"):
        check(k in r, f"{r['unitid']} missing key {k}")
with_coords = sum(1 for r in recs if r["latitude"] is not None and r["longitude"] is not None)
check(with_coords >= 1200, f"only {with_coords} records have coordinates (expected ~1228)")
stanford = next(r for r in recs if r["name"] == "Stanford University")
check(36 < stanford["latitude"] < 38 and -123 < stanford["longitude"] < -121,
      f"Stanford coords look wrong: {stanford['latitude']},{stanford['longitude']}")
check(stanford["city"] == "Stanford", f"Stanford city {stanford['city']!r} != 'Stanford'")

# 5. latest-value correctness: re-derive Princeton acceptance_rate from CSV
princeton = next(r for r in recs if r["name"] == "Princeton University")
pu = princeton["unitid"]
best_year, best_val = None, None
with open(MASTER, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        if int(row["unitid"]) != pu:
            continue
        cell = (row.get("acceptance_rate") or "").strip()
        if cell == "":
            continue
        y = int(row["year"])
        if best_year is None or y >= best_year:
            best_year, best_val = y, float(cell)
check(
    princeton["metrics"]["acceptance_rate"] == best_val,
    f"Princeton acceptance_rate {princeton['metrics']['acceptance_rate']} != latest CSV {best_val}",
)
check(0.0 < best_val < 0.10, f"Princeton acceptance_rate {best_val} not in expected ~0.05 range")

if failures:
    print("FAIL")
    for f_ in failures[:20]:
        print(" -", f_)
    sys.exit(1)
print(f"PASS: {len(recs)} records, all legacy VA + new metrics present, latest-value verified")
