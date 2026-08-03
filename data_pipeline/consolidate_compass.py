"""Consolidate the per-batch Compass JSON files into one clean CSV.

Reads every data/compass_raw/compass_b*.json, keeps records that actually
resolved (have a school name), joins usn_id -> unitid via compass_ids.csv, and
writes data/compass_profiles.csv (one row per school, deduped by usn_id).

Re-runnable: safe to run after each new batch to refresh the CSV.

Compass 2026 edition; cohort reference years vary by field (admissions/aid ~
2024-25 fall-2024 cohort, cost 2025-26, net price 2022-23) — see year note.
"""
import csv, glob, json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO, "data", "compass_raw")
IDS = os.path.join(RAW, "compass_ids.csv")
OUT = os.path.join(REPO, "data", "compass_profiles.csv")

# internal field -> output column
FIELDMAP = [
    ("gpa_avg", "gpa_avg"),
    ("gpa_range", "gpa_25_75"),
    ("top10", "pct_top10_hs"),
    ("pct_submit_gpa", "pct_submit_gpa"),
    ("median_sat", "median_sat"),
    ("median_act", "median_act"),
    ("acc_rate", "acceptance_rate"),
    ("avg_need_grant_ug", "avg_need_grant_ug"),
    ("pct_recv_need_ug", "pct_receiving_need_aid"),
    ("avg_merit_ug", "avg_merit_grant_ug"),
    ("pct_demonstrated_need", "pct_demonstrated_need"),
    ("pct_need_met", "pct_need_met"),
    ("commuter_pct", "commuter_pct"),
    ("pct_pell", "pct_pell"),
    ("first_gen", "pct_first_gen"),
    ("international_pct", "pct_international"),
    ("instate_pct", "pct_instate"),
]
OUTCOLS = ["unitid", "usn_id", "name", "compass_edition"] + [o for _, o in FIELDMAP]


def load_crosswalk():
    xw = {}
    with open(IDS) as f:
        for r in csv.DictReader(f):
            xw[r["usn_id"]] = r.get("unitid", "")
    return xw


def main():
    xw = load_crosswalk()
    rows = {}  # usn_id -> outrow (dedup, keep richest)
    files = sorted(glob.glob(os.path.join(RAW, "compass_b*.json")))
    for fp in files:
        data = json.load(open(fp))
        for rec in data.get("results", []):
            if not rec.get("name"):
                continue  # unresolved/failed record
            uid = rec["usn_id"]
            out = {"unitid": xw.get(uid, ""), "usn_id": uid,
                   "name": rec.get("name", ""), "compass_edition": "2026"}
            filled = 0
            for src, dst in FIELDMAP:
                v = rec.get(src, "")
                out[dst] = v if v not in (None,) else ""
                if out[dst] not in ("", None):
                    filled += 1
            # keep the record with more filled vars if duplicate usn_id
            if uid not in rows or filled > rows[uid][1]:
                rows[uid] = (out, filled)

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUTCOLS)
        w.writeheader()
        for out, _ in rows.values():
            w.writerow(out)

    # summary
    n = len(rows)
    print(f"wrote {n} schools -> data/compass_profiles.csv (from {len(files)} batch files)")
    fill = {dst: 0 for _, dst in FIELDMAP}
    for out, _ in rows.values():
        for _, dst in FIELDMAP:
            if out[dst] not in ("", None):
                fill[dst] += 1
    print("per-variable fill:")
    for _, dst in FIELDMAP:
        print(f"  {dst:24} {fill[dst]:>4}  ({fill[dst]*100//n}%)")


if __name__ == "__main__":
    main()
