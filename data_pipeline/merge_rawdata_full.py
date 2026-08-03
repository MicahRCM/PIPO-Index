"""Merge ALL RawData.csv columns into institutions_master.csv as `djm_*` columns.

RawData.csv (the historic US-News/CDS export, editions 1988-2020) has 168 columns;
only 19 were ever promoted. This brings in the rest, non-destructively, under a
`djm_` prefix so provenance is unmistakable and there is zero collision risk with
existing master columns.

Two things this handles carefully:

1. YEAR ALIGNMENT. RawData `Year` is the US-News *edition* year, which runs ~2
   years ahead of the IPEDS *cohort* year the master is keyed on. Validated
   empirically: SAT-75th median gap is 0.0 and acceptance gap 0.1pp at offset -2
   (vs 20.0 / 4.5pp at same-year). So we key on (unitid, Year - 2). The original
   RawData edition year is retained in `djm_usn_edition_year`.

2. KEEP EVERYTHING. Per request, no RawData row is discarded:
     - matched (unitid, cohort) that exists in master -> fill djm_ cols in place
     - matched (unitid, cohort) with no master row     -> create a new row
     - unmatched school (no unitid) or SUSPECT match    -> create a row with a
       blank unitid (data preserved, just not join-able to the IPEDS backbone)

Usage:
  python3 data_pipeline/merge_rawdata_full.py --dry-run   # report deltas, write nothing
  python3 data_pipeline/merge_rawdata_full.py             # back up + write master
"""
import argparse, csv, re, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAWDATA = Path("/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv")
MASTER = REPO / "data" / "institutions_master.csv"
XWALK = REPO / "data" / "rawdata_unitid_crosswalk.csv"
VALID = REPO / "data" / "rawdata_join_validation.csv"
BACKUP = REPO / "data" / "institutions_master.pre_djm.csv"
COLMAP = REPO / "data" / "djm_column_map.md"
YEAR_OFFSET = -2  # RawData edition year -> IPEDS cohort year

KEY_COLS = {"School", "Year"}  # not data; keys


def sanitize(header, taken):
    """RawData header -> unique djm_ snake_case column name."""
    s = header.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    s = re.sub(r"_+", "_", s)
    name = "djm_" + s
    base, n = name, 2
    while name in taken:
        name = f"{base}_{n}"; n += 1
    taken.add(name)
    return name


def clean(v):
    v = (v or "").strip()
    if v == "" or v.upper() in ("N/A", "NA", "-", "--"):
        return ""
    # numeric-ish: strip formatting chars but leave true text alone
    stripped = v.replace(",", "").replace("$", "").replace("%", "").strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", stripped):
        return stripped
    return v


