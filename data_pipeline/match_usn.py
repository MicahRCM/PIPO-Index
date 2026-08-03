#!/usr/bin/env python3
"""
match_usn.py — Match scraped US News schools to IPEDS UNITIDs.

Inputs:
  data/usn_categories_raw.csv  (category, rank, usn_id, name, city, state)
  data/ipeds_directory.csv     (unitid, name, alias, city, state, zip, ...)
  data/usn_rank_history.csv    (unitid, name, year, rank, category)  [Reiter]

The US News `usn_id` column is US News's OWN internal id, NOT an IPEDS UNITID,
so we cannot join on it. We join on normalized name + state (+ city tiebreaker),
augmented by IPEDS alias strings.

Reiter's usn_rank_history carries IPEDS unitid for the two national categories
(national_universities + national_liberal_arts). For those USN rows we attach
the Reiter unitid as GROUND TRUTH (joined on normalized name, year 2026), and we
use it to validate the fuzzy matcher's accuracy on that overlap.

Outputs:
  data/usn_categories.csv     — every USN row + unitid, match_confidence, match_method
  data/usn_match_review.csv   — ambiguous / low-confidence / duplicate-name cases
                                with top candidate unitids for manual validation.
"""

import csv
import os
import re
import sys
from difflib import SequenceMatcher

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO, "data", "usn_categories_raw.csv")
IPEDS = os.path.join(REPO, "data", "ipeds_directory.csv")
REITER = os.path.join(REPO, "data", "usn_rank_history.csv")
OUT = os.path.join(REPO, "data", "usn_categories.csv")
REVIEW = os.path.join(REPO, "data", "usn_match_review.csv")

# Map US News scrape slug -> Reiter category label.
SLUG_TO_REITER = {
    "national-universities": "national_universities",
    "national-liberal-arts-colleges": "national_liberal_arts",
}

NOISE = {"university", "college", "the", "of", "and", "campus", "main"}

# Confidence thresholds.
HIGH = 0.93
MED = 0.84
AMBIG_GAP = 0.04  # top1 - top2 closer than this => ambiguous

ABBREV = {
    "suny": "state university of new york",
    "cuny": "city university of new york",
}


