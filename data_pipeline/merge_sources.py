#!/usr/bin/env python3
"""Merge PIPO-Index raw sources into validated, analysis-ready CSVs.

Inputs (data/):
  scorecard_raw.csv  long: unitid,year,variable,value   (2003-2024)
  ipeds_raw.csv      long: unitid,year,variable,value   (1986-2022)
  ipeds_directory.csv   metadata authority
  usn_rank_history.csv  Reiter USN rank history (national_universities + national_liberal_arts)

Outputs (data/):
  institutions_long.csv    coalesced long: unitid,year,variable,value,source
  institutions_wide.csv    coalesced wide + name,state
  coverage_report.csv      per (variable,year): n_scorecard,n_ipeds,n_merged,pct_of_1249
  institutions_master.csv  wide LEFT-JOIN directory metadata + Reiter rank history

Coalescing rule: for variables present in BOTH sources, take the Scorecard value
if present, else the IPEDS value. Each emitted value records its source.

Pure stdlib. Does not alter scales or invent values. Missing = empty cell.
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

SCORECARD_RAW = os.path.join(DATA, "scorecard_raw.csv")
IPEDS_RAW = os.path.join(DATA, "ipeds_raw.csv")
DIRECTORY = os.path.join(DATA, "ipeds_directory.csv")
USN = os.path.join(DATA, "usn_rank_history.csv")

OUT_LONG = os.path.join(DATA, "institutions_long.csv")
OUT_WIDE = os.path.join(DATA, "institutions_wide.csv")
OUT_COVERAGE = os.path.join(DATA, "coverage_report.csv")
OUT_MASTER = os.path.join(DATA, "institutions_master.csv")

# ---------------------------------------------------------------------------
# Canonical schema (deterministic column ordering)
# ---------------------------------------------------------------------------
CANONICAL_VARS = [
    # coalesced (present in both sources unless noted)
    "retention_ft",
    "grad_rate_6yr",
    "grad_rate_6yr_pell",
    "grad_rate_6yr_nonpell",
    "pct_part_time",
    "pct_pell",
    "pct_international",
    "pct_white",
    "pct_black",
    "pct_hispanic",
    "pct_asian",
    "pct_aian",
    "pct_nhpi",
    "pct_two_or_more",
    "pct_unknown",
    "pct_minority",          # ipeds only
    "net_price_0_30k",
    "net_price_30_48k",
    "net_price_48_75k",
    "net_price_75_110k",
    "net_price_110k_plus",
    # scorecard-only pass-through
    "sat75_reading",
    "sat75_math",
    "sat75_writing",
    "act75_cumulative",
    "act75_english",
    "act75_math",
    "act75_writing",
    "acceptance_rate",
    "median_debt",
    "cost_attendance",
    "tuition_in_state",
    "tuition_out_of_state",
    "avg_net_price_public",
    "avg_net_price_private",
    "ug_size",
]
CANONICAL_SET = set(CANONICAL_VARS)

# IPEDS raw variable names are already canonical (identity map).
IPEDS_MAP = {v: v for v in [
    "retention_ft", "grad_rate_6yr", "grad_rate_6yr_pell", "grad_rate_6yr_nonpell",
    "pct_part_time", "pct_pell", "pct_international",
    "pct_white", "pct_black", "pct_hispanic", "pct_asian", "pct_aian",
    "pct_nhpi", "pct_two_or_more", "pct_unknown", "pct_minority",
    "net_price_0_30k", "net_price_30_48k", "net_price_48_75k",
    "net_price_75_110k", "net_price_110k_plus",
]}

# Scorecard raw variable names -> canonical names.
SCORECARD_MAP = {
    "retention_ft_4yr": "retention_ft",
    "grad_rate_6yr": "grad_rate_6yr",
    "grad_rate_pell": "grad_rate_6yr_pell",
    "grad_rate_nonpell": "grad_rate_6yr_nonpell",
    "pct_part_time": "pct_part_time",
    "pct_pell": "pct_pell",
    "pct_international": "pct_international",
    "race_white": "pct_white",
    "race_black": "pct_black",
    "race_hispanic": "pct_hispanic",
    "race_asian": "pct_asian",
    "race_aian": "pct_aian",
    "race_nhpi": "pct_nhpi",
    "race_two_or_more": "pct_two_or_more",
    "race_unknown": "pct_unknown",
    "net_price_0_30k": "net_price_0_30k",
    "net_price_30_48k": "net_price_30_48k",
    "net_price_48_75k": "net_price_48_75k",
    "net_price_75_110k": "net_price_75_110k",
    "net_price_110k_plus": "net_price_110k_plus",
    # scorecard-only pass-through
    "sat75_reading": "sat75_reading",
    "sat75_math": "sat75_math",
    "sat75_writing": "sat75_writing",
    "act75_cumulative": "act75_cumulative",
    "act75_english": "act75_english",
    "act75_math": "act75_math",
    "act75_writing": "act75_writing",
    "acceptance_rate": "acceptance_rate",
    "median_debt": "median_debt",
    "cost_attendance": "cost_attendance",
    "tuition_in_state": "tuition_in_state",
    "tuition_out_of_state": "tuition_out_of_state",
    "avg_net_price_public": "avg_net_price_public",
    "avg_net_price_private": "avg_net_price_private",
    "ug_size": "ug_size",
}

DENOM = 1249  # in-scope universe (union of scorecard+ipeds unitids)


def _read_source(path, varmap, label):
    """Read a long source; return {(unitid,year,canon_var): value} and
    a presence dict {(canon_var,year): set(unitid)} for non-empty values."""
    values = {}
    presence = {}  # (canon_var, year) -> set(unitid)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            raw_var = row["variable"]
            canon = varmap.get(raw_var)
            if canon is None:
                raise ValueError(
                    f"{label}: unmapped variable {raw_var!r} "
                    f"(unitid={row['unitid']}, year={row['year']})")
            val = row["value"]
            if val == "" or val is None:
                continue
            unitid = row["unitid"]
            year = row["year"]
            values[(unitid, year, canon)] = val
            presence.setdefault((canon, year), set()).add(unitid)
    return values, presence


def main():
    sc_vals, sc_presence = _read_source(SCORECARD_RAW, SCORECARD_MAP, "scorecard")
    ip_vals, ip_presence = _read_source(IPEDS_RAW, IPEDS_MAP, "ipeds")

    # In-scope universe = union of unitids appearing in either source.
    inscope = set()
    for (u, _y, _v) in sc_vals:
        inscope.add(u)
    for (u, _y, _v) in ip_vals:
        inscope.add(u)

    # --- Coalesce: scorecard wins where present, else ipeds. -----------------
    coalesced = {}  # (unitid, year, canon) -> (value, source)
    for key, val in ip_vals.items():
        coalesced[key] = (val, "ipeds")
    for key, val in sc_vals.items():
        coalesced[key] = (val, "scorecard")  # overwrite ipeds when scorecard present

    # --- 1. institutions_long.csv -------------------------------------------
    long_rows = sorted(
        coalesced.items(),
        key=lambda kv: (kv[0][0], int(kv[0][1]), CANONICAL_VARS.index(kv[0][2])),
    )
    with open(OUT_LONG, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unitid", "year", "variable", "value", "source"])
        n_long = 0
        for (unitid, year, var), (val, src) in long_rows:
            w.writerow([unitid, year, var, val, src])
            n_long += 1

    # --- directory metadata --------------------------------------------------
    directory = {}
    with open(DIRECTORY, newline="") as f:
        for row in csv.DictReader(f):
            directory[row["unitid"]] = row

    # --- 2. institutions_wide.csv -------------------------------------------
    # Build (unitid, year) -> {canon: value}
    cells = {}
    uy_set = set()
    for (unitid, year, var), (val, _src) in coalesced.items():
        uy_set.add((unitid, year))
        cells.setdefault((unitid, year), {})[var] = val

    uy_sorted = sorted(uy_set, key=lambda t: (t[0], int(t[1])))

    wide_header = ["unitid", "year"] + CANONICAL_VARS + ["name", "state"]
    with open(OUT_WIDE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(wide_header)
        for (unitid, year) in uy_sorted:
            d = cells[(unitid, year)]
            meta = directory.get(unitid, {})
            row = [unitid, year]
            row += [d.get(v, "") for v in CANONICAL_VARS]
            row += [meta.get("name", ""), meta.get("state", "")]
            w.writerow(row)
    n_wide = len(uy_sorted)

    # --- 3. coverage_report.csv ---------------------------------------------
    # For each (variable, year): counts of distinct unitids with a value.
    years_by_var = {}
    for (var, year), uids in sc_presence.items():
        years_by_var.setdefault(var, set()).add(year)
    for (var, year), uids in ip_presence.items():
        years_by_var.setdefault(var, set()).add(year)

    with open(OUT_COVERAGE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variable", "year", "n_scorecard", "n_ipeds",
                    "n_merged", "pct_of_1249"])
        n_cov = 0
        for var in CANONICAL_VARS:
            years = sorted(years_by_var.get(var, set()), key=int)
            for year in years:
                sc_u = sc_presence.get((var, year), set())
                ip_u = ip_presence.get((var, year), set())
                n_sc = len(sc_u)
                n_ip = len(ip_u)
                n_merged = len(sc_u | ip_u)
                pct = round(100.0 * n_merged / DENOM, 2)
                w.writerow([var, year, n_sc, n_ip, n_merged, pct])
                n_cov += 1

    # --- 4. institutions_master.csv -----------------------------------------
    # Reiter rank history keyed by (unitid, year).
    ranks = {}  # (unitid, year) -> (rank, category)
    with open(USN, newline="") as f:
        for row in csv.DictReader(f):
            ranks[(row["unitid"], row["year"])] = (row["rank"], row["category"])

    master_header = (["unitid", "year"] + CANONICAL_VARS +
                     ["name", "state", "city", "zip", "region", "control",
                      "longitude", "latitude", "usn_rank", "usn_category"])
    with open(OUT_MASTER, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(master_header)
        for (unitid, year) in uy_sorted:
            d = cells[(unitid, year)]
            meta = directory.get(unitid, {})
            rank, category = ranks.get((unitid, year), ("", ""))
            row = [unitid, year]
            row += [d.get(v, "") for v in CANONICAL_VARS]
            row += [
                meta.get("name", ""), meta.get("state", ""),
                meta.get("city", ""), meta.get("zip", ""),
                meta.get("region", ""), meta.get("control", ""),
                meta.get("longitude", ""), meta.get("latitude", ""),
                rank, category,
            ]
            w.writerow(row)
    n_master = len(uy_sorted)

    # --- summary -------------------------------------------------------------
    schools_with_value = len(inscope)
    print("=== merge_sources summary ===")
    print(f"in-scope unitids (union):       {len(inscope)}")
    print(f"schools with >=1 value:         {schools_with_value}")
    print(f"institutions_long.csv rows:     {n_long}")
    print(f"institutions_wide.csv rows:     {n_wide}")
    print(f"coverage_report.csv rows:       {n_cov}")
    print(f"institutions_master.csv rows:   {n_master}")
    return {
        "n_long": n_long, "n_wide": n_wide, "n_cov": n_cov,
        "n_master": n_master, "inscope": len(inscope),
    }


if __name__ == "__main__":
    main()