def load_crosswalk_and_suspects():
    xw = {}
    for r in csv.DictReader(XWALK.open()):
        uid = r.get("unitid", "").strip()
        if uid:
            xw[r["rawdata_school_name"]] = uid
    suspects = set()
    for r in csv.DictReader(VALID.open()):
        if r.get("verdict") == "SUSPECT":
            suspects.add(r["rawdata_name"])
    return xw, suspects


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    xw, suspects = load_crosswalk_and_suspects()
    print(f"crosswalk matches: {len(xw)}   suspect names excluded: {len(suspects)}",
          file=sys.stderr)

    # --- build djm_ column names from RawData header ---
    rdr = csv.reader(RAWDATA.open(encoding="utf-8-sig", errors="replace"))
    raw_header = next(rdr)
    taken = set()
    data_cols = [(i, h) for i, h in enumerate(raw_header) if h.strip() and h.strip() not in KEY_COLS]
    djm_of = {i: sanitize(h, taken) for i, h in data_cols}
    year_i = raw_header.index("Year")
    school_i = raw_header.index("School")
    djm_cols = [djm_of[i] for i, _ in data_cols] + ["djm_usn_edition_year"]

    # --- ingest RawData rows -> records keyed (unitid, cohort, name) ---
    records = []          # each: (uid, cohort_year, name, {djm_col: val})
    n_no_uid = n_suspect = 0
    for row in rdr:
        if len(row) <= year_i:
            continue
        yr = row[year_i].strip()
        if not yr.isdigit():
            continue
        cohort = str(int(yr) + YEAR_OFFSET)
        name = row[school_i].strip()
        uid = xw.get(name, "")
        if name in suspects:
            uid = ""; n_suspect += 1
        elif not uid:
            n_no_uid += 1
        vals = {djm_of[i]: clean(row[i]) for i, _ in data_cols if i < len(row)}
        vals["djm_usn_edition_year"] = yr
        records.append((uid, cohort, name, vals))

    # --- load master ---
    with MASTER.open() as f:
        rd = csv.DictReader(f)
        mcols = rd.fieldnames
        mrows = list(rd)
    new_cols = [c for c in djm_cols if c not in mcols]
    outcols = mcols + new_cols

    # index existing rows by (unitid, year); track dup keys
    index = {}
    dup_keys = 0
    for r in mrows:
        k = (r["unitid"], r["year"])
        if k in index:
            dup_keys += 1
        else:
            index[k] = r

    # --- apply ---
    for r in mrows:
        for c in new_cols:
            r.setdefault(c, "")
    filled_existing = created_matched = created_blank = 0
    for uid, cohort, name, vals in records:
        target = index.get((uid, cohort)) if uid else None
        if target is not None:
            for c, v in vals.items():
                if v != "":
                    target[c] = v
            filled_existing += 1
        else:
            newrow = {c: "" for c in outcols}
            newrow["unitid"] = uid
            newrow["year"] = cohort
            if not newrow.get("name"):
                newrow["name"] = name
            newrow["djm_rawdata_name"] = name  # always keep the raw name for trace
            for c, v in vals.items():
                newrow[c] = v
            mrows.append(newrow)
            if uid:
                created_matched += 1
            else:
                created_blank += 1

    # djm_rawdata_name may be a brand-new col
    if "djm_rawdata_name" not in outcols:
        outcols = outcols + ["djm_rawdata_name"]
        for r in mrows:
            r.setdefault("djm_rawdata_name", "")

    # --- report ---
    print(f"\n=== RawData -> djm_ merge ({'DRY RUN' if args.dry_run else 'WRITING'}) ===")
    print(f"RawData records ingested:            {len(records)}")
    print(f"  with a unitid (matched):           {len(records)-n_no_uid-n_suspect}")
    print(f"  no unitid (unmatched school):      {n_no_uid}")
    print(f"  suspect match -> blanked unitid:   {n_suspect}")
    print(f"new djm_ columns added:              {len(new_cols)} (+ djm_rawdata_name)")
    print(f"master columns: {len(mcols)} -> {len(outcols)}")
    print(f"rows filled into existing master:    {filled_existing}")
    print(f"rows created (matched, new cohort):  {created_matched}")
    print(f"rows created (blank unitid, kept):   {created_blank}")
    print(f"master rows: {len(mrows)-created_matched-created_blank} -> {len(mrows)}")
    if dup_keys:
        print(f"WARNING: {dup_keys} duplicate (unitid,year) keys in master; filled first only")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        print("sample new columns:", ", ".join(new_cols[:12]))
        return

    shutil.copy2(MASTER, BACKUP)
    print(f"\nbacked up -> {BACKUP}")
    with MASTER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=outcols)
        w.writeheader()
        w.writerows(mrows)
    print(f"wrote {MASTER}")

    # column map doc
    with COLMAP.open("w") as f:
        f.write("# RawData -> `djm_*` column map\n\n")
        f.write(f"_Generated by `data_pipeline/merge_rawdata_full.py`. Source: `{RAWDATA}` "
                f"(editions 1988-2020). Join key: (unitid, RawData_Year {YEAR_OFFSET}). "
                f"Original edition year retained in `djm_usn_edition_year`._\n\n")
        f.write("| djm_ column | source header (exact) |\n|---|---|\n")
        for i, h in data_cols:
            f.write(f"| `{djm_of[i]}` | {h.strip()} |\n")
        f.write("| `djm_usn_edition_year` | (RawData `Year`, unshifted) |\n")
        f.write("| `djm_rawdata_name` | (RawData `School`, for rows created with no/blank unitid) |\n")
    print(f"wrote {COLMAP}")


if __name__ == "__main__":
    main()
