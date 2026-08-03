#!/usr/bin/env python3
"""Validation tests for data_pipeline/merge_sources.py outputs.

Runs the merge fresh, then asserts:
  (a) UAB (100663) has plausible coalesced values across years.
  (b) Coalescing prefers scorecard when both sources have a value.
  (c) coverage_report counts reconcile with raw inputs for sample variables.
  (d) institutions_master has one row per (unitid,year) and Reiter rank
      history attaches (Princeton 186131 national_universities rank ~1).
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "data_pipeline"))

import merge_sources  # noqa: E402


def load_long():
    rows = []
    with open(os.path.join(DATA, "institutions_long.csv"), newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def raw_lookup(path, varmap):
    """Return {(unitid,year,canon): value} for a raw long source."""
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            canon = varmap.get(r["variable"])
            if canon is None:
                continue
            out[(r["unitid"], r["year"], canon)] = r["value"]
    return out


def main():
    # Build outputs fresh.
    merge_sources.main()

    failures = []

    def check(cond, msg):
        if cond:
            print(f"  PASS: {msg}")
        else:
            print(f"  FAIL: {msg}")
            failures.append(msg)

    long_rows = load_long()
    # index long by (unitid,year,var)
    long_idx = {(r["unitid"], r["year"], r["variable"]): r for r in long_rows}

    # ----- (a) UAB plausibility -----------------------------------------
    print("(a) UAB (100663) plausibility")
    uab_ret = [(r["year"], float(r["value"]))
               for r in long_rows
               if r["unitid"] == "100663" and r["variable"] == "retention_ft"]
    check(len(uab_ret) > 5, f"UAB has retention_ft across many years (n={len(uab_ret)})")
    in_band = [y for y, v in uab_ret if 0.7 <= v <= 0.9]
    check(len(in_band) > 0,
          f"UAB retention_ft ~0.8 in some years (years in 0.7-0.9: {len(in_band)})")

    # net price band in 13-20k for ~2020
    np_keys = ["net_price_0_30k", "net_price_30_48k", "net_price_48_75k",
               "net_price_75_110k", "net_price_110k_plus"]
    found_np = []
    for yr in ("2019", "2020", "2021"):
        for k in np_keys:
            r = long_idx.get(("100663", yr, k))
            if r:
                found_np.append((yr, k, float(r["value"])))
    in_range = [t for t in found_np if 13000 <= t[2] <= 20000]
    check(len(in_range) > 0,
          f"UAB has a net_price band in 13-20k near 2020 (matches: {in_range[:3]})")

    # ----- (b) coalescing prefers scorecard ------------------------------
    print("(b) coalescing prefers scorecard when both present")
    sc_raw = raw_lookup(os.path.join(DATA, "scorecard_raw.csv"),
                        merge_sources.SCORECARD_MAP)
    ip_raw = raw_lookup(os.path.join(DATA, "ipeds_raw.csv"),
                        merge_sources.IPEDS_MAP)
    both = [k for k in sc_raw if k in ip_raw]
    check(len(both) > 0, f"found keys present in both sources (n={len(both)})")
    # every coalesced row for a 'both' key must be source=scorecard with sc value
    sample = both[:5000]
    bad = []
    for k in sample:
        r = long_idx.get(k)
        if r is None:
            bad.append((k, "missing in long"))
        elif r["source"] != "scorecard":
            bad.append((k, f"source={r['source']}"))
        elif r["value"] != sc_raw[k]:
            bad.append((k, f"value={r['value']} != sc {sc_raw[k]}"))
    check(not bad, f"all {len(sample)} sampled 'both' keys -> scorecard value (bad={bad[:3]})")
    # show one concrete example
    if both:
        ek = both[0]
        er = long_idx.get(ek)
        print(f"     example {ek}: source={er['source']} value={er['value']} "
              f"(sc={sc_raw[ek]}, ipeds={ip_raw[ek]})")

    # ----- (c) coverage reconciliation -----------------------------------
    print("(c) coverage_report reconciles with raw inputs")
    cov = load_csv("coverage_report.csv")
    cov_idx = {(r["variable"], r["year"]): r for r in cov}

    def raw_count(raw, var, year):
        return len({k[0] for k in raw if k[2] == var and k[1] == year})

    for var, year in [("retention_ft", "2010"), ("pct_minority", "2015"),
                      ("ug_size", "2020"), ("grad_rate_6yr", "2018")]:
        row = cov_idx.get((var, year))
        if row is None:
            check(False, f"coverage row exists for {var}/{year}")
            continue
        exp_sc = raw_count(sc_raw, var, year)
        exp_ip = raw_count(ip_raw, var, year)
        exp_merged = len(
            {k[0] for k in sc_raw if k[2] == var and k[1] == year} |
            {k[0] for k in ip_raw if k[2] == var and k[1] == year})
        ok = (int(row["n_scorecard"]) == exp_sc and
              int(row["n_ipeds"]) == exp_ip and
              int(row["n_merged"]) == exp_merged)
        check(ok, f"{var}/{year}: sc={row['n_scorecard']}({exp_sc}) "
                  f"ip={row['n_ipeds']}({exp_ip}) merged={row['n_merged']}({exp_merged})")

    # ----- (d) master one-row-per-(unitid,year) + rank attach ------------
    print("(d) institutions_master integrity + rank attach")
    master = load_csv("institutions_master.csv")
    keys = [(r["unitid"], r["year"]) for r in master]
    check(len(keys) == len(set(keys)),
          f"one row per (unitid,year) (rows={len(keys)}, unique={len(set(keys))})")
    # in-scope coverage: all 1249 present
    n_schools = len({r["unitid"] for r in master})
    check(n_schools == 1249, f"all 1249 in-scope schools present (got {n_schools})")
    # Princeton rank
    princeton = [r for r in master
                 if r["unitid"] == "186131" and r["usn_rank"] != ""]
    check(len(princeton) > 0, f"Princeton 186131 has rank rows (n={len(princeton)})")
    recent = [r for r in princeton if int(r["year"]) >= 2018]
    cats = {r["usn_category"] for r in recent}
    ranks_recent = [int(r["usn_rank"]) for r in recent]
    check("national_universities" in cats,
          f"Princeton category national_universities present ({cats})")
    check(all(1 <= rk <= 3 for rk in ranks_recent) and 1 in ranks_recent,
          f"Princeton recent rank ~1 (ranks {sorted(set(ranks_recent))})")

    # ----- result --------------------------------------------------------
    print()
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for m in failures:
            print(f"  - {m}")
        sys.exit(1)
    print("RESULT: ALL ASSERTIONS PASSED")


if __name__ == "__main__":
    main()
