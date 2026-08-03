#!/usr/bin/env python3
"""Append one US News category's scraped rows to data/usn_categories_raw.csv.

Usage: python append_usn_category.py <category_slug> <json_file>
The JSON file holds the extractor output: [{usnId,name,rank,loc="City, ST"}, ...]
Splits loc into city/state and appends rows. Creates the header if file is new.
"""
import csv
import json
import os
import sys

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "usn_categories_raw.csv")
HEADER = ["category", "rank", "usn_id", "name", "city", "state"]


def split_loc(loc):
    if not loc:
        return "", ""
    parts = loc.rsplit(",", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return loc.strip(), ""


def main():
    slug = sys.argv[1]
    with open(sys.argv[2]) as f:
        data = json.load(f)
    rows = data["rows"] if isinstance(data, dict) and "rows" in data else data

    # Idempotent: drop any existing rows for this slug, then re-append.
    existing = []
    if os.path.exists(RAW) and os.path.getsize(RAW) > 0:
        with open(RAW, newline="") as f:
            rd = csv.reader(f)
            header = next(rd, None)
            existing = [row for row in rd if row and row[0] != slug]

    with open(RAW, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for row in existing:
            w.writerow(row)
        n = 0
        for r in rows:
            city, state = split_loc(r.get("loc"))
            w.writerow([slug, r.get("rank"), r.get("usnId"), r.get("name"), city, state])
            n += 1
    print(f"{slug}: wrote {n} rows (replaced any prior {slug} rows)")


if __name__ == "__main__":
    main()
