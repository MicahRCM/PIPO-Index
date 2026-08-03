"""Match Combined2024SAT75.csv (School, State, SAT75) to IPEDS unitid and merge
the SAT-75th value into institutions_master.csv at year 2024.

Matching is keyed on (name, state) — state uniquely disambiguates, so all fuzzy
matching is constrained to WITHIN the same state (kills look-alike cross-state
false matches like Becker/Eckerd, Mills/Miles). Reference universes:
  - data/ipeds_directory.csv  (names + aliases, the unitid authority)
  - data/usn_categories.csv   (same US-News universe, already unitid-keyed)

Tiers: exact-normalized (incl. campus-stripped) -> unambiguous within-state fuzzy.
Anything else is reported for review, never guessed.

Usage:
  python3 data_pipeline/match_sat75.py            # match + report, write crosswalk
  python3 data_pipeline/match_sat75.py --apply     # + merge into master (year 2024)
"""
import argparse, csv, re, difflib, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = Path("/Users/peacespherical/Documents/Higher Ed Labs/Combined2024SAT75.csv")
DIRECTORY = REPO / "data" / "ipeds_directory.csv"
CATS = REPO / "data" / "usn_categories.csv"
MASTER = REPO / "data" / "institutions_master.csv"
OUT_XW = REPO / "data" / "sat75_crosswalk.csv"
OUT_REVIEW = REPO / "data" / "sat75_unmatched.csv"
BACKUP = REPO / "data" / "institutions_master.pre_sat75.csv"
COL = "sat75_combined"
YEAR = "2024"
FUZZY_CUTOFF = 0.87


# source uses period-abbreviations that don't match IPEDS full names
ABBR = {
    "u": "university", "univ": "university", "col": "college", "sci": "science",
    "tech": "technology", "technol": "technology", "aero": "aeronautical",
    "aeron": "aeronautics", "envir": "environmental", "acad": "academy",
    "adv": "advancement", "metropo": "metropolitan", "inst": "institute",
    "intl": "international", "poly": "polytechnic",
}


# hand-verified unitids for source names too abbreviated for auto-matching.
# keyed on (School, State) exactly as they appear in the source file.
MANUAL_OVERRIDES = {
    ("Louisiana State University–Baton Rouge", "LA"): "159391",
    ("Central Methodist University", "MO"): "176947",  # CLAS (undergrad) campus
    ("The Citadel, Military College of SC", "SC"): "217864",
    ("Cal. Polytech. State U.–San Luis Obispo", "CA"): "110422",
    ("Edgewood University", "WI"): "238661",            # IPEDS "Edgewood College"
    ("William Paterson University of N.J.", "NJ"): "187444",
    # "Texas A&M University–Victoria" — no such IPEDS campus; left unmatched.
    # "National University College" (PR) — for-profit, blank SAT; left unmatched.
}


