"""
Fetch IPEDS variables from the Urban Institute Education Data API for every
UNITID in university_data.json and write them to data/ipeds_raw.csv in LONG
format: one row per (unitid, year, variable, value).

The Urban Institute "Education Data API" is open (NO API key required):
    https://educationdata.urban.org/documentation/

Why Urban and not Scorecard for these series? Urban exposes deeper IPEDS
history (retention back to 2003, grad rates back to 1996) than several
Scorecard fields, and needs no key, so it can be exercised fully in tests.

Variable -> column naming mirrors the College Scorecard puller so the two
raw files merge cleanly later on (unitid, year):

    retention_ft            first-to-second-year retention, full-time
    grad_rate_6yr           6-year (150%) bachelor's completion rate
    grad_rate_6yr_pell      6-year completion, Pell recipients
    grad_rate_6yr_nonpell   6-year completion, non-Pell (derived)
    pct_part_time           share of degree-seeking UG that is part-time
    pct_white .. pct_unknown  undergraduate race/ethnicity shares
    pct_international       non-resident-alien share (IPEDS race code 8)
    pct_minority           1 - white - international - unknown
    net_price_0_30k ..      net price by income band (5 bands)
    pct_pell               share of all undergraduates receiving Pell

All rates/shares are stored as FRACTIONS (0-1) to match Scorecard's native
scale; net price is in dollars.

Series coverage (real Urban coverage from data_pipeline/variable_sources.md):
    retention_ft            2003 - 2020
    grad_rate_6yr           1996 - 2022
    grad pell / non-pell    2015 - 2017   (Urban only has 3 cohort years)
    fall enrollment shares  1986 - 2022
    net price bands         2008 - 2021
    pct_pell                2007 - 2021

USAGE
    # Full pull (all 1,249 unitids, all years, all series) -- LONG, asks first:
    python3 data_pipeline/fetch_ipeds.py

    # Subset test (the configuration used in this script's self-test):
    python3 data_pipeline/fetch_ipeds.py \
        --unitids 100663,100706,100751,110635,166683,186131,243744,130794,139755,228778 \
        --years 2016,2018,2020 --out data/ipeds_test.csv

    # First N institutions only:
    python3 data_pipeline/fetch_ipeds.py --limit 50

    # Restrict to certain series:
    python3 data_pipeline/fetch_ipeds.py --series retention,grad,pell

Polite sleeps are inserted between requests. The full pull is ~1,000 requests
and takes several minutes; per project rules, confirm before launching it.
"""

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNI_DATA = ROOT / "university_data.json"
DEFAULT_OUT = ROOT / "data" / "ipeds_raw.csv"

BASE = "https://educationdata.urban.org/api/v1/college-university/ipeds"

# Comma-separated unitid batch size. ~200 ids keeps the URL well under common
# 8 KB limits while cutting request count.
BATCH_SIZE = 200
SLEEP = 0.5          # polite pause between requests (seconds)
TIMEOUT = 120        # per-request timeout (seconds)
RETRIES = 3

# IPEDS race code -> Scorecard-style share column (fall-enrollment endpoint).
RACE_COLS = {
    1: "pct_white",
    2: "pct_black",
    3: "pct_hispanic",
    4: "pct_asian",
    5: "pct_aian",
    6: "pct_nhpi",
    7: "pct_two_or_more",
    8: "pct_international",   # non-resident alien
    9: "pct_unknown",
}

# Net-price income_level code -> column. 1=<30k .. 5=110k+.
NETPRICE_COLS = {
    1: "net_price_0_30k",
    2: "net_price_30_48k",
    3: "net_price_48_75k",
    4: "net_price_75_110k",
    5: "net_price_110k_plus",
}

# Series -> real Urban year coverage (inclusive).
COVERAGE = {
    "retention": range(2003, 2021),   # 2003-2020
    "grad": range(1996, 2023),        # 1996-2022
    "pell": range(2015, 2018),        # grad-rates-pell: 2015-2017 only
    "enrollment": range(1986, 2023),  # 1986-2022
    "netprice": range(2008, 2022),    # 2008-2021
    "pctpell": range(2007, 2022),     # 2007-2021
}
ALL_SERIES = list(COVERAGE.keys())


