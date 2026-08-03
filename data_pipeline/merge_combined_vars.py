"""Match CombinedMoreVariables.csv (School, State, + 6 variables) to IPEDS unitid
and merge all variables into institutions_master.csv at year 2024.

Reuses the (name, state) matcher from match_sat75.py. This file additionally has
~64 rows where the State cell is blank (all in the Regional categories), so for
those we fall back to a STATE-AGNOSTIC exact/loose match (their names are
nationally unique — verified 58/64 unique, 0 ambiguous) plus a small name-only
override table for the 6 heavily-abbreviated ones.

Columns merged at year 2024 (source -> master), source-tagged `_combined`:
  SAT75th P                                  -> sat75_combined         (numeric)
  Category                                   -> category_combined      (text)
  Peer Assessment Score                      -> peer_assessment_combined (float)
  Social Mobility Rank                       -> social_mobility_rank_combined (int)
  Median Debt for Grads with Federal Loans   -> median_debt_combined    ($ stripped)
  % Earning More Than Typical HS Grad        -> pct_earn_above_hs_combined (% stripped)

Usage:
  python3 data_pipeline/merge_combined_vars.py            # report
  python3 data_pipeline/merge_combined_vars.py --apply    # + merge into master
"""
import argparse, csv, importlib.util, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = Path("/Users/peacespherical/Documents/Higher Ed Labs/CombinedMoreVariables.csv")
MASTER = REPO / "data" / "institutions_master.csv"
BACKUP = REPO / "data" / "institutions_master.pre_combined.csv"
XW = REPO / "data" / "combined_vars_crosswalk.csv"
REVIEW = REPO / "data" / "combined_vars_unmatched.csv"
YEAR = "2024"

# reuse the matcher
_spec = importlib.util.spec_from_file_location("match_sat75", REPO / "data_pipeline" / "match_sat75.py")
M = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(M)

# name-only unitids for the abbreviated schools that appear here with BLANK state
NAME_OVERRIDES = {
    "Pontifical Catholic U. of PR–Mayaguez": "243586",
    "Inter American U. of PR–Barranquitas": "242644",
    "Inter American U. of PR–Metropo. Campus": "242653",
    "William Paterson University of N.J.": "187444",
    "The Citadel, Military College of SC": "217864",
    "Cal. Polytech. State U.–San Luis Obispo": "110422",
}

COLMAP = [
    ("SAT75th P", "sat75_combined"),
    ("Category", "category_combined"),
    ("Peer Assessment Score", "peer_assessment_combined"),
    ("Social Mobility Rank", "social_mobility_rank_combined"),
    ("Median Debt for Grads with Federal Loans", "median_debt_combined"),
    ("% Earning More Than Typical HS Grad", "pct_earn_above_hs_combined"),
]
NEWCOLS = [dst for _, dst in COLMAP]


def clean(v):
    v = (v or "").strip().replace("$", "").replace(",", "").replace("%", "").strip()
    if v.upper() in ("", "N/A", "NA", "-", "--"):
        return ""
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    exact, loose, name_of = M.build_refs()
    kbs = M.keys_by_state_index(exact)
    # state-agnostic collapse for blank-state rows
    sa_exact, sa_loose = {}, {}
    for (st, k), u in exact.items():
        sa_exact.setdefault(k, set()).update(u)
    for (st, k), u in loose.items():
        sa_loose.setdefault(k, set()).update(u)

    def resolve(school, st):
        if st:
            uid, method = M.match_one(school, st, exact, loose, kbs)
            if uid:
                return uid, method
        nk, lk = M.norm(school), M.norm_campus(school)
        if nk in sa_exact and len(sa_exact[nk]) == 1:
            return next(iter(sa_exact[nk])), "exact_nostate"
        if lk in sa_loose and len(sa_loose[lk]) == 1:
            return next(iter(sa_loose[lk])), "loose_nostate"
        if school in NAME_OVERRIDES:
            return NAME_OVERRIDES[school], "manual_name"
        return None, None

    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    matched, review = [], []          # matched: (unitid, {dst:val}, school, method)
    for r in rows:
        school = (r.get("School") or "").strip()
        st = (r.get("State") or "").strip()
        uid, method = resolve(school, st)
        vals = {dst: clean(r.get(src, "")) for src, dst in COLMAP}
        if uid:
            matched.append((uid, vals, school, method))
        else:
            review.append((school, st))

    # collision check
    from collections import Counter
    dup = {u: n for u, n in Counter(m[0] for m in matched).items() if n > 1}

    by_method = Counter(m[3].split(":")[0] for m in matched)
    print(f"source rows: {len(rows)}")
    print(f"  matched to unitid: {len(matched)}")
    print(f"  unmatched: {len(review)}  {[r[0] for r in review]}")
    print(f"  by method: {dict(by_method)}")
    print(f"  collisions (unitid used by >1 row): {len(dup)}  {dup}")
    print("  per-variable non-blank among matched:")
    for _, dst in COLMAP:
        print(f"    {dst:32} {sum(1 for m in matched if m[1][dst])}")

    with XW.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["school", "unitid", "method"] + NEWCOLS)
        for uid, vals, school, method in matched:
            w.writerow([school, uid, method] + [vals[c] for c in NEWCOLS])
    with REVIEW.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["school", "state"]); w.writerows(review)

    if not args.apply:
        print("\n(no --apply: master not modified)")
        return

    uid_vals = {m[0]: m[1] for m in matched}
    with MASTER.open() as f:
        rd = csv.DictReader(f); cols = rd.fieldnames; mrows = list(rd)
    outcols = cols + [c for c in NEWCOLS if c not in cols]

    filled = created = 0
    sat_changed = 0
    seen24 = set()
    for r in mrows:
        for c in NEWCOLS:
            r.setdefault(c, "")
        if r["year"] == YEAR and r["unitid"] in uid_vals:
            v = uid_vals[r["unitid"]]
            if v["sat75_combined"] and r.get("sat75_combined", "") and v["sat75_combined"] != r["sat75_combined"]:
                sat_changed += 1
            for c in NEWCOLS:
                if v[c]:
                    r[c] = v[c]
            filled += 1; seen24.add(r["unitid"])
    for uid, v in uid_vals.items():
        if uid not in seen24:
            nr = {c: "" for c in outcols}
            nr["unitid"] = uid; nr["year"] = YEAR; nr["name"] = name_of.get(uid, "")
            for c in NEWCOLS:
                nr[c] = v[c]
            mrows.append(nr); created += 1

    shutil.copy2(MASTER, BACKUP)
    with MASTER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=outcols)
        w.writeheader(); w.writerows(mrows)
    print(f"\nbacked up -> {BACKUP.name}")
    print(f"merged at {YEAR}: filled {filled} rows, created {created} rows")
    print(f"sat75_combined values that differ from the earlier SAT merge: {sat_changed}")
    print(f"master cols: {len(cols)} -> {len(outcols)}")


if __name__ == "__main__":
    main()
