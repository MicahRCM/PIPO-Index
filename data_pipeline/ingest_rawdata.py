#!/usr/bin/env python3
"""Ingest the enterprise historic Common Data Set spreadsheet (RawData.csv, 1988-2020)
into our institutions_master panel as CDS-unique historic variables.

Pure-python (no pandas). Produces PREVIEW/review artifacts only; NEVER overwrites
institutions_master.csv or RawData.csv.

Outputs:
  data/rawdata_unitid_crosswalk.csv    name -> unitid crosswalk
  data/rawdata_match_review.csv        ambiguous/low-confidence/unmatched for humans
  data/rawdata_column_map.md           column mapping documentation
  data/institutions_master_with_cds.csv  master COPY + mapped CDS columns
  data/rawdata_ingest_report.md        coverage / data-quality report

Run from repo root:  python3 data_pipeline/ingest_rawdata.py
"""
import csv, os, re, sys
from collections import defaultdict
from difflib import SequenceMatcher

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = '/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv'
MASTER = os.path.join(REPO, 'data', 'institutions_master.csv')
IPEDS_DIR = os.path.join(REPO, 'data', 'ipeds_directory.csv')
USN = os.path.join(REPO, 'data', 'usn_categories.csv')

OUT_XWALK = os.path.join(REPO, 'data', 'rawdata_unitid_crosswalk.csv')
OUT_REVIEW = os.path.join(REPO, 'data', 'rawdata_match_review.csv')
OUT_COLMAP = os.path.join(REPO, 'data', 'rawdata_column_map.md')
OUT_PREVIEW = os.path.join(REPO, 'data', 'institutions_master_with_cds.csv')
OUT_REPORT = os.path.join(REPO, 'data', 'rawdata_ingest_report.md')

# ---------------------------------------------------------------- name matching
STOP = {'university', 'college', 'the', 'of', 'at', 'and', '&', 'for',
        'school', 'institute', 'main', 'campus'}


def norm(s):
    """Normalized name key (matches substitute_analysis.py conventions)."""
    s = (s or '').lower()
    s = s.replace('&', ' and ')
    s = re.sub(r'\bst\.?\b', 'saint', s)
    s = s.replace('--', ' ').replace('-', ' ')
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    toks = [t for t in s.split() if t not in STOP]
    return ' '.join(toks)


def tokens(k):
    return set(k.split())


