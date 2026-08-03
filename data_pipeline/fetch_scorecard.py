#!/usr/bin/env python3
"""
Pull every College Scorecard-sourced variable used by the PIPO-Index project
for the UNITIDs in university_data.json, across a range of IPEDS data-collection
years. Field paths and year-coverage gotchas come from
``data_pipeline/variable_sources.md`` (the authoritative source-of-truth map).

Data source: https://api.data.gov/ed/collegescorecard/v1/schools
Field paths use the per-year prefix ``{year}.<path>`` (e.g.
``2018.student.size``). One request is issued per (UNITID batch, year) so the
field count per request stays small enough to avoid the HTTP 500 the API throws
when too many year-suffixed fields are combined.

Outputs (both written to ``data/``):
  - scorecard_raw.csv   LONG  : unitid, year, variable, value
  - scorecard_wide.csv  WIDE  : unitid, year, <one column per variable>

Values are stored RAW exactly as the API returns them -- shares and rates are
fractions in [0, 1] (e.g. acceptance_rate 0.8854, pct_international 0.0233),
while scores / dollars / counts are absolute (sat75_math 708,
net_price_0_30k 13862, ug_size 13284). Nulls and negatives are skipped; values
are never invented.

Rate limits: data.gov DEMO_KEY allows ~30 req/hr (so only run the small built-in
test scope with it). A free personal key (https://api.data.gov/signup/) raises
this to ~1000 req/hr -- enough for the full 1,249-school x ~21-year pull.

Examples:
  # Small DEMO_KEY-safe smoke test (5 schools, 3 years):
  python3 data_pipeline/fetch_scorecard.py --test

  # Full pull with a personal key:
  COLLEGE_SCORECARD_API_KEY=xxxx python3 data_pipeline/fetch_scorecard.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNI_DATA = ROOT / "university_data.json"
OUT_DIR = ROOT / "data"
OUT_LONG = OUT_DIR / "scorecard_raw.csv"
OUT_WIDE = OUT_DIR / "scorecard_wide.csv"

BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"
PER_PAGE = 100  # API max; with batches of <=20 ids everything fits one page.

# Defaults. All overridable via CLI.
DEFAULT_START_YEAR = 2003
DEFAULT_END_YEAR = 2023          # latest broadly-populated collection year
DEFAULT_BATCH_SIZE = 20          # API 500s above ~22 ids w/ many year fields
DEFAULT_SLEEP = 0.3              # polite pause between requests (seconds)

# Well-known schools for the DEMO_KEY-safe smoke test.
TEST_UNITIDS = ["100663", "186131", "110635", "130794", "228778"]
TEST_YEARS = (2016, 2018)        # inclusive range -> 2016, 2017, 2018

# ---------------------------------------------------------------------------
# Field map.  column_name -> scorecard path (without the {year}. prefix).
# Paths follow data_pipeline/variable_sources.md.  Values returned RAW.
# ---------------------------------------------------------------------------
SIMPLE_FIELDS: dict[str, str] = {
    # 6-yr (150%-of-time) graduation rate, overall
    "grad_rate_6yr": "completion.completion_rate_4yr_150nt",
    # Pell graduation rate (non-Pell is computed below from two components)
    "grad_rate_pell": "completion.completion_rate_four_year_150_pell",
    # SAT 75th percentile
    "sat75_reading": "admissions.sat_scores.75th_percentile.critical_reading",
    "sat75_math": "admissions.sat_scores.75th_percentile.math",
    "sat75_writing": "admissions.sat_scores.75th_percentile.writing",
    # ACT 75th percentile
    "act75_cumulative": "admissions.act_scores.75th_percentile.cumulative",
    "act75_english": "admissions.act_scores.75th_percentile.english",
    "act75_math": "admissions.act_scores.75th_percentile.math",
    "act75_writing": "admissions.act_scores.75th_percentile.writing",
    # Acceptance rate
    "acceptance_rate": "admissions.admission_rate.overall",
    # Enrollment composition
    "pct_part_time": "student.part_time_share",
    # Race / ethnicity undergraduate shares (fractions 0-1)
    "race_white": "student.demographics.race_ethnicity.white",
    "race_black": "student.demographics.race_ethnicity.black",
    "race_hispanic": "student.demographics.race_ethnicity.hispanic",
    "race_asian": "student.demographics.race_ethnicity.asian",
    "race_aian": "student.demographics.race_ethnicity.aian",
    "race_nhpi": "student.demographics.race_ethnicity.nhpi",
    "race_two_or_more": "student.demographics.race_ethnicity.two_or_more",
    "race_unknown": "student.demographics.race_ethnicity.unknown",
    # % international == non-resident alien share
    "pct_international": "student.demographics.race_ethnicity.non_resident_alien",
    # % Pell
    "pct_pell": "aid.pell_grant_rate",
    # Median loan debt of completers (NSLDS; frozen/null in recent years)
    "median_debt": "aid.median_debt.completers.overall",
    # Cost / tuition
    "cost_attendance": "cost.attendance.academic_year",
    "tuition_in_state": "cost.tuition.in_state",
    "tuition_out_of_state": "cost.tuition.out_of_state",
    "avg_net_price_public": "cost.avg_net_price.public",
    "avg_net_price_private": "cost.avg_net_price.private",
    # Helpers
    "ug_size": "student.size",
    "retention_ft_4yr": "student.retention_rate.four_year.full_time",
}

# Non-Pell grad rate = loan_nopell + noloan_nopell (Scorecard has no single
# combined non-Pell completion rate; see variable_sources.md).
NONPELL_COMPONENTS = [
    "completion.completion_rate_four_year_150_loan_nopell",
    "completion.completion_rate_four_year_150_noloan_nopell",
]

# Net price by income band. Only ONE control suffix is populated per school
# (_PUB / _PRIV / _PROG / _OTHER). We request all controls for all bands and
# capture whichever is non-null into one net_price_<band> column.
NET_PRICE_CONTROLS = ["public", "private", "program_reporter", "other_academic_year"]
NET_PRICE_BANDS = {
    "net_price_0_30k": "0-30000",
    "net_price_30_48k": "30001-48000",
    "net_price_48_75k": "48001-75000",
    "net_price_75_110k": "75001-110000",
    "net_price_110k_plus": "110001-plus",
}

# Stable output column order for the wide CSV / LONG variable enumeration.
VARIABLE_ORDER = (
    list(SIMPLE_FIELDS.keys())[:2]            # grad_rate_6yr, grad_rate_pell
    + ["grad_rate_nonpell"]
    + list(SIMPLE_FIELDS.keys())[2:]          # everything else
    + list(NET_PRICE_BANDS.keys())
)


def net_price_path(control: str, band_key: str) -> str:
    return f"cost.net_price.{control}.by_income_level.{band_key}"


def all_paths() -> list[str]:
    """Every scorecard path (sans year prefix) we need to request."""
    paths = list(SIMPLE_FIELDS.values()) + list(NONPELL_COMPONENTS)
    for control in NET_PRICE_CONTROLS:
        for band_key in NET_PRICE_BANDS.values():
            paths.append(net_price_path(control, band_key))
    return paths


def build_url(ids: list[str], year: int, page: int, api_key: str) -> str:
    fields = ["id"] + [f"{year}.{p}" for p in all_paths()]
    params = {
        "id": ",".join(ids),
        "fields": ",".join(fields),
        "per_page": str(PER_PAGE),
        "page": str(page),
        "api_key": api_key,
    }
    return BASE + "?" + urllib.parse.urlencode(params)


def _num(v) -> float | None:
    """Coerce to a usable number, or None if null/negative/non-numeric."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v if v >= 0 else None
    return None