def get_json(url):
    """GET a URL and return parsed JSON, with simple retry/backoff."""
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PIPO-Index/ipeds-puller"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last = e
            code = getattr(e, "code", None)
            if code == 404:
                # Year/endpoint genuinely has no data -> treat as empty.
                return {"results": []}
            wait = SLEEP * (attempt + 1) * 2
            print(f"    retry {attempt + 1}/{RETRIES} after error ({e}); "
                  f"sleeping {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)
    print(f"    giving up on {url[:120]}... ({last})", file=sys.stderr)
    return {"results": []}


def build_url(path, **params):
    return f"{BASE}/{path}?" + urllib.parse.urlencode(params)


def batches(ids, size=BATCH_SIZE):
    for i in range(0, len(ids), size):
        yield ids[i:i + size]


# --------------------------------------------------------------------------
# Per-series fetchers. Each yields (unitid, year, variable, value) tuples.
# --------------------------------------------------------------------------

def fetch_retention(ids, years):
    for year in years:
        for batch in batches(ids):
            url = build_url(f"fall-retention/{year}/",
                            unitid=",".join(map(str, batch)), ftpt=1)
            for r in get_json(url).get("results", []):
                v = r.get("retention_rate")
                if v is not None and v >= 0:
                    yield (r["unitid"], year, "retention_ft", v)
            time.sleep(SLEEP)


def fetch_grad(ids, years):
    """6-yr (150%) bachelor's completion. Prefer subcohort 2 (bachelor's),
    fall back to subcohort 99 (total cohort)."""
    for year in years:
        for batch in batches(ids):
            url = build_url(f"grad-rates/{year}/",
                            unitid=",".join(map(str, batch)),
                            institution_level=4, race=99, sex=99)
            # per unitid: {subcohort: (rate, cohort_adj)} keeping the best row
            best = defaultdict(dict)
            for r in get_json(url).get("results", []):
                rate = r.get("completion_rate_150pct")
                if rate is None:
                    continue
                sc = r.get("subcohort")
                cohort = r.get("cohort_adj_150pct") or 0
                cur = best[r["unitid"]].get(sc)
                if cur is None or cohort > cur[1]:
                    best[r["unitid"]][sc] = (rate, cohort)
            for uid, by_sc in best.items():
                chosen = by_sc.get(2) or by_sc.get(99)
                if chosen is not None:
                    yield (uid, year, "grad_rate_6yr", chosen[0])
            time.sleep(SLEEP)


def fetch_pell_grad(ids, years):
    """grad-rates-pell: Pell rate (fed_aid_type=1) directly; non-Pell derived
    from total (99) minus Pell using cohort_rev and completers_150pct. Uses
    subcohort 99 (total cohort)."""
    for year in years:
        for batch in batches(ids):
            url = build_url(f"grad-rates-pell/{year}/",
                            unitid=",".join(map(str, batch)), institution_level=4)
            agg = defaultdict(dict)  # uid -> {fed_aid_type: (cohort, completers, rate)}
            for r in get_json(url).get("results", []):
                if r.get("subcohort") != 99:
                    continue
                fat = r.get("fed_aid_type")
                agg[r["unitid"]][fat] = (
                    r.get("cohort_rev"),
                    r.get("completers_150pct"),
                    r.get("completion_rate_150pct"),
                )
            for uid, by_fat in agg.items():
                pell = by_fat.get(1)
                total = by_fat.get(99)
                if pell and pell[2] is not None:
                    yield (uid, year, "grad_rate_6yr_pell", pell[2])
                if pell and total and None not in (pell[0], pell[1], total[0], total[1]):
                    np_cohort = total[0] - pell[0]
                    np_comp = total[1] - pell[1]
                    if np_cohort > 0:
                        yield (uid, year, "grad_rate_6yr_nonpell",
                               round(np_comp / np_cohort, 4))
            time.sleep(SLEEP)


def fetch_enrollment(ids, years):
    """Undergraduate degree-seeking fall enrollment. Computes part-time share,
    race/ethnicity shares, international share and minority share."""
    for year in years:
        for batch in batches(ids):
            url = build_url(f"fall-enrollment/{year}/1/race/sex/",
                            unitid=",".join(map(str, batch)),
                            sex=99, class_level=99, degree_seeking=1)
            # uid -> {"ftpt": {ftpt: enr}, "race": {race: enr}}
            data = defaultdict(lambda: {"ftpt": {}, "race": {}})
            for r in get_json(url).get("results", []):
                uid = r["unitid"]
                enr = r.get("enrollment_fall")
                if enr is None:
                    continue
                if r.get("race") == 99 and r.get("ftpt") in (1, 2, 99):
                    data[uid]["ftpt"][r["ftpt"]] = enr
                if r.get("ftpt") == 99 and r.get("race") in (*RACE_COLS, 99):
                    data[uid]["race"][r["race"]] = enr
            for uid, d in data.items():
                total = d["ftpt"].get(99) or d["race"].get(99)
                if not total:
                    continue
                pt = d["ftpt"].get(2)
                if pt is not None and d["ftpt"].get(99):
                    yield (uid, year, "pct_part_time",
                           round(pt / d["ftpt"][99], 4))
                rt = d["race"].get(99)
                if rt:
                    for code, col in RACE_COLS.items():
                        if code in d["race"]:
                            yield (uid, year, col, round(d["race"][code] / rt, 4))
                    white = d["race"].get(1, 0)
                    intl = d["race"].get(8, 0)
                    unk = d["race"].get(9, 0)
                    yield (uid, year, "pct_minority",
                           round(1 - (white + intl + unk) / rt, 4))
            time.sleep(SLEEP)


def fetch_netprice(ids, years):
    for year in years:
        for batch in batches(ids):
            url = build_url(f"sfa-grants-and-net-price/{year}/",
                            unitid=",".join(map(str, batch)), type_of_aid=9)
            for r in get_json(url).get("results", []):
                col = NETPRICE_COLS.get(r.get("income_level"))
                v = r.get("net_price")
                if col and v is not None:
                    yield (r["unitid"], year, col, v)
            time.sleep(SLEEP)


def fetch_pctpell(ids, years):
    for year in years:
        for batch in batches(ids):
            url = build_url(f"sfa-all-undergraduates/{year}/",
                            unitid=",".join(map(str, batch)), type_of_aid=5)
            for r in get_json(url).get("results", []):
                v = r.get("percent_of_students")
                if v is not None and v >= 0:
                    yield (r["unitid"], year, "pct_pell", v)
            time.sleep(SLEEP)


SERIES_FN = {
    "retention": fetch_retention,
    "grad": fetch_grad,
    "pell": fetch_pell_grad,
    "enrollment": fetch_enrollment,
    "netprice": fetch_netprice,
    "pctpell": fetch_pctpell,
}


def load_unitids():
    with UNI_DATA.open() as f:
        unis = json.load(f)
    return [int(u["UNITID"]) for u in unis if u.get("UNITID") is not None]


def parse_args():
    p = argparse.ArgumentParser(description="Pull IPEDS vars from Urban API -> long CSV")
    p.add_argument("--unitids", help="comma-separated unitid subset")
    p.add_argument("--limit", type=int, help="use only the first N unitids")
    p.add_argument("--years", help="comma-separated year subset (intersected with each series' coverage)")
    p.add_argument("--series", help=f"comma-separated subset of {ALL_SERIES}")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="output CSV path")
    return p.parse_args()


