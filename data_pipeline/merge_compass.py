"""Merge the Compass premium layer (data/compass_profiles.csv) into
institutions_master.csv as US-News-sourced columns at the 2024 cohort year.

Non-destructive: adds new `usn_*` columns (no existing column is modified), so
the RawData/IPEDS/Scorecard layers stay intact and the US-News 2024 layer is
clearly source-attributed. Schools lacking a 2024 row get one created.

Year-stamp: Compass 2026 edition == fall-2024 admissions cohort (verified via
IPEDS applicant match), so these land at year 2024.
"""
import csv, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(REPO, "data", "institutions_master.csv")
COMPASS = os.path.join(REPO, "data", "compass_profiles.csv")
YEAR = "2024"

# compass column -> new master column
MAP = {
    "gpa_avg": "usn_gpa_avg",
    "gpa_25_75": "usn_gpa_25_75",
    "pct_top10_hs": "usn_top10_hs",
    "pct_submit_gpa": "usn_pct_submit_gpa",
    "median_sat": "usn_median_sat",
    "median_act": "usn_median_act",
    "acceptance_rate": "usn_acceptance_rate",
    "avg_need_grant_ug": "usn_avg_need_grant_ug",
    "pct_receiving_need_aid": "usn_pct_receiving_need_aid",
    "avg_merit_grant_ug": "usn_avg_merit_grant_ug",
    "pct_demonstrated_need": "usn_demonstrated_need",
    "pct_need_met": "usn_need_met",
    "commuter_pct": "usn_commuter_pct",
    "pct_pell": "usn_pct_pell",
    "pct_first_gen": "usn_pct_first_gen",
    "pct_international": "usn_pct_international",
    "pct_instate": "usn_pct_instate",
}
NEWCOLS = list(MAP.values())


def clean(v):
    v = (v or "").strip()
    if v == "" or "N/A" in v.upper():
        return ""
    return v


def main():
    comp = {}
    for r in csv.DictReader(open(COMPASS)):
        if not r["unitid"]:
            continue
        comp[r["unitid"]] = {dst: clean(r.get(src, "")) for src, dst in MAP.items()}
        comp[r["unitid"]]["_name"] = r.get("name", "")

    with open(MASTER) as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)
    outcols = cols + [c for c in NEWCOLS if c not in cols]

    filled = set()
    for r in rows:
        for c in NEWCOLS:
            r.setdefault(c, "")
        if r["year"] == YEAR and r["unitid"] in comp:
            for c in NEWCOLS:
                r[c] = comp[r["unitid"]][c]
            filled.add(r["unitid"])

    # create a 2024 row for compass schools that had none
    created = 0
    for uid, vals in comp.items():
        if uid in filled:
            continue
        newrow = {c: "" for c in outcols}
        newrow["unitid"] = uid
        newrow["year"] = YEAR
        newrow["name"] = vals["_name"]
        for c in NEWCOLS:
            newrow[c] = vals[c]
        rows.append(newrow)
        created += 1

    with open(MASTER, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=outcols)
        w.writeheader()
        w.writerows(rows)

    print(f"columns: {len(cols)} -> {len(outcols)} (+{len(outcols)-len(cols)} usn_ cols)")
    print(f"rows: {len(rows)} (created {created} new 2024 rows)")
    print(f"schools with US-News 2024 data: {len(filled) + created}")


if __name__ == "__main__":
    main()