def norm(s):
    s = (s or "").lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"[‐-―\-/]+", " ", s)          # all dashes -> space
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    # multi-word abbreviations first
    s = s.replace("s d ", "south dakota ").replace("u s ", "united states ")
    s = re.sub(r"\bpenn state\b", "pennsylvania state", s)
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bthe\b", " ", s)
    # expand single-token abbreviations
    s = " ".join(ABBR.get(tok, tok) for tok in s.split())
    s = re.sub(r"\b\d+\b$", "", s).strip()    # trailing footnote digit
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_campus(s):
    """looser key: drop trailing campus qualifiers."""
    n = norm(s)
    n = re.sub(r"\b(main campus|campus|main)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def build_refs():
    """(state, norm_name) -> set(unitid), plus loose variant, plus unitid->name."""
    exact, loose, name_of = {}, {}, {}
    def add(d, st, key, uid):
        if key:
            d.setdefault((st, key), set()).add(uid)
    for r in csv.DictReader(DIRECTORY.open()):
        uid, st = r["unitid"], r["state"].strip()
        name_of[uid] = r["name"]
        keys = {r["name"]}
        for a in (r.get("alias") or "").split("|"):
            if a.strip():
                keys.add(a)
        for k in keys:
            add(exact, st, norm(k), uid)
            add(loose, st, norm_campus(k), uid)
    for r in csv.DictReader(CATS.open()):
        uid, st = r["unitid"].strip(), r["state"].strip()
        if uid:
            name_of.setdefault(uid, r["name"])
            add(exact, st, norm(r["name"]), uid)
            add(loose, st, norm_campus(r["name"]), uid)
    return exact, loose, name_of


def keys_by_state_index(exact):
    kbs = {}
    for (st, k) in exact:
        kbs.setdefault(st, []).append(k)
    return kbs


def match_one(school, st, exact, loose, keys_by_state):
    """Resolve one (school, state) to (unitid, method) or (None, None).

    All fuzzy matching is constrained to `st`; caller supplies a state key.
    """
    nk, lk = norm(school), norm_campus(school)
    if (school, st) in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[(school, st)], "manual"
    if (st, nk) in exact and len(exact[(st, nk)]) == 1:
        return next(iter(exact[(st, nk)])), "exact"
    if (st, lk) in loose and len(loose[(st, lk)]) == 1:
        return next(iter(loose[(st, lk)])), "loose_campus"
    # token-set (Jaccard) similarity — weights the DISTINCTIVE token (e.g. the
    # Penn State campus name), which difflib's ratio drowns out under the long
    # shared prefix. Require a clear margin over the 2nd-best candidate.
    src = set(nk.split())
    scored = []
    for k in keys_by_state.get(st, []):
        t = set(k.split())
        if t:
            scored.append((len(src & t) / len(src | t), k))
    scored.sort(reverse=True)
    if scored and scored[0][0] >= 0.6:
        best_j, best_k = scored[0]
        margin = best_j - (scored[1][0] if len(scored) > 1 else 0)
        if len(exact[(st, best_k)]) == 1 and (len(scored) == 1 or margin >= 0.12):
            return next(iter(exact[(st, best_k)])), f"fuzzy:{best_k}"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    exact, loose, name_of = build_refs()
    keys_by_state = keys_by_state_index(exact)

    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    satcol = [c for c in rows[0] if "SAT" in c.upper()][0]

    matched, review = [], []
    for r in rows:
        school = (r.get("School") or "").strip()
        st = (r.get("State") or "").strip()
        sat = (r.get(satcol) or "").strip()
        uid, method = match_one(school, st, exact, loose, keys_by_state)
        if uid:
            matched.append((school, st, sat, uid, name_of.get(uid, ""), method))
        else:
            review.append((school, st, sat))

    n_sat = sum(1 for m in matched if m[2])
    print(f"SAT75 source rows: {len(rows)}")
    print(f"  matched to unitid: {len(matched)}  (with a SAT value: {n_sat})")
    print(f"  unmatched (review): {len(review)}")
    by_method = {}
    for m in matched:
        key = m[5].split(":")[0]
        by_method[key] = by_method.get(key, 0) + 1
    print(f"  by method: {by_method}")

    with OUT_XW.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["school", "state", "sat75", "unitid", "matched_name", "method"])
        w.writerows(matched)
    with OUT_REVIEW.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["school", "state", "sat75"])
        w.writerows(review)
    print(f"\nwrote {OUT_XW.name} ({len(matched)}) and {OUT_REVIEW.name} ({len(review)})")
    fuzzy = [m for m in matched if m[5].startswith("fuzzy")]
    if fuzzy:
        print(f"\nfuzzy matches to eyeball ({len(fuzzy)}) — source  ->  IPEDS:")
        for s, st, sat, uid, mn, meth in fuzzy:
            print(f"    {s[:34]:34} ({st}) -> {mn[:38]:38} [{uid}]")
    if review:
        print(f"\nunmatched ({len(review)}):")
        for s, st, sat in review:
            print(f"    {s}  ({st})  sat={sat or '-'}")

    if not args.apply:
        print("\n(no --apply: master not modified)")
        return

    # merge non-blank SAT into master at year 2024
    uid_sat = {m[3]: m[2] for m in matched if m[2]}
    # dup-unitid guard: if two source rows map to same unitid, warn
    seen = {}
    for m in matched:
        if m[2]:
            seen.setdefault(m[3], []).append(m[0])
    dups = {u: v for u, v in seen.items() if len(v) > 1}
    if dups:
        print(f"WARNING: {len(dups)} unitids matched by >1 source row: {list(dups.items())[:3]}")

    with MASTER.open() as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        mrows = list(rd)
    outcols = cols + ([COL] if COL not in cols else [])
    filled = created = 0
    seen24 = set()
    for r in mrows:
        r.setdefault(COL, "")
        if r["year"] == YEAR and r["unitid"] in uid_sat:
            r[COL] = uid_sat[r["unitid"]]
            filled += 1
            seen24.add(r["unitid"])
    for uid, sat in uid_sat.items():
        if uid not in seen24:
            nr = {c: "" for c in outcols}
            nr["unitid"] = uid; nr["year"] = YEAR; nr[COL] = sat
            nr["name"] = name_of.get(uid, "")
            mrows.append(nr); created += 1

    shutil.copy2(MASTER, BACKUP)
    with MASTER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=outcols)
        w.writeheader(); w.writerows(mrows)
    print(f"\nbacked up -> {BACKUP.name}")
    print(f"merged `{COL}` at {YEAR}: filled {filled} existing rows, created {created} rows")
    print(f"master cols: {len(cols)} -> {len(outcols)}")


if __name__ == "__main__":
    main()
