#!/usr/bin/env python3
"""Tests for data_pipeline/match_usn.py output.

Validates that known schools map to their correct IPEDS UNITIDs, that regional
schools match, that duplicate-name / ambiguous schools land in the review file,
and that overall match coverage and Reiter ground-truth agreement stay high.

Run: python test_scripts/test_match_usn.py
"""
import csv
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "usn_categories.csv")
REVIEW = os.path.join(REPO, "data", "usn_match_review.csv")


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def find(rows, name, category=None):
    for r in rows:
        if r["name"] == name and (category is None or r["category"] == category):
            return r
    return None


def main():
    # (Re)generate outputs so the test exercises the current matcher.
    subprocess.run([sys.executable, os.path.join(REPO, "data_pipeline", "match_usn.py")],
                   check=True, cwd=REPO, stdout=subprocess.DEVNULL)

    rows = load(OUT)
    review = load(REVIEW)
    review_names = {r["usn_name"] for r in review}
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # 1) National anchors (Reiter ground truth)
    pr = find(rows, "Princeton University", "national-universities")
    check(pr and pr["unitid"] == "186131", f"Princeton should map to 186131, got {pr and pr['unitid']}")

    wi = find(rows, "Williams College", "national-liberal-arts-colleges")
    check(wi and wi["unitid"] == "168342", f"Williams should map to 168342, got {wi and wi['unitid']}")

    # 2) Regional schools match to a unitid
    er = find(rows, "Embry-Riddle Aeronautical University--Prescott", "regional-colleges-west")
    check(er and er["unitid"] == "104586", f"Embry-Riddle Prescott should map to 104586, got {er and er['unitid']}")

    hp = find(rows, "High Point University", "regional-colleges-south")
    check(hp and hp["unitid"] == "198695", f"High Point should map to 198695, got {hp and hp['unitid']}")

    cp = find(rows, "California Polytechnic State University--San Luis Obispo",
              "regional-universities-west")
    check(cp and cp["unitid"] == "110422", f"Cal Poly SLO should map to 110422, got {cp and cp['unitid']}")

    # 3) Branch campus whose state was lost in scraping is recovered, and maps to
    #    the SPECIFIC branch (city-consistent), never the main campus (214777).
    ps = find(rows, "Pennsylvania State University -- Scranton", "regional-colleges-north")
    check(ps and ps["unitid"] == "214652",
          f"Penn State Scranton should map to 214652, got {ps and ps['unitid']}")

    for nm, uid in [("Pennsylvania State University -- Beaver", "214698"),
                    ("Pennsylvania State University--Altoona", "214689"),
                    ("Pennsylvania State University -- York", "214829")]:
        b = find(rows, nm, "regional-colleges-north")
        check(b and b["unitid"] == uid,
              f"{nm} should map to its branch {uid}, got {b and b['unitid']}")
        check(b and b["unitid"] != "214777",
              f"{nm} must NOT map to the Penn State main campus 214777")

    # 3b) "University of Colorado Denver" (Denver, CO) must NOT collapse onto the
    #     short subset name "University of Denver" (127060); it should resolve to
    #     a CU-Denver unitid (126562).
    cud = find(rows, "University of Colorado Denver", "national-universities")
    check(cud and cud["unitid"] != "127060",
          f"CU Denver must not map to University of Denver 127060, got {cud and cud['unitid']}")
    check(cud and cud["unitid"] == "126562",
          f"CU Denver should map to CU-Denver 126562, got {cud and cud['unitid']}")

    # 3c) CSU Long Beach / Fullerton are NOT swapped: trust the exact location
    #     match over the (swapped) Reiter ground-truth rows.
    lb = find(rows, "California State University, Long Beach", "national-universities")
    check(lb and lb["unitid"] == "110583",
          f"CSU Long Beach should map to 110583, got {lb and lb['unitid']}")
    fu = find(rows, "California State University--Fullerton", "national-universities")
    check(fu and fu["unitid"] == "110565",
          f"CSU Fullerton should map to 110565, got {fu and fu['unitid']}")

    # 3d) Extra-token school: "Southwestern Assemblies of God University" must not
    #     auto-bind to "Southwestern University" (228343); it is flagged and, via
    #     its unique city, recovered as IPEDS 228325 (renamed Nelson University).
    sw = find(rows, "Southwestern Assemblies of God University", "regional-universities-west")
    check(sw and sw["unitid"] != "228343",
          f"SAGU must not map to Southwestern University 228343, got {sw and sw['unitid']}")
    check("Southwestern Assemblies of God University" in review_names,
          "SAGU should be flagged for review")

    # 3e) A branch campus with no IPEDS counterpart must be flagged, never bound
    #     to the main campus (College Station 228723).
    tv = find(rows, "Texas A&M University--Victoria", "regional-universities-west")
    check(tv and tv["unitid"] != "228723",
          f"Texas A&M Victoria must not map to College Station 228723, got {tv and tv['unitid']}")
    check("Texas A&M University--Victoria" in review_names,
          "Texas A&M Victoria should be flagged for review")

    # 4) Duplicate-name school is disambiguated to the CORRECT campus by rank +
    #    city (not collapsed onto one). "Wheaton College" is IL 149781 (rank 50)
    #    and MA 168281 (rank 76); each must land on its own distinct unitid.
    wh = [r for r in rows if r["name"] == "Wheaton College"
          and r["category"] == "national-liberal-arts-colleges"]
    wh_ids = {r["rank"]: r["unitid"] for r in wh}
    check(wh_ids.get("50") == "149781",
          f"Wheaton (IL, rank 50) should map to 149781, got {wh_ids.get('50')}")
    check(wh_ids.get("76") == "168281",
          f"Wheaton (MA, rank 76) should map to 168281, got {wh_ids.get('76')}")

    # 5) Coverage: essentially every row should get a unitid (only Spanish-named
    #    PR institutions are expected to be unmatchable English->Spanish).
    matched = sum(1 for r in rows if r["unitid"])
    rate = matched / len(rows)
    check(rate >= 0.99, f"Match rate should be >= 99%, got {rate:.3%} ({matched}/{len(rows)})")

    # 6) Every Reiter-confirmed/ground-truth row carries a unitid.
    gt = [r for r in rows if r["match_method"].startswith("reiter")]
    check(all(r["unitid"] for r in gt), "All Reiter ground-truth rows must have a unitid")
    check(len(gt) >= 250, f"Expected >=250 Reiter-backed national rows, got {len(gt)}")

    # 7) Review file holds only non-clean matches: never a plain exact or a
    #    clean Reiter-confirmed row (those need no human attention). High-
    #    confidence rows are allowed only when fuzzy disagreed with ground truth.
    clean = {"exact_name_state", "exact_name_state_city", "core_name_state",
             "core_name_state_city", "reiter_confirmed"}
    check(all(r["match_method"] not in clean for r in review),
          "Review file should not contain cleanly auto-matched rows")

    if failures:
        print("FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print(f"All assertions passed. rows={len(rows)} matched={matched} "
          f"({rate:.1%}) review={len(review)} reiter_backed={len(gt)}")


if __name__ == "__main__":
    main()
