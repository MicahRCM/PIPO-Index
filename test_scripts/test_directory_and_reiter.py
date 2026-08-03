#!/usr/bin/env python3
"""Smoke tests for build_directory.py + ingest_reiter.py outputs.

Run AFTER both pipeline scripts have produced their CSVs:
    python3 data_pipeline/build_directory.py
    python3 data_pipeline/ingest_reiter.py
    python3 test_scripts/test_directory_and_reiter.py
"""
import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    d = load("data/ipeds_directory.csv")
    assert len(d) >= 6000, f"directory too small: {len(d)}"
    uab = next(r for r in d if r["unitid"] == "100663")
    assert uab["name"] == "University of Alabama at Birmingham", uab["name"]
    assert uab["city"] == "Birmingham" and uab["state"] == "AL", uab
    assert all(r["city"] and r["state"] and r["zip"] for r in d[:50]), "missing join keys"

    h = load("data/usn_rank_history.csv")
    assert len(h) > 5000, f"rank history too small: {len(h)}"
    cats = {r["category"] for r in h}
    assert cats == {"national_universities", "national_liberal_arts"}, cats

    def rank(name, cat, year):
        return next(int(r["rank"]) for r in h
                    if r["name"].startswith(name) and r["category"] == cat and r["year"] == year)

    assert rank("Williams", "national_liberal_arts", "2026") == 1
    assert rank("Princeton", "national_universities", "2026") == 1
    assert all(r["unitid"] for r in h), "expected UNITID on every Reiter row"

    print("ALL TESTS PASSED")
    print(f"  directory rows: {len(d)}")
    print(f"  rank-history rows: {len(h)}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("TEST FAILED:", e)
        sys.exit(1)