def normalize(name, expand=True):
    """Aggressive normalized form for keying/comparison.

    expand=True expands SUNY/CUNY to their long forms (matches IPEDS entries
    that spell them out, e.g. "State University of New York at New Paltz").
    expand=False keeps the acronym dropped entirely, which matches IPEDS
    entries that use the short campus brand (e.g. "Binghamton University").
    """
    s = (name or "").lower().strip()
    s = s.replace("&", " and ")
    s = s.replace("--", " ").replace("—", " ").replace("–", " ")
    s = re.sub(r"\bat\b", " ", s)
    # Saint / St. unification
    s = re.sub(r"\bst\.?\b", "saint", s)
    # drop punctuation
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    if expand:
        s = " ".join(ABBREV.get(t, t) for t in s.split())
    else:
        s = " ".join(t for t in s.split() if t not in ABBREV)
    # drop "main campus" noise that IPEDS appends to flagships
    s = re.sub(r"\bmain campus\b", " ", s)
    # strip a leading "the"
    s = re.sub(r"^the\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def core(name):
    """Normalized form with generic noise words removed (loose fallback key)."""
    toks = [t for t in normalize(name).split() if t not in NOISE]
    return " ".join(toks)


def core_tokens(name):
    return set(t for t in normalize(name).split() if t not in NOISE)


def token_set_noexpand(name):
    """Content tokens with SUNY/CUNY dropped entirely (not expanded)."""
    return set(t for t in normalize(name, expand=False).split() if t not in NOISE)


def significant(tokens):
    """Tokens long enough to be distinguishing (drops 'a','m','t','st' noise)."""
    return set(t for t in tokens if len(t) >= 3)


def min_missing(name, ipeds_tokens_all):
    """Smallest significant set of USN tokens absent from the IPEDS token union,
    taken over both normalization variants (so a SUNY/CUNY tag is not counted as
    'missing' against an IPEDS name that simply omits it)."""
    best = None
    for uv in (core_tokens(name), token_set_noexpand(name)):
        if not uv:
            continue
        miss = significant(uv) - ipeds_tokens_all
        if best is None or len(miss) < len(best):
            best = miss
    return best or set()


def ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


def overlap(a_toks, b_toks):
    """Token overlap relative to the smaller token set (0..1)."""
    if not a_toks or not b_toks:
        return 0.0
    return len(a_toks & b_toks) / min(len(a_toks), len(b_toks))


def load_ipeds():
    """Return rows and indexes: by (norm,state), by (core,state).

    Each IPEDS institution contributes its name plus every alias string as
    candidate normalized keys.
    """
    rows = []
    by_norm = {}        # (norm, state) -> list of row idx
    by_core = {}        # (core, state) -> list of row idx
    by_state = {}       # state -> list of row idx
    by_city_state = {}  # (city, state) -> list of row idx
    with open(IPEDS, newline="") as f:
        for r in csv.DictReader(f):
            idx = len(rows)
            state = (r["state"] or "").strip().upper()
            city = (r["city"] or "").strip().lower()
            names = [r["name"]]
            # alias column packs former/alt names separated by | or multiple spaces
            for piece in re.split(r"[|]|\s{2,}", r.get("alias") or ""):
                piece = piece.strip()
                if piece:
                    names.append(piece)
            # precompute normalized + token forms for fast scoring
            norms = []
            tokens = []
            for nm in names:
                nkey = normalize(nm)
                if nkey:
                    norms.append(nkey)
                    tokens.append(core_tokens(nm))
                    by_norm.setdefault((nkey, state), []).append(idx)
                ckey = core(nm)
                if ckey:
                    by_core.setdefault((ckey, state), []).append(idx)
            r["_norms"] = norms
            r["_tokens"] = tokens
            r["_tokens_all"] = set().union(*tokens) if tokens else set()
            r["_state"] = state
            rows.append(r)
            by_state.setdefault(state, []).append(idx)
            if city:
                by_city_state.setdefault((city, state), []).append(idx)
    return rows, by_norm, by_core, by_state, by_city_state


def load_reiter_groundtruth():
    """(reiter_category, normalized_name) -> list[(rank_int, unitid)], year 2026.

    Stored as a list because duplicate school names exist (e.g. two "Wheaton
    College" LACs, IL rank 50 and MA rank 76); the caller disambiguates by the
    closest US News rank.
    """
    gt = {}
    with open(REITER, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("year") != "2026":
                continue
            uid = (r.get("unitid") or "").strip()
            if not uid:
                continue
            try:
                rk = int(r.get("rank"))
            except (TypeError, ValueError):
                rk = None
            # Key under both normalization variants so a USN name carrying a
            # campus-system tag ("Binghamton University--SUNY") still resolves to
            # the Reiter row ("Binghamton University").
            for nkey in {normalize(r.get("name"), True), normalize(r.get("name"), False)}:
                gt.setdefault((r.get("category"), nkey), []).append((rk, uid))
    return gt


def gt_lookup(gt, reiter_cat, name, usn_rank):
    """Resolve a Reiter unitid for a USN row, disambiguating dup names by rank.

    Tries both normalization variants of the USN name so a campus-system tag
    ("--SUNY"/"--CUNY") does not block the join.
    """
    if not reiter_cat:
        return None
    entries = []
    seen = set()
    for nkey in {normalize(name, True), normalize(name, False)}:
        for e in gt.get((reiter_cat, nkey), []):
            if e[1] not in seen:
                seen.add(e[1])
                entries.append(e)
    if not entries:
        return None
    if len(entries) == 1:
        return entries[0][1]
    try:
        ur = int(usn_rank)
    except (TypeError, ValueError):
        return entries[0][1]
    return min(entries, key=lambda e: abs((e[0] if e[0] is not None else 10 ** 6) - ur))[1]


def uniq(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def best_fuzzy(name, city, state, ipeds_rows, by_state):
    """Rank IPEDS candidates within `state` (or all states if state is empty).

    Scoring is RECALL-oriented: how many of the USN name's content tokens does a
    candidate cover (|usn & cand| / |usn|), blended with the difflib ratio and a
    city-match boost. Crucially, candidates that are MISSING significant USN
    tokens are penalized -- this stops a short subset name ("University of
    Denver") from beating the institution that carries the full token set
    ("University of Colorado Denver ...") just because it is a subset, and it
    keeps a branch campus from collapsing onto the main campus.

    The recall / missing set is computed against the single best-covering alias
    of each candidate (not the union of all aliases), so an unrelated alias
    (e.g. "Colorado Seminary" attached to University of Denver) cannot
    accidentally launder in a token the institution does not really carry.

    Returns list of (idx, score, ratio, recall, city_match, n_missing), best
    first.  n_missing counts significant USN tokens the chosen alias lacks.
    """
    nkeys = {normalize(name, expand=True), normalize(name, expand=False)}
    # Two token interpretations: with SUNY/CUNY expanded, and with the tag
    # dropped. Scoring takes the BEST of the two so a campus-system tag does not
    # inject phantom "state new york" tokens that wrongly penalize the real match.
    usn_variants = uniq([v for v in (core_tokens(name), token_set_noexpand(name)) if v])
    if not usn_variants:
        usn_variants = [set()]
    city = (city or "").strip().lower()
    pool = by_state.get(state, []) if state else range(len(ipeds_rows))
    scored = []
    for idx in pool:
        r = ipeds_rows[idx]
        rr = max((ratio(nk, c) for nk in nkeys for c in r["_norms"]), default=0.0)
        # Pick the (candidate alias, USN variant) pair that best covers the name.
        best_recall = 0.0
        best_missing = significant(usn_variants[0])
        for t in r["_tokens"]:
            for uv in usn_variants:
                if not uv:
                    continue
                rec = len(uv & t) / len(uv)
                miss = significant(uv) - t
                if rec > best_recall or (rec == best_recall and len(miss) < len(best_missing)):
                    best_recall = rec
                    best_missing = miss
        city_match = bool(city) and (r["city"] or "").strip().lower() == city
        base = max(rr, 0.45 * rr + 0.55 * best_recall)
        penalty = min(0.60, 0.22 * len(best_missing))
        score = min(1.0, max(0.0, base + (0.12 if city_match else 0.0) - penalty))
        scored.append((idx, score, rr, best_recall, city_match, len(best_missing)))
    # best score, then city match, then ratio, then fewest missing tokens
    scored.sort(key=lambda t: (-t[1], -t[4], -t[2], t[5]))
    return scored


def candidate_str(ipeds_rows, idx, score):
    r = ipeds_rows[idx]
    return f"{r['unitid']}|{r['name']}|{r['city']}, {r['state']}|{score:.3f}"


def main():
    ipeds_rows, by_norm, by_core, by_state, by_city_state = load_ipeds()
    gt = load_reiter_groundtruth()
    unitid_to_idx = {r["unitid"]: i for i, r in enumerate(ipeds_rows)}

    out_rows = []
    review_rows = []
    # accuracy tracking on Reiter overlap
    val_total = val_agree = val_override = 0
    val_disagree = []  # (name, assigned_unitid, reiter_unitid)

    with open(RAW, newline="") as f:
        usn = list(csv.DictReader(f))

    for u in usn:
        slug = u["category"]
        name = u["name"]
        state = (u["state"] or "").strip().upper()
        city = (u["city"] or "").strip().lower()
        reiter_cat = SLUG_TO_REITER.get(slug)
        # Reiter ground truth, disambiguating duplicate names by closest rank.
        gt_uid = gt_lookup(gt, reiter_cat, name, u["rank"]) if reiter_cat else None

        unitid = ""
        conf = ""
        method = ""
        candidates = best_fuzzy(name, city, state, ipeds_rows, by_state)
        top = candidates[0] if candidates else None
        second = candidates[1] if len(candidates) > 1 else None

        # 1) exact normalized name + state (unique)
        exact = uniq(by_norm.get((normalize(name), state), [])) if state else []
        core_hits = uniq(by_core.get((core(name), state), [])) if state else []

        if len(exact) == 1:
            unitid, conf, method = ipeds_rows[exact[0]]["unitid"], "high", "exact_name_state"
        elif len(exact) > 1:
            # disambiguate by city
            cm = [i for i in exact if (ipeds_rows[i]["city"] or "").strip().lower() == city]
            if len(cm) == 1:
                unitid, conf, method = ipeds_rows[cm[0]]["unitid"], "high", "exact_name_state_city"
            else:
                method = "ambiguous_exact"
        elif len(core_hits) == 1:
            unitid, conf, method = ipeds_rows[core_hits[0]]["unitid"], "high", "core_name_state"
        elif len(core_hits) > 1:
            cm = [i for i in core_hits if (ipeds_rows[i]["city"] or "").strip().lower() == city]
            if len(cm) == 1:
                unitid, conf, method = ipeds_rows[cm[0]]["unitid"], "high", "core_name_state_city"
            else:
                method = "ambiguous_core"

        # 2) fuzzy / token fallback when not yet resolved
        if not unitid and top:
            ti, s1, r1, rec1, cm1, miss1 = top
            s2 = second[1] if second else 0.0
            gap = s1 - s2
            method_tag = "fuzzy_nostate" if not state else "fuzzy_state"
            if s1 >= HIGH and gap >= AMBIG_GAP:
                unitid, conf, method = ipeds_rows[ti]["unitid"], "high", method_tag
            elif s1 >= HIGH and cm1 and r1 >= MED:
                # tied scores but this candidate's city matches and name is close
                unitid, conf, method = ipeds_rows[ti]["unitid"], "high", method_tag + "_city"
            elif s1 >= MED and (gap >= AMBIG_GAP or cm1):
                unitid, conf, method = ipeds_rows[ti]["unitid"], "medium", method_tag
            elif s1 >= 0.55 and miss1 == 0:
                # weak but the candidate covers EVERY significant USN token, so it
                # is not a branch/extra-token mismatch -- accept at low confidence.
                unitid, conf, method = ipeds_rows[ti]["unitid"], "low", method_tag + "_weak"
            elif cm1 and rec1 >= 0.5 and r1 >= 0.55:
                # Missing some USN tokens, BUT the candidate sits in the same city
                # and the raw name similarity is strong -- this is an abbreviation
                # / rename, not a different campus (e.g. "North Carolina
                # Agricultural and Technical State University" -> IPEDS "North
                # Carolina A & T State University", both Greensboro). The
                # missing-token penalty deflates the blended score here, so we
                # gate on the raw ratio r1 instead. Low confidence + flag.
                unitid, conf, method = ipeds_rows[ti]["unitid"], "low", method_tag + "_weak"
            else:
                # Leaving unitid empty here is deliberate: the top candidate is
                # missing distinguishing USN tokens (a branch name, a "Colorado",
                # an "Assemblies of God") AND its city does not match, so we must
                # NOT collapse onto it (e.g. main campus). Flag for review instead.
                method = method or "low_fuzzy"

        # 3) token-containment recovery (handles branch campuses whose state was
        #    lost in scraping, e.g. "Pennsylvania State University -- Scranton").
        if not unitid:
            usn_tok = core_tokens(name)
            pool = by_state.get(state, []) if state else range(len(ipeds_rows))
            if len(usn_tok) >= 2:
                # forward: all USN tokens present in the IPEDS name (high precision)
                fwd = uniq([i for i in pool if usn_tok <= ipeds_rows[i]["_tokens_all"]])
                if len(fwd) == 1:
                    unitid, conf, method = ipeds_rows[fwd[0]]["unitid"], "medium", "containment_subset"
                elif state:
                    # reverse within state: a (>=2 token) IPEDS name fully inside USN,
                    # pick best by ratio if unambiguous.
                    rev = [i for i in pool
                           if len(ipeds_rows[i]["_tokens_all"]) >= 2
                           and ipeds_rows[i]["_tokens_all"] <= usn_tok]
                    if rev:
                        nk = normalize(name)
                        rev.sort(key=lambda i: -max(ratio(nk, c) for c in ipeds_rows[i]["_norms"]))
                        best = rev[0]
                        bs = max(ratio(nk, c) for c in ipeds_rows[best]["_norms"])
                        s2 = (max(ratio(nk, c) for c in ipeds_rows[rev[1]]["_norms"])
                              if len(rev) > 1 else 0.0)
                        if bs - s2 >= AMBIG_GAP:
                            unitid, conf, method = ipeds_rows[best]["unitid"], "medium", "containment_super"

        # 4) city-unique last resort: a name we couldn't confidently match whose
        #    (city, state) maps to exactly ONE IPEDS institution is almost
        #    certainly that institution -- recovers renamed schools whose tokens
        #    no longer overlap (e.g. "Southwestern Assemblies of God University",
        #    now IPEDS "Nelson University", the only school in Waxahachie TX).
        if (not unitid or conf == "low") and city and state:
            cs = uniq(by_city_state.get((city, state), []))
            if len(cs) == 1 and cs[0] != (unitid_to_idx.get(unitid) if unitid else None):
                unitid, conf, method = ipeds_rows[cs[0]]["unitid"], "low", "city_unique"

        # Did the pipeline land on an EXACT location match (same normalized name
        # AND same city AND same state, score ~1.0)? Such a match is authoritative
        # and trumps a disagreeing Reiter row (Reiter has the CSU Long Beach /
        # Fullerton unitids swapped relative to the IPEDS authority).
        loc_exact = method in ("exact_name_state", "exact_name_state_city",
                               "core_name_state_city")
        if not loc_exact and unitid and top and abs(top[2] - 1.0) < 1e-9 \
                and top[4] and ipeds_rows[top[0]]["unitid"] == unitid:
            loc_exact = True

        # ground-truth override for the two national categories
        if gt_uid:
            if unitid and unitid == gt_uid:
                conf, method = "high", "reiter_confirmed"
            elif loc_exact and unitid and unitid != gt_uid:
                # Exact name+city+state match contradicts Reiter -> trust the
                # IPEDS authority (Reiter join key is wrong/swapped). Flag it.
                conf, method = "high", "exact_loc_over_reiter"
            else:
                # trust Reiter; flag if fuzzy disagreed
                if unitid and unitid != gt_uid:
                    method = "reiter_override_fuzzy_disagree"
                else:
                    method = "reiter_groundtruth"
                unitid, conf = gt_uid, "high"

        # validation stats: does the FINAL assigned unitid agree with Reiter?
        # exact_loc_over_reiter rows are deliberate, authoritative disagreements.
        if gt_uid:
            val_total += 1
            if unitid == gt_uid:
                val_agree += 1
            elif method == "exact_loc_over_reiter":
                val_override += 1
                val_disagree.append((name, unitid, gt_uid))
            else:
                val_disagree.append((name, unitid, gt_uid))

        out_rows.append({
            "category": slug, "rank": u["rank"], "usn_id": u["usn_id"],
            "name": name, "city": u["city"], "state": u["state"],
            "unitid": unitid, "match_confidence": conf, "match_method": method,
        })

        # Review aggressively. A row is flagged when ANY of:
        #  - it is not high confidence (or unmatched / ambiguous), OR
        #  - the assigned unitid is not the top CITY-CONSISTENT candidate, OR
        #  - the chosen IPEDS name lacks a significant token of the USN name.
        # Cleanly auto-matched rows (exact / core / reiter_confirmed) are exempt
        # from the latter two checks -- by construction they carry no leftover
        # tokens and need no human attention.
        clean = {"exact_name_state", "exact_name_state_city", "core_name_state",
                 "core_name_state_city", "reiter_confirmed"}
        needs_review = (
            not unitid
            or conf in ("", "low", "medium")
            or method.startswith("ambiguous")
            or method in ("low_fuzzy", "reiter_override_fuzzy_disagree",
                          "exact_loc_over_reiter")
        )
        if not needs_review and method not in clean and unitid:
            chosen_idx = unitid_to_idx.get(unitid)
            # (a) top city-consistent candidate disagrees with our pick
            top_city = next((c for c in candidates if c[4]), None)
            if top_city and ipeds_rows[top_city[0]]["unitid"] != unitid:
                needs_review = True
            # (b) USN name carries significant tokens the chosen IPEDS name lacks
            if chosen_idx is not None and min_missing(name, ipeds_rows[chosen_idx]["_tokens_all"]):
                needs_review = True
        if needs_review:
            cands = [candidate_str(ipeds_rows, c[0], c[1]) for c in candidates[:3]]
            review_rows.append({
                "category": slug, "rank": u["rank"], "usn_id": u["usn_id"],
                "usn_name": name, "usn_city": u["city"], "usn_state": u["state"],
                "assigned_unitid": unitid, "match_confidence": conf,
                "match_method": method,
                "candidate_1": cands[0] if len(cands) > 0 else "",
                "candidate_2": cands[1] if len(cands) > 1 else "",
                "candidate_3": cands[2] if len(cands) > 2 else "",
            })

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "category", "rank", "usn_id", "name", "city", "state",
            "unitid", "match_confidence", "match_method"])
        w.writeheader()
        w.writerows(out_rows)

    with open(REVIEW, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "category", "rank", "usn_id", "usn_name", "usn_city", "usn_state",
            "assigned_unitid", "match_confidence", "match_method",
            "candidate_1", "candidate_2", "candidate_3"])
        w.writeheader()
        w.writerows(review_rows)

    matched = sum(1 for r in out_rows if r["unitid"])
    acc = (val_agree / val_total * 100) if val_total else float("nan")
    print(f"USN rows: {len(out_rows)}")
    print(f"matched to unitid: {matched} ({matched/len(out_rows)*100:.1f}%)")
    print(f"flagged for review: {len(review_rows)}")
    print(f"Reiter agreement (Nat'l+LAC): final unitid matched ground truth on "
          f"{val_agree}/{val_total} ({acc:.1f}%); "
          f"{val_override} deliberate exact-location overrides of bad Reiter rows")
    for nm, got, want in val_disagree:
        print(f"   Reiter disagree: {nm!r} assigned={got} reiter={want}")


if __name__ == "__main__":
    main()
