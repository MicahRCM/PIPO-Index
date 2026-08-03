#!/usr/bin/env python3
"""
build_directory.py — Build the IPEDS institutional-directory crosswalk.

Pulls the IPEDS HD (institutional directory) file from the Urban Institute
Education Data API (open, no API key):

    https://educationdata.urban.org/api/v1/college-university/ipeds/directory/{year}/

This directory is the authoritative crosswalk that US News ranking rows are
matched against (see PLAN.md section 4 — UNITID matching). It is keyed by
IPEDS UNITID and provides the join keys name + city + state + zip, plus alias
strings (`inst_alias`) so USN names that differ from the current IPEDS name can
still be matched.

Output: data/ipeds_directory.csv
Columns: unitid, name, alias, city, state, zip, control, control_detail,
         region, longitude, latitude
"""

import csv
import json
import os
import sys
import urllib.request
import urllib.error

BASE = "https://educationdata.urban.org/api/v1/college-university/ipeds/directory"
# Probe years from newest downward to confirm the latest available year.
CANDIDATE_YEARS = list(range(2026, 2014, -1))

# IPEDS inst_control code -> human label.
# 1 = Public, 2 = Private not-for-profit, 3 = Private for-profit.
CONTROL_DETAIL = {1: "public", 2: "private not-for-profit", 3: "private for-profit"}
CONTROL_SIMPLE = {1: "public", 2: "private", 3: "private"}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO, "data", "ipeds_directory.csv")


def fetch_json(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "PIPO-Index/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def latest_available_year():
    """Return the newest year whose directory endpoint returns rows."""
    for year in CANDIDATE_YEARS:
        url = f"{BASE}/{year}/?unitid=100663"
        try:
            data = fetch_json(url, timeout=40)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            print(f"  year {year}: probe failed ({e}) — skipping", file=sys.stderr)
            continue
        if data.get("count", 0) > 0:
            return year
        print(f"  year {year}: empty — trying older", file=sys.stderr)
    raise RuntimeError("No directory year returned data in candidate range")


def fetch_all_rows(year):
    """Fetch every directory row for `year`, following pagination if present."""
    rows = []
    url = f"{BASE}/{year}/"
    page = 0
    while url:
        page += 1
        print(f"  fetching page {page}: {url}", file=sys.stderr)
        data = fetch_json(url, timeout=180)
        rows.extend(data.get("results", []))
        url = data.get("next")
    return rows


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def main():
    print("Determining latest available IPEDS directory year...", file=sys.stderr)
    year = latest_available_year()
    print(f"Latest available directory year: {year}", file=sys.stderr)

    rows = fetch_all_rows(year)
    print(f"Fetched {len(rows)} institutions for {year}", file=sys.stderr)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fields = [
        "unitid", "name", "alias", "city", "state", "zip",
        "control", "control_detail", "region", "longitude", "latitude",
    ]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            ctrl = r.get("inst_control")
            writer.writerow({
                "unitid": clean(r.get("unitid")),
                "name": clean(r.get("inst_name")),
                # inst_alias is a pipe-ish delimited string of former/alt names.
                "alias": clean(r.get("inst_alias")),
                "city": clean(r.get("city")),
                "state": clean(r.get("state_abbr")),
                "zip": clean(r.get("zip")),
                "control": CONTROL_SIMPLE.get(ctrl, ""),
                "control_detail": CONTROL_DETAIL.get(ctrl, clean(ctrl)),
                "region": clean(r.get("region")),
                "longitude": clean(r.get("longitude")),
                "latitude": clean(r.get("latitude")),
            })

    print(f"Wrote {len(rows)} rows -> {OUT_PATH}")
    print(f"Directory year used: {year}")
    return year, len(rows)


if __name__ == "__main__":
    main()
