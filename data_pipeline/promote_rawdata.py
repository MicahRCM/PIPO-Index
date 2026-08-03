#!/usr/bin/env python3
"""Cross-validate the name-based RawData->unitid joins, then promote the 19
validated CDS columns from the preview into institutions_master.csv.

Pure-python (no pandas).

Step 1 (validate): join RawData (name -> unitid via crosswalk) to master on
  (unitid, year) over overlapping years and compare RawData's own
  `Acceptance rate` / `SAT 75th percentile` / `ACT 75th percentile` against the
  trustworthy master columns. A large acceptance-rate gap indicates the RawData
  school was matched to the WRONG unitid. Writes data/rawdata_join_validation.csv.

Step 2 (promote): copy the preview into institutions_master.csv (which is byte-
  identical in its first 50 cols + 19 appended CDS cols), but BLANK the 19 CDS
  values for any unitid flagged SUSPECT. Backs up master first.

Run from repo root:  python3 data_pipeline/promote_rawdata.py [--dry-run]
"""
import csv, os, sys, shutil
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = '/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv'
MASTER = os.path.join(REPO, 'data', 'institutions_master.csv')
XWALK = os.path.join(REPO, 'data', 'rawdata_unitid_crosswalk.csv')
PREVIEW = os.path.join(REPO, 'data', 'institutions_master_with_cds.csv')
OUT_VALID = os.path.join(REPO, 'data', 'rawdata_join_validation.csv')
OUT_REPORT = os.path.join(REPO, 'data', 'rawdata_promotion_report.md')
BACKUP = ('/private/tmp/claude-501/-Users-peacespherical-Documents-GitHub-'
          'PIPO-Index/66fc5bde-feb6-4ef6-987c-4063571951cb/scratchpad/'
          'institutions_master.pre_rawdata.csv')

# RawData source headers used for validation (verified against printed headers)
RAW_ACC = 'Acceptance rate'                 # 0-100 scale
RAW_SAT75 = 'SAT 75th percentile'           # total (reading+math)
RAW_ACT75 = 'ACT 75th percentile'           # composite

CDS_FIELDS = ['commuter_pct', 'pct_demonstrated_need', 'pct_need_met',
              'pct_receiving_need_aid', 'pct_top10_hs', 'gpa_25th', 'gpa_75th',
              'gpa_band_below_100', 'gpa_band_100_199', 'gpa_band_200_249',
              'gpa_band_250_299', 'gpa_band_300_324', 'gpa_band_325_349',
              'gpa_band_350_374', 'gpa_band_375_plus', 'avg_aid_package_ug',
              'avg_need_grant_ug', 'avg_merit_grant_fresh', 'avg_pct_need_met_ug']

# SUSPECT thresholds
ACC_THRESH = 20.0      # median abs acceptance-rate gap (percentage points)
SAT_THRESH = 250.0     # median abs total-SAT gap when acceptance can't decide
MIN_ACC_YEARS = 2      # need at least this many overlapping acc years to trust the acc signal


