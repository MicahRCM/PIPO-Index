"""Drop the 19 stale (same-year-misaligned) RawData columns from the master.

These were promoted by `promote_rawdata.py` using a same-year join, so they sit
~2 years too recent. The `djm_*` columns from `merge_rawdata_full.py` are the
correctly-aligned replacements. Before dropping `commuter_pct` (which was a
DERIVED 100 - housing%), we recreate it correctly-aligned as `djm_commuter_pct`
from the aligned raw housing column so that convenience isn't lost.

Non-destructive: backs up to data/institutions_master.pre_drop.csv first.
"""
import csv, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MASTER = REPO / "data" / "institutions_master.csv"
BACKUP = REPO / "data" / "institutions_master.pre_drop.csv"
HOUSING = "djm_undergraduates_who_live_in_college_owned_operated_or_affiliated_housing"
DERIVED_COMMUTER = "djm_commuter_pct"

STALE = [
    "commuter_pct", "pct_demonstrated_need", "pct_need_met", "pct_receiving_need_aid",
    "pct_top10_hs", "gpa_25th", "gpa_75th",
    "gpa_band_below_100", "gpa_band_100_199", "gpa_band_200_249", "gpa_band_250_299",
    "gpa_band_300_324", "gpa_band_325_349", "gpa_band_350_374", "gpa_band_375_plus",
    "avg_aid_package_ug", "avg_need_grant_ug", "avg_merit_grant_fresh", "avg_pct_need_met_ug",
]


def main():
    with MASTER.open() as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)

    present = [c for c in STALE if c in cols]
    missing = [c for c in STALE if c not in cols]
    if missing:
        print("note: not present (already gone):", missing)

    # derive aligned commuter % from the aligned raw housing column
    derived = 0
    have_housing = HOUSING in cols
    for r in rows:
        r.setdefault(DERIVED_COMMUTER, "")
        if have_housing:
            v = r.get(HOUSING, "").strip()
            if v:
                try:
                    h = float(v)
                    if 0 <= h <= 100:
                        r[DERIVED_COMMUTER] = str(round(100 - h, 4))
                        derived += 1
                except ValueError:
                    pass

    outcols = [c for c in cols if c not in present]
    if DERIVED_COMMUTER not in outcols:
        # place it next to the other djm commuter/housing fields (append is fine)
        outcols = outcols + [DERIVED_COMMUTER]

    shutil.copy2(MASTER, BACKUP)
    with MASTER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=outcols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"backed up -> {BACKUP}")
    print(f"dropped {len(present)} stale columns: {present}")
    print(f"added {DERIVED_COMMUTER} (aligned, from raw housing): {derived} values")
    print(f"columns: {len(cols)} -> {len(outcols)}")


if __name__ == "__main__":
    main()
