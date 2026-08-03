#!/usr/bin/env python3
"""Build the Next.js app dataset: web/data/institutions.json.

This is the data-layer swap the app was designed for. It JOINS, on unitid:

  * the LEGACY computed value-added fields from web/data/university_data.json
    ("VA Retention", "VA Graduation", "VAdistance", "US News Rank",
    "Retention Rate", "Graduation Rate", nationalu, pubpriv, region) -- these
    residuals are NOT present in the merged data and VAM/VAI depend on them, so
    they MUST be preserved verbatim; and

  * the 33+ canonical analytical variables from data/institutions_master.csv
    (unitid x year), each carried in as the LATEST AVAILABLE value: the value
    from the most recent year in which that specific variable is non-null. The
    sourcing year is recorded per-variable in `metricYears` so the snapshot is
    as complete as possible even when different variables peak in different
    years.

Output: one record per in-scope unitid (the 1,249 in university_data.json).
Schools in the legacy file but absent from the master CSV keep their VA fields
and simply carry no new metrics (reported at the end).

Re-runnable: reads from data/ + web/data/, writes web/data/institutions.json.
Does NOT modify any input file.
"""

from __future__ import annotations

import csv
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_CSV = os.path.join(REPO_ROOT, "data", "institutions_master.csv")
LEGACY_JSON = os.path.join(REPO_ROOT, "web", "data", "university_data.json")
DIRECTORY_CSV = os.path.join(REPO_ROOT, "data", "ipeds_directory.csv")
OUT_JSON = os.path.join(REPO_ROOT, "web", "data", "institutions.json")