def build_reference():
    """Return exact-key map {norm_name: unitid}, and candidate list of
    (norm_name, unitid, display_name, city, state) for fuzzy fallback."""
    exact = {}
    cands = []           # (norm, unitid, dispname, city, state)
    uid_info = {}        # unitid -> (name, city, state)
    with open(IPEDS_DIR, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            uid = row['unitid'].strip()
            name = row['name'].strip()
            city = row.get('city', '').strip()
            st = row.get('state', '').strip()
            if uid not in uid_info:
                uid_info[uid] = (name, city, st)
            names = [name] + [a for a in row.get('alias', '').split('|') if a.strip()]
            for nm in names:
                k = norm(nm)
                if not k:
                    continue
                if k not in exact:
                    exact[k] = uid
                cands.append((k, uid, name, city, st))
    # USN categories augment (name->unitid); lower priority than IPEDS
    with open(USN, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            uid = row.get('unitid', '').strip()
            nm = row.get('name', '').strip()
            if not (uid and nm):
                continue
            k = norm(nm)
            if not k:
                continue
            if k not in exact:
                exact[k] = uid
            if uid not in uid_info:
                uid_info[uid] = (nm, row.get('city', '').strip(), row.get('state', '').strip())
            cands.append((k, uid, nm, row.get('city', '').strip(), row.get('state', '').strip()))
    # index candidates by token for fast fuzzy prefiltering
    tok_index = defaultdict(list)
    seen = set()
    dedup = []
    for c in cands:
        key = (c[0], c[1])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(c)
    for i, c in enumerate(dedup):
        for t in tokens(c[0]):
            tok_index[t].append(i)
    return exact, dedup, tok_index, uid_info


def fuzzy_candidates(nkey, cands, tok_index, topn=3):
    """Return top-N (score, unitid, dispname, city, state) for a normalized name."""
    if not nkey:
        return []
    cand_idx = set()
    for t in tokens(nkey):
        cand_idx.update(tok_index.get(t, ()))
    scored = []
    best_per_uid = {}
    for i in cand_idx:
        k, uid, name, city, st = cands[i]
        r = SequenceMatcher(None, nkey, k).ratio()
        if uid not in best_per_uid or r > best_per_uid[uid][0]:
            best_per_uid[uid] = (r, uid, name, city, st)
    scored = sorted(best_per_uid.values(), key=lambda x: -x[0])
    return scored[:topn]


HIGH = 0.92
MED = 0.86
AMBIG_GAP = 0.03


def build_crosswalk(raw_names):
    exact, cands, tok_index, uid_info = build_reference()
    xwalk = {}        # rawname -> (unitid, matched_name, confidence, method)
    review = []       # rows for review file
    for rawname in sorted(raw_names):
        nkey = norm(rawname)
        uid = exact.get(nkey)
        if uid:
            mn = uid_info.get(uid, (rawname, '', ''))[0]
            xwalk[rawname] = (uid, mn, 'high', 'exact_norm')
            continue
        # fuzzy fallback
        tops = fuzzy_candidates(nkey, cands, tok_index, topn=3)
        if not tops:
            xwalk[rawname] = ('', '', 'none', 'unmatched')
            review.append((rawname, 'unmatched', tops))
            continue
        best = tops[0]
        second = tops[1][0] if len(tops) > 1 else 0.0
        gap = best[0] - second
        if best[0] >= HIGH and gap >= AMBIG_GAP:
            xwalk[rawname] = (best[1], best[2], 'high', 'fuzzy')
        elif best[0] >= MED and gap >= AMBIG_GAP:
            xwalk[rawname] = (best[1], best[2], 'medium', 'fuzzy')
            review.append((rawname, 'medium_confidence', tops))
        else:
            xwalk[rawname] = ('', '', 'low', 'ambiguous' if gap < AMBIG_GAP else 'low')
            review.append((rawname, 'ambiguous_or_low', tops))
    return xwalk, review, uid_info


# ---------------------------------------------------------------- column mapping
# our_field -> exact source header (verified against printed headers)
COLMAP = {
    'commuter_pct': ('% Undergraduates who live in college-owned, operated or affiliated housing', 'inv_pct'),
    'pct_demonstrated_need': ('% Undergraduates determined to have financial need', 'pct'),
    'pct_need_met': ('% Undergraduates whose need was fully met', 'pct'),
    'pct_receiving_need_aid': ('% Undergraduates who received need-based scholarship or grant aid', 'pct'),
    'pct_top10_hs': ('% of first year student in top 10 percent of high school class', 'pct'),
    'gpa_25th': ('25th percentile GPA of all first-time, first-year (freshman) students', 'gpa'),
    'gpa_75th': ('75th percentile GPA of all first-time, first-year (freshman) students', 'gpa'),
    'gpa_band_below_100': ('% who had GPA below 1.00', 'pct'),
    'gpa_band_100_199': ('% who had GPA between 1.00 and 1.99', 'pct'),
    'gpa_band_200_249': ('% who had GPA between 2.00 and 2.49', 'pct'),
    'gpa_band_250_299': ('% who had GPA between 2.50 and 2.99', 'pct'),
    'gpa_band_300_324': ('% who had GPA between 3.00 and 3.24', 'pct'),
    'gpa_band_325_349': ('% who had GPA between 3.25 and 3.49', 'pct'),
    'gpa_band_350_374': ('% who had GPA between 3.50 and 3.74', 'pct'),
    'gpa_band_375_plus': ('% who had GPA higher than 3.75', 'pct'),
    'avg_aid_package_ug': ('Average financial aid package (undergraduates)', 'money'),
    'avg_need_grant_ug': ('Average need-based scholarship or grant award (undergraduates)', 'money'),
    'avg_merit_grant_fresh': ('Average non-need-based scholarship or grant award (freshmen) ', 'money'),
    'avg_pct_need_met_ug': ('Average percent of need met (undergraduates)', 'pct'),
}
CDS_FIELDS = list(COLMAP.keys())


def clean(val, kind):
    """Clean a raw value. Returns (numeric_str_or_empty, flag_or_None)."""
    if val is None:
        return '', None
    v = str(val).strip().replace(',', '').replace('%', '').replace('$', '')
    if v == '' or v.lower() in ('na', 'n/a', 'nan', 'null', '-'):
        return '', None
    try:
        f = float(v)
    except ValueError:
        return '', 'nonnumeric'
    if kind == 'inv_pct':
        if f < 0 or f > 100:
            return '', 'housing_pct_oor'
        f = 100.0 - f
        val_out = f
        return _fmt(val_out), None
    if kind == 'pct':
        if f < 0 or f > 100:
            return '', 'pct_oor'
        return _fmt(f), None
    if kind == 'gpa':
        if f < 0 or f > 5:
            return '', 'gpa_oor'
        return _fmt(f), None
    if kind == 'money':
        if f < 0:
            return '', 'money_neg'
        return _fmt(f), None
    return _fmt(f), None


def _fmt(f):
    if f == int(f):
        return str(int(f))
    return f'{f:.4f}'.rstrip('0').rstrip('.')


# ---------------------------------------------------------------- main
def main():
    # 1. distinct raw school names + full raw rows
    raw_names = set()
    with open(RAW, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            raw_names.add(row['School'].strip())

    xwalk, review, uid_info = build_crosswalk(raw_names)

    # write crosswalk
    with open(OUT_XWALK, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rawdata_school_name', 'unitid', 'matched_name', 'confidence', 'method'])
        for nm in sorted(xwalk):
            uid, mn, conf, meth = xwalk[nm]
            w.writerow([nm, uid, mn, conf, meth])

    # write review
    with open(OUT_REVIEW, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rawdata_school_name', 'reason',
                    'cand1_unitid', 'cand1_name', 'cand1_city', 'cand1_state', 'cand1_score',
                    'cand2_unitid', 'cand2_name', 'cand2_city', 'cand2_state', 'cand2_score',
                    'cand3_unitid', 'cand3_name', 'cand3_city', 'cand3_state', 'cand3_score'])
        for rawname, reason, tops in review:
            cells = [rawname, reason]
            for i in range(3):
                if i < len(tops):
                    sc, uid, name, city, st = tops[i]
                    cells += [uid, name, city, st, f'{sc:.3f}']
                else:
                    cells += ['', '', '', '', '']
            w.writerow(cells)

    matched = sum(1 for v in xwalk.values() if v[0])
    match_rate = matched / len(raw_names) * 100

    # 2. build (unitid,year)->cds values from RawData, with cleaning + flags
    #    name->unitid via xwalk
    cds = {}   # (unitid, year) -> {field: value}
    flags = defaultdict(int)
    field_school_years = defaultdict(int)      # field -> count of school-years filled
    field_schools = defaultdict(set)           # field -> distinct unitids
    n_raw_rows = 0
    n_rows_matched = 0
    with open(RAW, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            n_raw_rows += 1
            nm = row['School'].strip()
            uid = xwalk.get(nm, ('',))[0]
            if not uid:
                continue
            n_rows_matched += 1
            year = row['Year'].strip()
            key = (uid, year)
            rec = cds.setdefault(key, {})
            for field, (src, kind) in COLMAP.items():
                out, flag = clean(row.get(src), kind)
                if flag:
                    flags[flag] += 1
                if out != '':
                    # if duplicate (uid,year) collision, keep first non-empty
                    if rec.get(field, '') == '':
                        rec[field] = out
                        field_school_years[field] += 1
                        field_schools[field].add(uid)

    # 3. build preview = master copy + cds columns (overlap years only)
    with open(MASTER, encoding='utf-8-sig', newline='') as f:
        r = csv.reader(f)
        master_header = next(r)
        master_rows = list(r)
    idx_uid = master_header.index('unitid')
    idx_year = master_header.index('year')

    out_header = master_header + CDS_FIELDS
    n_master = 0
    n_filled_rows = 0
    with open(OUT_PREVIEW, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(out_header)
        for mr in master_rows:
            n_master += 1
            uid = mr[idx_uid].strip()
            year = mr[idx_year].strip()
            rec = cds.get((uid, year), {})
            extra = [rec.get(fld, '') for fld in CDS_FIELDS]
            if any(e != '' for e in extra):
                n_filled_rows += 1
            w.writerow(mr + extra)

    # 4. column map doc
    write_colmap()

    # 5. report
    write_report(raw_names, xwalk, matched, match_rate, cds, field_school_years,
                 field_schools, flags, n_raw_rows, n_rows_matched, n_master,
                 n_filled_rows, review)

    # stdout machine summary
    print(f"MATCH_RATE {match_rate:.1f}%  matched={matched}/{len(raw_names)}")
    print(f"raw_rows={n_raw_rows} rows_matched={n_rows_matched} "
          f"master_rows={n_master} preview_rows_filled={n_filled_rows}")
    print("FLAGS", dict(flags))
    return xwalk, cds


def write_colmap():
    lines = ['# RawData (CDS) -> institutions_master column mapping\n',
             '_Generated by `data_pipeline/ingest_rawdata.py`. Source: '
             '`/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv` (1988-2020)._\n',
             'Join key: RawData `School` (name) -> `unitid` via '
             '`data/rawdata_unitid_crosswalk.csv`, then joined to master on '
             '(unitid, year), overlap years only. Master\'s own columns are untouched.\n',
             'Cleaning: strip `%`, `,`, `$`; coerce numeric; blank/NA -> empty. '
             'Sanity ranges enforced (percentages 0-100 else dropped+flagged; GPA 0-5; '
             'money >= 0). `commuter_pct` is derived as `100 - housing%`.\n',
             '| our_field | source header (exact) | transform |',
             '|---|---|---|']
    for field, (src, kind) in COLMAP.items():
        t = {'inv_pct': '100 - value (percent)', 'pct': 'numeric, 0-100',
             'gpa': 'numeric, 0-5', 'money': 'numeric, >=0'}[kind]
        lines.append(f'| `{field}` | {src.strip()} | {t} |')
    with open(OUT_COLMAP, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def write_report(raw_names, xwalk, matched, match_rate, cds, field_school_years,
                 field_schools, flags, n_raw_rows, n_rows_matched, n_master,
                 n_filled_rows, review):
    # per-year fill for a headline CDS field to show historic depth
    year_fill = defaultdict(int)
    field_year = defaultdict(lambda: defaultdict(int))   # field -> year -> count
    for (uid, year), rec in cds.items():
        if any(v != '' for v in rec.values()):
            year_fill[year] += 1
        for fld, v in rec.items():
            if v != '':
                field_year[fld][year] += 1
    years = sorted(year_fill)
    # earliest year each field has data (temporal availability, honest depth)
    first_year = {}
    for fld in CDS_FIELDS:
        ys = [y for y in field_year[fld]]
        first_year[fld] = min(ys) if ys else '-'
    n_conf_high = sum(1 for v in xwalk.values() if v[2] == 'high')
    n_conf_med = sum(1 for v in xwalk.values() if v[2] == 'medium')
    n_unmatched = sum(1 for v in xwalk.values() if not v[0])
    matched_uids = {v[0] for v in xwalk.values() if v[0]}

    lines = []
    lines.append('# RawData (CDS) Ingest Report\n')
    lines.append('_Generated by `data_pipeline/ingest_rawdata.py`. PREVIEW only — '
                 '`institutions_master.csv` was NOT modified._\n')
    lines.append('## Source')
    lines.append('- File: `/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv`')
    lines.append(f'- Enterprise historic Common Data Set, years {years[0] if years else "?"}'
                 f'-{years[-1] if years else "?"} (source spans 1988-2020).')
    lines.append(f'- {n_raw_rows:,} rows, {len(raw_names):,} distinct school names.\n')
    lines.append('## Name -> UNITID match rate')
    lines.append(f'- **{match_rate:.1f}%** of distinct RawData schools matched to a unitid '
                 f'({matched:,}/{len(raw_names):,}).')
    lines.append(f'  - high confidence: {n_conf_high:,}; medium (needs review): {n_conf_med:,}; '
                 f'unmatched/low: {n_unmatched:,}.')
    lines.append(f'- {n_rows_matched:,}/{n_raw_rows:,} RawData school-year rows carry a unitid.')
    lines.append(f'- Distinct matched institutions: **{len(matched_uids):,}** '
                 f'(vs. prior CDS coverage of ~408 schools, one recent year).')
    lines.append(f'- {len(review):,} schools written to `data/rawdata_match_review.csv` '
                 f'for human validation.\n')
    lines.append('## Preview join')
    lines.append(f'- `data/institutions_master_with_cds.csv` = copy of master '
                 f'({n_master:,} rows) + {len(CDS_FIELDS)} CDS columns.')
    lines.append(f'- {n_filled_rows:,} master rows received at least one CDS value '
                 f'(join on unitid+year, overlap years only).\n')
    lines.append('## Per-variable coverage')
    lines.append('| CDS field | distinct schools | school-years filled | earliest year |')
    lines.append('|---|---:|---:|---:|')
    for fld in CDS_FIELDS:
        lines.append(f'| `{fld}` | {len(field_schools[fld]):,} | '
                     f'{field_school_years[fld]:,} | {first_year[fld]} |')
    lines.append('')
    lines.append('_Before this ingest, these CDS-unique variables existed for ~408 schools '
                 'and essentially one recent year. This adds a multi-decade panel._\n')
    lines.append('**Honest note on temporal depth:** the deep history back to 1988 is carried '
                 'almost entirely by two fields — `pct_receiving_need_aid` and `pct_top10_hs` '
                 '(both to 1988). The dollar/need fields (`pct_demonstrated_need`, '
                 '`pct_need_met`, `avg_aid_package_ug`, `avg_need_grant_ug`) begin ~2000; '
                 '`commuter_pct`, `avg_merit_grant_fresh`, `avg_pct_need_met_ug` begin ~2005; '
                 'and the GPA percentiles/bands begin ~2008. So the "schools filled by year" '
                 'table below overstates depth for pre-2005 years.\n')
    lines.append('## Coverage by year (rows with >=1 CDS value)')
    lines.append('| year | schools filled |')
    lines.append('|---|---:|')
    for y in years:
        lines.append(f'| {y} | {year_fill[y]:,} |')
    lines.append('')
    lines.append('## Data-quality flags')
    if flags:
        lines.append('| flag | count (values dropped) |')
        lines.append('|---|---:|')
        for k in sorted(flags):
            lines.append(f'| {k} | {flags[k]:,} |')
    else:
        lines.append('- None.')
    lines.append('')
    lines.append('Flag meanings: `housing_pct_oor` = housing% outside 0-100 (commuter not '
                 'derivable); `pct_oor` = percentage outside 0-100; `gpa_oor` = GPA outside '
                 '0-5; `money_neg` = negative dollar amount; `nonnumeric` = unparseable.\n')
    lines.append('## Caveats / honest gaps')
    lines.append('- RawData has **no city/state**, so name matching is name-only; '
                 'multi-campus systems (e.g. "X University--Montgomery") rely on the '
                 'normalized name alone. Verify medium/ambiguous rows in the review file.')
    lines.append('- Temporal depth is uneven per field (see per-variable table): only '
                 '`pct_receiving_need_aid` and `pct_top10_hs` reach back to 1988; commuter '
                 'and GPA fields effectively start ~2005-2008.')
    lines.append('- `gpa_25th`/`gpa_75th` have ~1,300 schools in 2008-2010 but drop to ~825 '
                 'from 2015 on (a source reporting change), while the low-GPA bands '
                 '(`gpa_band_below_100`, `gpa_band_100_199`) are near-empty every year '
                 'EXCEPT 2020 (~1,067) — treat these bands as effectively a 2020 snapshot.')
    lines.append('- Only the undergraduate-level aid/GPA-percentile columns are mapped; '
                 'merit aid is only available at the freshman level (`avg_merit_grant_fresh`).')
    lines.append('- GPA percentile columns (`gpa_25th`/`gpa_75th`) are blank for many '
                 'selective schools (e.g. Princeton pre-2020) that report distributions '
                 'instead of percentiles.')
    with open(OUT_REPORT, 'w') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