def fnum(v):
    if v is None:
        return None
    v = str(v).strip().replace(',', '').replace('%', '').replace('$', '')
    if v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    if n % 2:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def load_crosswalk():
    """name -> unitid (only matched rows)."""
    m = {}
    with open(XWALK, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            uid = (row['unitid'] or '').strip()
            if uid:
                m[row['rawdata_school_name'].strip()] = uid
    return m


def load_master_truth():
    """(unitid, year) -> (acc_pct, sat_total, act) from trustworthy master cols."""
    truth = {}
    with open(MASTER, encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            uid = row['unitid'].strip()
            yr = row['year'].strip()
            acc = fnum(row.get('acceptance_rate'))
            acc_pct = acc * 100.0 if acc is not None else None  # 0-1 -> 0-100
            sr = fnum(row.get('sat75_reading'))
            sm = fnum(row.get('sat75_math'))
            sat_total = sr + sm if (sr is not None and sm is not None) else None
            act = fnum(row.get('act75_cumulative'))
            truth[(uid, yr)] = (acc_pct, sat_total, act)
    return truth


def validate():
    xwalk = load_crosswalk()
    truth = load_master_truth()

    # gather per-unitid, per-year comparison pairs from RawData
    # per_uid[uid] = {'names': set, 'acc': [absdiff], 'sat': [absdiff], 'act':[absdiff], 'years': set}
    per_uid = defaultdict(lambda: {'names': set(), 'acc': [], 'sat': [],
                                   'act': [], 'years': set()})
    with open(RAW, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            nm = row['School'].strip()
            uid = xwalk.get(nm)
            if not uid:
                continue
            yr = row['Year'].strip()
            m = truth.get((uid, yr))
            if m is None:
                continue
            m_acc, m_sat, m_act = m
            d = per_uid[uid]
            d['names'].add(nm)
            r_acc = fnum(row.get(RAW_ACC))
            if r_acc is not None and m_acc is not None:
                d['acc'].append(abs(r_acc - m_acc))
                d['years'].add(yr)
            r_sat = fnum(row.get(RAW_SAT75))
            if r_sat is not None and m_sat is not None:
                d['sat'].append(abs(r_sat - m_sat))
            r_act = fnum(row.get(RAW_ACT75))
            if r_act is not None and m_act is not None:
                d['act'].append(abs(r_act - m_act))

    results = []   # dict per unitid
    for uid, d in per_uid.items():
        med_acc = median(d['acc'])
        med_sat = median(d['sat'])
        med_act = median(d['act'])
        n_acc = len(d['acc'])
        # verdict: acceptance rate is the primary, unambiguous signal.
        verdict = 'OK'
        reason = ''
        if med_acc is not None and n_acc >= MIN_ACC_YEARS and med_acc > ACC_THRESH:
            verdict = 'SUSPECT'
            reason = f'acc_gap={med_acc:.1f}pp'
        elif med_acc is not None and n_acc == 1 and med_acc > ACC_THRESH + 15:
            # single overlapping year but a huge gap -> still suspect
            verdict = 'SUSPECT'
            reason = f'acc_gap={med_acc:.1f}pp(1yr)'
        elif med_acc is None and med_sat is not None and med_sat > SAT_THRESH:
            # no acceptance overlap to judge on; fall back to a very wild SAT gap
            verdict = 'SUSPECT'
            reason = f'sat_gap={med_sat:.0f}(no acc)'
        results.append({
            'unitid': uid,
            'rawdata_name': ' | '.join(sorted(d['names'])),
            'n_years': len(d['years']),
            'n_acc': n_acc,
            'median_acc_diff': med_acc,
            'median_sat_diff': med_sat,
            'median_act_diff': med_act,
            'verdict': verdict,
            'reason': reason,
        })

    results.sort(key=lambda r: (-(r['median_acc_diff'] or -1), r['unitid']))

    # matched_name from crosswalk (first name's matched_name)
    matched_name = {}
    with open(XWALK, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            uid = (row['unitid'] or '').strip()
            if uid and uid not in matched_name:
                matched_name[uid] = (row.get('matched_name') or '').strip()

    with open(OUT_VALID, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['unitid', 'rawdata_name', 'matched_name', 'n_years',
                    'median_acc_diff', 'median_sat_diff', 'verdict', 'reason'])
        for r in results:
            w.writerow([r['unitid'], r['rawdata_name'], matched_name.get(r['unitid'], ''),
                        r['n_years'],
                        '' if r['median_acc_diff'] is None else f"{r['median_acc_diff']:.2f}",
                        '' if r['median_sat_diff'] is None else f"{r['median_sat_diff']:.1f}",
                        r['verdict'], r['reason']])

    suspects = {r['unitid'] for r in results if r['verdict'] == 'SUSPECT'}
    return results, suspects, matched_name


def promote(suspects, dry_run=False):
    """Copy preview -> master, blanking the 19 CDS cols for SUSPECT unitids."""
    with open(PREVIEW, encoding='utf-8-sig', newline='') as f:
        r = csv.reader(f)
        header = next(r)
        rows = list(r)

    ncol = len(header)
    assert ncol == 69, f'expected 69 cols, got {ncol}'
    idx_uid = header.index('unitid')
    # indices of the 19 CDS cols
    cds_idx = [header.index(c) for c in CDS_FIELDS]
    assert cds_idx == list(range(50, 69)), f'CDS cols not at end: {cds_idx}'

    written = 0
    suppressed = 0
    coverage = defaultdict(set)   # field -> set(unitid) with non-empty value
    for row in rows:
        uid = row[idx_uid].strip()
        if uid in suspects:
            for i in cds_idx:
                if row[i] != '':
                    suppressed += 1
                    row[i] = ''
        for c, i in zip(CDS_FIELDS, cds_idx):
            if row[i] != '':
                written += 1
                coverage[c].add(uid)

    if not dry_run:
        # backup then write
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(MASTER, BACKUP)
        with open(MASTER, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    return {'n_rows': len(rows), 'n_cols': ncol, 'written': written,
            'suppressed': suppressed, 'coverage': coverage, 'header': header,
            'rows': rows}


def spot_check(rows, header):
    idx_uid = header.index('unitid')
    idx_year = header.index('year')
    cds_idx = {c: header.index(c) for c in CDS_FIELDS}
    out = {}
    for uid, name in [('186131', 'Princeton'), ('100858', 'Auburn')]:
        vals = {}
        for row in rows:
            if row[idx_uid].strip() == uid and row[idx_year].strip() == '2020':
                vals = {c: row[i] for c, i in cds_idx.items()}
                break
        out[name] = vals
    return out


def write_report(results, suspects, matched_name, promo, spot):
    n_suspect = len(suspects)
    examples = [r for r in results if r['verdict'] == 'SUSPECT'][:12]
    cov = promo['coverage']
    lines = []
    lines.append('# RawData CDS Promotion Report\n')
    lines.append('_Generated by `data_pipeline/promote_rawdata.py`. Cross-validated the '
                 'name-based RawData->unitid joins against trustworthy master columns '
                 '(`acceptance_rate`, `sat75_reading`+`sat75_math`, `act75_cumulative`), '
                 'then promoted the 19 CDS columns from the preview into '
                 '`institutions_master.csv`, suppressing values from SUSPECT joins._\n')
    lines.append('## Backup')
    lines.append(f'- `institutions_master.csv` backed up to:\n  `{BACKUP}`\n')
    lines.append('## Step 1 - Join cross-validation')
    lines.append(f'- Institutions with an overlapping-year comparison: **{len(results):,}**.')
    lines.append(f'- **SUSPECT joins (likely wrong unitid): {n_suspect}.**')
    lines.append(f'- Rule: SUSPECT if median absolute acceptance-rate gap > {ACC_THRESH:.0f} '
                 f'percentage points (acceptance rate is the unambiguous primary signal), '
                 f'with a fallback to a very wild SAT gap (> {SAT_THRESH:.0f} total points) '
                 f'when no acceptance-year overlaps.\n')
    lines.append('### SUSPECT examples (wrong name-matches caught)')
    lines.append('| unitid | rawdata name | matched to | n_years | median acc gap (pp) | median SAT gap | reason |')
    lines.append('|---|---|---|---:|---:|---:|---|')
    for r in examples:
        acc_s = '' if r['median_acc_diff'] is None else f"{r['median_acc_diff']:.1f}"
        sat_s = '' if r['median_sat_diff'] is None else f"{r['median_sat_diff']:.0f}"
        lines.append(f"| {r['unitid']} | {r['rawdata_name']} | "
                     f"{matched_name.get(r['unitid'], '')} | {r['n_years']} | "
                     f"{acc_s} | {sat_s} | {r['reason']} |")
    lines.append('')
    lines.append('Full detail: `data/rawdata_join_validation.csv`.\n')
    lines.append('## Step 2 - Promotion')
    lines.append(f'- Master now: **{promo["n_cols"]} columns x {promo["n_rows"]:,} data rows** '
                 f'(50 original + 19 CDS).')
    lines.append(f'- CDS values written: **{promo["written"]:,}**.')
    lines.append(f'- CDS values **suppressed** (blanked because their unitid was SUSPECT): '
                 f'**{promo["suppressed"]:,}**.\n')
    lines.append('## Final per-variable coverage (distinct schools) in promoted master')
    lines.append('| CDS field | distinct schools |')
    lines.append('|---|---:|')
    for c in CDS_FIELDS:
        lines.append(f'| `{c}` | {len(cov.get(c, set())):,} |')
    lines.append('')
    lines.append('## Spot checks (year 2020)')
    for name in ('Princeton', 'Auburn'):
        vals = spot[name]
        nonempty = {k: v for k, v in vals.items() if v != ''}
        lines.append(f'- **{name}**: ' +
                     (', '.join(f'`{k}`={v}' for k, v in nonempty.items()) if nonempty
                      else '(no CDS values for 2020)'))
    lines.append('')
    with open(OUT_REPORT, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    dry_run = '--dry-run' in sys.argv
    results, suspects, matched_name = validate()
    promo = promote(suspects, dry_run=dry_run)
    spot = spot_check(promo['rows'], promo['header'])
    if not dry_run:
        write_report(results, suspects, matched_name, promo, spot)

    print(f"VALIDATED institutions: {len(results)}")
    print(f"SUSPECT joins: {len(suspects)}")
    for r in [x for x in results if x['verdict'] == 'SUSPECT'][:8]:
        print(f"  SUSPECT {r['unitid']} '{r['rawdata_name']}' -> "
              f"'{matched_name.get(r['unitid'],'')}' "
              f"acc_gap={r['median_acc_diff']} sat_gap={r['median_sat_diff']} "
              f"({r['reason']})")
    print(f"PROMOTE cols={promo['n_cols']} rows={promo['n_rows']} "
          f"written={promo['written']} suppressed={promo['suppressed']}"
          + (' [DRY-RUN, master NOT written]' if dry_run else ''))
    print("SPOT Princeton 2020:", {k: v for k, v in spot['Princeton'].items() if v})
    print("SPOT Auburn 2020:", {k: v for k, v in spot['Auburn'].items() if v})


if __name__ == '__main__':
    main()
