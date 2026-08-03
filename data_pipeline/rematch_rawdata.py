"""Second-pass name matching for the ~196 RawData schools that never got a unitid.

Conservative: matches only via (a) exact normalized name/alias against the IPEDS
directory, or (b) very-high fuzzy similarity with a SINGLE unambiguous candidate.
Every proposed match is then acceptance-rate validated against the master (using
the -2 edition->cohort alignment): a match is ACCEPTED only if the median
acceptance gap is small, or if there is no overlap to check (exact-normalized
matches are trusted without acceptance data).

Writes the accepted new matches to data/rawdata_crosswalk_additions.csv and, with
--apply, appends them to data/rawdata_unitid_crosswalk.csv.

Usage:
  python3 data_pipeline/rematch_rawdata.py            # report candidates
  python3 data_pipeline/rematch_rawdata.py --apply    # + append to crosswalk
"""
import argparse, csv, re, difflib, statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAWDATA = Path("/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv")
DIRECTORY = REPO / "data" / "ipeds_directory.csv"
XWALK = REPO / "data" / "rawdata_unitid_crosswalk.csv"
MASTER = REPO / "data" / "institutions_master.csv"
ADDITIONS = REPO / "data" / "rawdata_crosswalk_additions.csv"

ACC_GAP_MAX = 15.0   # pp; validation threshold when overlap exists


def norm(s):
    s = (s or "").lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"[-/]+", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    # standardize common tokens
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bagricultural and mechanical\b", "a and m", s)
    s = re.sub(r"\buniv\b", "university", s)
    s = re.sub(r"\s+", " ", s).strip()
    # drop a trailing campus qualifier only for a secondary key
    return s


def norm_nocampus(s):
    n = norm(s)
    # strip common campus/state qualifiers to a looser key
    n = re.sub(r"\b(tempe|provo|main campus)\b", "", n)
    n = re.sub(r"\bof pennsylvania\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def load_directory():
    by_name = {}
    by_loose = {}
    rows = []
    for r in csv.DictReader(DIRECTORY.open()):
        rows.append(r)
        keys = {norm(r["name"])}
        for a in (r.get("alias") or "").split("|"):
            if a.strip():
                keys.add(norm(a))
        for k in keys:
            if k:
                by_name.setdefault(k, set()).add(r["unitid"])
        lk = norm_nocampus(r["name"])
        if lk:
            by_loose.setdefault(lk, set()).add(r["unitid"])
    return rows, by_name, by_loose


def load_existing():
    matched = set()
    for r in csv.DictReader(XWALK.open()):
        if r.get("unitid", "").strip():
            matched.add(r["rawdata_school_name"])
    return matched


def raw_acc_by_year(name):
    """RawData acceptance% keyed by cohort year (edition-2) for one school."""
    out = {}
    r = csv.reader(RAWDATA.open(encoding="utf-8-sig", errors="replace"))
    h = next(r)
    si, yi, ai = h.index("School"), h.index("Year"), h.index("Acceptance rate")
    for row in r:
        if len(row) <= ai or row[si].strip() != name:
            continue
        y, a = row[yi].strip(), row[ai].strip().replace("%", "")
        if y.isdigit() and a:
            try:
                av = float(a)
                out[str(int(y) - 2)] = av * 100 if av <= 1 else av
            except ValueError:
                pass
    return out


def load_master_acc():
    macc = {}
    for r in csv.DictReader(MASTER.open()):
        v = r["acceptance_rate"].strip()
        if v:
            try:
                macc[(r["unitid"], r["year"])] = float(v) * 100
            except ValueError:
                pass
    return macc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    _, by_name, by_loose = load_directory()
    matched = load_existing()

    raw_schools = set()
    r = csv.reader(RAWDATA.open(encoding="utf-8-sig", errors="replace"))
    h = next(r); si = h.index("School")
    for row in r:
        if len(row) > si and row[si].strip():
            raw_schools.add(row[si].strip())
    unmatched = sorted(raw_schools - matched)
    all_dir_keys = list(by_name.keys())
    macc = load_master_acc()

    accepted, rejected, ambiguous, nomatch = [], [], [], []
    for name in unmatched:
        nk, lk = norm(name), norm_nocampus(name)
        cand, method = None, None
        if nk in by_name and len(by_name[nk]) == 1:
            cand, method = next(iter(by_name[nk])), "exact_name/alias"
        elif lk in by_loose and len(by_loose[lk]) == 1:
            cand, method = next(iter(by_loose[lk])), "loose_nocampus"
        else:
            # Fuzzy is UNSAFE for short college names (Becker/Eckerd, Mills/Miles,
            # MacMurray/McMurry are distinct schools that spell alike). Report
            # near-misses for manual review only — never auto-accept them.
            close = difflib.get_close_matches(nk, all_dir_keys, n=2, cutoff=0.92)
            if close:
                ambiguous.append((name, close))
            else:
                nomatch.append(name)
            continue

        # acceptance validation
        rawacc = raw_acc_by_year(name)
        gaps = [abs(rawacc[y] - macc[(cand, y)]) for y in rawacc if (cand, y) in macc]
        if gaps:
            med = st.median(gaps)
            if med <= ACC_GAP_MAX:
                accepted.append((name, cand, method, f"acc_gap={med:.1f}pp/n={len(gaps)}"))
            else:
                rejected.append((name, cand, method, f"acc_gap={med:.1f}pp/n={len(gaps)}"))
        else:
            accepted.append((name, cand, method, "no_overlap(trust exact/loose)"))

    print(f"unmatched: {len(unmatched)}")
    print(f"  ACCEPTED new matches: {len(accepted)}")
    print(f"  rejected (acc gap too big): {len(rejected)}")
    print(f"  ambiguous (multiple candidates): {len(ambiguous)}")
    print(f"  no match (likely closed/non-degree): {len(nomatch)}\n")
    print("=== ACCEPTED ===")
    for n, u, m, v in accepted:
        print(f"  {u}  {n[:45]:45} [{m}] {v}")
    if rejected:
        print("\n=== REJECTED (validation failed — left unmatched) ===")
        for n, u, m, v in rejected:
            print(f"  {u}  {n[:45]:45} [{m}] {v}")

    with ADDITIONS.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rawdata_school_name", "unitid", "matched_name", "confidence", "method"])
        for n, u, m, v in accepted:
            w.writerow([n, u, "", "second_pass", f"{m};{v}"])
    print(f"\nwrote {len(accepted)} -> {ADDITIONS}")

    if args.apply:
        existing = list(csv.DictReader(XWALK.open()))
        fld = existing[0].keys()
        with XWALK.open("a", newline="") as f:
            w = csv.writer(f)
            for n, u, m, v in accepted:
                w.writerow([n, u, "", "second_pass", f"{m};{v}"])
        print(f"appended {len(accepted)} rows -> {XWALK}")


if __name__ == "__main__":
    main()