def parse_row(row: dict, year: int) -> dict[str, float]:
    """Extract {variable: value} for a single school-year result row."""
    out: dict[str, float] = {}

    for col, path in SIMPLE_FIELDS.items():
        v = _num(row.get(f"{year}.{path}"))
        if v is not None:
            out[col] = v

    # Non-Pell grad rate = sum of the two no-Pell components (both required).
    a = _num(row.get(f"{year}.{NONPELL_COMPONENTS[0]}"))
    b = _num(row.get(f"{year}.{NONPELL_COMPONENTS[1]}"))
    if a is not None and b is not None:
        out["grad_rate_nonpell"] = round(a + b, 6)

    # Net price control-suffix branch: take whichever control is populated.
    for col, band_key in NET_PRICE_BANDS.items():
        for control in NET_PRICE_CONTROLS:
            v = _num(row.get(f"{year}.{net_price_path(control, band_key)}"))
            if v is not None:
                out[col] = v
                break

    return out


def fetch_batch_year(
    ids: list[str], year: int, api_key: str, sleep: float
) -> dict[int, dict[str, float]]:
    """Return {unitid: {variable: value}} for one batch in one year."""
    out: dict[int, dict[str, float]] = {}
    page = 0
    while True:
        url = build_url(ids, year, page, api_key)
        payload = None
        for attempt in range(8):
            try:
                with urllib.request.urlopen(url, timeout=120) as resp:
                    payload = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503):  # rate-limited / temporarily unavailable
                    retry_after = e.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait = min(int(retry_after) + 2, 3700)
                    else:
                        wait = min(30 * (attempt + 1), 300)
                    print(
                        f"  HTTP {e.code} year={year} page={page}: rate-limited, "
                        f"waiting {wait}s (attempt {attempt + 1}/8)",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                body = e.read()[:300]
                print(
                    f"  HTTP {e.code} year={year} page={page}: {body!r}",
                    file=sys.stderr,
                )
                raise
            except (urllib.error.URLError, TimeoutError) as e:  # transient network
                wait = min(10 * (attempt + 1), 60)
                print(
                    f"  network error year={year} page={page}: {e}; "
                    f"retry in {wait}s (attempt {attempt + 1}/8)",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
        if payload is None:
            raise RuntimeError(
                f"failed after retries: year={year} page={page}"
            )
        for row in payload.get("results", []):
            uid = int(row["id"])
            vals = parse_row(row, year)
            if vals:
                out.setdefault(uid, {}).update(vals)
        total = payload.get("metadata", {}).get("total", 0)
        if (page + 1) * PER_PAGE >= total:
            break
        page += 1
        time.sleep(sleep)
    return out


def load_unitids(limit: int | None) -> list[str]:
    with UNI_DATA.open() as f:
        unis = json.load(f)
    ids = [str(u["UNITID"]) for u in unis if u.get("UNITID") is not None]
    return ids[:limit] if limit else ids


def write_outputs(records: dict[tuple[int, int], dict[str, float]]) -> tuple[int, int]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # LONG
    long_rows = 0
    with OUT_LONG.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unitid", "year", "variable", "value"])
        for (uid, year) in sorted(records):
            vals = records[(uid, year)]
            for var in VARIABLE_ORDER:
                if var in vals:
                    w.writerow([uid, year, var, vals[var]])
                    long_rows += 1

    # WIDE
    with OUT_WIDE.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unitid", "year"] + VARIABLE_ORDER)
        for (uid, year) in sorted(records):
            vals = records[(uid, year)]
            w.writerow([uid, year] + [vals.get(v, "") for v in VARIABLE_ORDER])

    return long_rows, len(records)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test", action="store_true",
                   help="DEMO_KEY-safe smoke test: 5 known schools, 2016-2018.")
    p.add_argument("--unitids", default=None,
                   help="Comma-separated UNITIDs (default: all in university_data.json).")
    p.add_argument("--limit", type=int, default=None,
                   help="Only the first N UNITIDs (quick partial runs).")
    p.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    p.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    p.add_argument("--api-key", default=None,
                   help="Override the COLLEGE_SCORECARD_API_KEY env var.")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    api_key = args.api_key or os.environ.get("COLLEGE_SCORECARD_API_KEY", "DEMO_KEY")

    if args.test:
        unitids = TEST_UNITIDS
        start_year, end_year = TEST_YEARS
    else:
        if args.unitids:
            unitids = [s.strip() for s in args.unitids.split(",") if s.strip()]
        else:
            if not UNI_DATA.exists():
                print(f"missing {UNI_DATA}", file=sys.stderr)
                return 1
            unitids = load_unitids(args.limit)
        start_year, end_year = args.start_year, args.end_year

    years = list(range(start_year, end_year + 1))
    batch_size = args.batch_size
    n_batches = (len(unitids) + batch_size - 1) // batch_size
    total_requests = n_batches * len(years)

    key_label = "DEMO_KEY" if api_key == "DEMO_KEY" else "personal key"
    print(f"Scorecard pull: {len(unitids)} schools x {len(years)} years "
          f"({years[0]}-{years[-1]}), batch={batch_size} -> "
          f"~{total_requests} requests via {key_label}.")
    if api_key == "DEMO_KEY" and total_requests > 25:
        print("WARNING: this scope will exceed the DEMO_KEY ~30 req/hr cap. "
              "Use --test or supply a personal key.", file=sys.stderr)

    records: dict[tuple[int, int], dict[str, float]] = {}
    req = 0
    for year in years:
        for i in range(0, len(unitids), batch_size):
            batch = unitids[i:i + batch_size]
            req += 1
            print(f"  [{req}/{total_requests}] year={year} "
                  f"ids {i + 1}-{i + len(batch)}")
            batch_data = fetch_batch_year(batch, year, api_key, args.sleep)
            for uid, vals in batch_data.items():
                # Each (uid, year) is produced exactly once, so assign directly.
                records[(uid, year)] = vals
            time.sleep(args.sleep)
        # Checkpoint after each year so a long run can't lose accumulated data.
        write_outputs(records)
        print(f"  checkpoint after year {year}: {len(records)} school-year rows")

    long_rows, wide_rows = write_outputs(records)
    schools = len({uid for uid, _ in records})
    print(f"\nWrote {OUT_LONG.relative_to(ROOT)} ({long_rows} value rows) and "
          f"{OUT_WIDE.relative_to(ROOT)} ({wide_rows} school-year rows).")
    print(f"Populated data for {schools} distinct schools.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