# The 33+ canonical analytical variables in institutions_master.csv. Order here
# is the order they appear in the output metrics bag. Everything else in the CSV
# is identity / directory meta (handled separately) or join keys.
CANONICAL_VARS = [
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
    "pct_minority",
    "net_price_0_30k",
    "net_price_30_48k",
    "net_price_48_75k",
    "net_price_75_110k",
    "net_price_110k_plus",
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

# Directory meta columns we pull "latest non-null" from the master CSV.
DIRECTORY_META = ["name", "state", "region", "control"]

# IPEDS OBEREG / BEA region codes -> the human-readable names the legacy data
# (and the VAM region filter) already use. Verified 1:1 against the legacy
# region strings for in-scope unitids.
REGION_CODE_TO_NAME = {
    "0": "Service Schools",
    "1": "New England",
    "2": "Mid East",
    "3": "Great Lakes",
    "4": "Plains",
    "5": "Southeast",
    "6": "Southwest",
    "7": "Rocky Mountains",
    "8": "Far West",
    "9": "Outlying Areas",
}


def parse_float(value: str | None):
    """CSV cell -> float, or None for blanks / non-numeric."""
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_legacy() -> dict[int, dict]:
    with open(LEGACY_JSON, encoding="utf-8") as f:
        rows = json.load(f)
    return {int(r["UNITID"]): r for r in rows}


def load_directory() -> dict[int, dict]:
    """ipeds_directory.csv -> {unitid: {latitude, longitude, city}}.

    The directory carries one row per unitid with point coordinates (and city)
    used to plot each institution on the Atlas map. ~21 in-scope schools have no
    directory row; those simply get null coordinates downstream.
    """
    by_unitid: dict[int, dict] = {}
    with open(DIRECTORY_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                unitid = int(row["unitid"])
            except (KeyError, ValueError):
                continue
            by_unitid[unitid] = {
                "latitude": parse_float(row.get("latitude")),
                "longitude": parse_float(row.get("longitude")),
                "city": (row.get("city") or "").strip() or None,
            }
    return by_unitid


def collect_master(in_scope: set[int]):
    """Scan the master CSV once, keeping, per in-scope unitid:

      * latest[var]      -> most-recent non-null value for each canonical var
      * latest_year[var] -> the year that value came from
      * meta[col]        -> latest non-null directory value
    """
    latest: dict[int, dict[str, float]] = {}
    latest_year: dict[int, dict[str, int]] = {}
    meta: dict[int, dict[str, str]] = {}
    meta_year: dict[int, dict[str, int]] = {}

    with open(MASTER_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            # The master carries some rows with no unitid — historic RawData
            # schools that never matched the IPEDS directory. They are kept in
            # the CSV on purpose (data preservation) but cannot be keyed here.
            raw_uid = (row.get("unitid") or "").strip()
            if not raw_uid.isdigit():
                continue
            unitid = int(raw_uid)
            if unitid not in in_scope:
                continue
            year = int(row["year"])

            lv = latest.setdefault(unitid, {})
            ly = latest_year.setdefault(unitid, {})
            for var in CANONICAL_VARS:
                v = parse_float(row.get(var))
                if v is None:
                    continue
                if var not in ly or year >= ly[var]:
                    lv[var] = v
                    ly[var] = year

            mv = meta.setdefault(unitid, {})
            my = meta_year.setdefault(unitid, {})
            for col in DIRECTORY_META:
                raw = (row.get(col) or "").strip()
                if raw == "":
                    continue
                if col not in my or year >= my[col]:
                    mv[col] = raw
                    my[col] = year

    return latest, latest_year, meta


def num(v):
    """Legacy JSON value -> float/None, dropping NaN-ish entries."""
    if isinstance(v, (int, float)):
        return v
    return None


def build():
    legacy = load_legacy()
    in_scope = set(legacy.keys())
    latest, latest_year, meta = collect_master(in_scope)
    directory = load_directory()

    records = []
    missing_master: list[int] = []
    missing_coords: list[int] = []

    for unitid in sorted(in_scope):
        leg = legacy[unitid]
        dir_meta = meta.get(unitid, {})
        var_vals = latest.get(unitid, {})
        var_years = latest_year.get(unitid, {})

        if unitid not in latest:
            missing_master.append(unitid)

        # Geocoordinates + city from the IPEDS directory (one row per unitid).
        # Schools absent from the directory get null lat/lng/city and are
        # skipped by the map's projection downstream.
        dir_row = directory.get(unitid, {})
        latitude = dir_row.get("latitude")
        longitude = dir_row.get("longitude")
        city = dir_row.get("city")
        if latitude is None or longitude is None:
            missing_coords.append(unitid)

        # Identity: name prefers legacy (display continuity); state/region
        # prefer directory (master CSV) and fall back to legacy.
        name = leg.get("Name") or dir_meta.get("name") or "(Unnamed)"
        state = dir_meta.get("state") or leg.get("state")
        region_code = dir_meta.get("region")
        region = REGION_CODE_TO_NAME.get(region_code) if region_code else None
        if region is None:
            region = leg.get("region")

        metrics: dict[str, object] = {
            # --- LEGACY computed value-added fields (preserved verbatim) ---
            "vaRetention": num(leg.get("VA Retention")),
            "vaGraduation": num(leg.get("VA Graduation")),
            "vaDistance": num(leg.get("VAdistance")),
            "usNewsRank": num(leg.get("US News Rank")),
            "retentionRate": num(leg.get("Retention Rate")),
            "graduationRate": num(leg.get("Graduation Rate")),
        }
        # --- New canonical variables: latest available value, native scale ---
        metric_years: dict[str, int] = {}
        for var in CANONICAL_VARS:
            if var in var_vals:
                metrics[var] = var_vals[var]
                metric_years[var] = var_years[var]
            else:
                metrics[var] = None

        records.append(
            {
                "unitid": unitid,
                "name": name,
                "state": state,
                "region": region,
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                # pubpriv: 1 = public, 2 = private (legacy encoding kept so the
                # data.ts seam derives publicPrivate exactly as before).
                "pubpriv": leg.get("pubpriv"),
                "national": leg.get("nationalu"),
                "metrics": metrics,
                "metricYears": metric_years,
            }
        )

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    print(f"Wrote {len(records)} records -> {OUT_JSON}")
    print(f"In-scope unitids: {len(in_scope)}")
    print(f"Matched in master CSV: {len(in_scope) - len(missing_master)}")
    print(f"With coordinates: {len(in_scope) - len(missing_coords)}")
    if missing_coords:
        print(f"NO coordinates (null lat/lng, skipped on map): {len(missing_coords)}")
    if missing_master:
        names = ", ".join(legacy[u].get("Name", str(u)) for u in missing_master[:20])
        print(f"NOT in master (kept VA only, no new metrics): {len(missing_master)}")
        print(f"  {names}{' ...' if len(missing_master) > 20 else ''}")
    return records


if __name__ == "__main__":
    recs = build()
    # tiny sanity print for spot-checking
    for r in recs:
        if "Princeton" in r["name"]:
            m = r["metrics"]
            print(
                "Princeton:",
                "acceptance_rate=", m.get("acceptance_rate"),
                "net_price_0_30k=", m.get("net_price_0_30k"),
                "sat75_math=", m.get("sat75_math"),
                "grad_rate_6yr=", m.get("grad_rate_6yr"),
                "vaRetention=", m.get("vaRetention"),
            )
            break
    sys.exit(0)