def main():
    args = parse_args()

    if args.unitids:
        ids = [int(x) for x in args.unitids.split(",") if x.strip()]
    else:
        ids = load_unitids()
        if args.limit:
            ids = ids[:args.limit]

    year_filter = None
    if args.years:
        year_filter = {int(y) for y in args.years.split(",") if y.strip()}

    series = ALL_SERIES
    if args.series:
        series = [s.strip() for s in args.series.split(",") if s.strip() in SERIES_FN]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Pulling {len(ids)} unitids | series={series} | "
          f"years={'all coverage' if not year_filter else sorted(year_filter)}")

    rows = []
    for name in series:
        years = list(COVERAGE[name])
        if year_filter is not None:
            years = [y for y in years if y in year_filter]
        if not years:
            print(f"  [{name}] no years in range -> skip")
            continue
        print(f"  [{name}] years {years[0]}-{years[-1]} "
              f"({len(years)} yr x {len(list(batches(ids)))} batches)")
        before = len(rows)
        for row in SERIES_FN[name](ids, years):
            rows.append(row)
        print(f"  [{name}] +{len(rows) - before} rows")

    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unitid", "year", "variable", "value"])
        w.writerows(rows)

    distinct_vars = sorted({r[2] for r in rows})
    distinct_uids = len({r[0] for r in rows})
    print(f"\nWrote {out_path} : {len(rows)} rows, "
          f"{distinct_uids} unitids, {len(distinct_vars)} variables")
    print("variables:", ", ".join(distinct_vars))
    return 0


if __name__ == "__main__":
    sys.exit(main())
