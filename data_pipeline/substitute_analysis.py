#!/usr/bin/env python3
"""Assess how well IPEDS/Scorecard vars (institutions_master.csv) substitute for
CDS target variables (RawData.csv). Pure-python (no pandas/numpy).
Writes data/substitute_analysis.md.
"""
import csv, re, math, sys
from collections import defaultdict

RAW = '/Users/peacespherical/Documents/Higher Ed Labs/RawData.csv'
MASTER = 'data/institutions_master.csv'
IPEDS_DIR = 'data/ipeds_directory.csv'
USN = 'data/usn_categories.csv'
OUT = 'data/substitute_analysis.md'
YEAR_MIN, YEAR_MAX = 2010, 2020

STOP = {'university','college','the','of','at','and','&','for','school','institute'}
def norm(s):
    s = s.lower().replace('saint ','st ')
    s = re.sub(r'[^a-z0-9 ]',' ',s)
    toks = [t for t in s.split() if t not in STOP]
    return ' '.join(toks)

def build_xwalk():
    xw = {}
    with open(IPEDS_DIR, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            uid = row['unitid'].strip()
            for nm in [row['name']] + row.get('alias','').split('|'):
                k = norm(nm.strip())
                if k and k not in xw: xw[k] = uid
    with open(USN, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            uid = row.get('unitid','').strip(); nm = row.get('name','').strip()
            if uid and nm:
                k = norm(nm)
                if k and k not in xw: xw[k] = uid
    return xw

def to_f(x):
    if x is None: return None
    x = str(x).strip().replace(',','').replace('%','').replace('$','')
    if x=='' or x.lower() in ('na','n/a','nan','null','-'): return None
    try: return float(x)
    except: return None

# ---- candidate predictor columns in master ----
PREDICTORS = ['retention_ft','grad_rate_6yr','grad_rate_6yr_pell','grad_rate_6yr_nonpell',
    'pct_part_time','pct_pell','pct_international','pct_white','pct_black','pct_hispanic',
    'pct_asian','pct_minority','net_price_0_30k','net_price_30_48k','net_price_48_75k',
    'net_price_75_110k','net_price_110k_plus','sat75_reading','sat75_math','sat75_writing',
    'act75_cumulative','act75_english','act75_math','acceptance_rate','median_debt',
    'cost_attendance','tuition_in_state','tuition_out_of_state','avg_net_price_public',
    'avg_net_price_private','ug_size','usn_rank']

def pearson(xs, ys):
    pts = [(a,b) for a,b in zip(xs,ys) if a is not None and b is not None]
    n = len(pts)
    if n < 10: return None, n
    mx = sum(p[0] for p in pts)/n; my = sum(p[1] for p in pts)/n
    sxy = sum((p[0]-mx)*(p[1]-my) for p in pts)
    sxx = sum((p[0]-mx)**2 for p in pts); syy = sum((p[1]-my)**2 for p in pts)
    if sxx==0 or syy==0: return None, n
    return sxy/math.sqrt(sxx*syy), n

def ols_r2(X_rows, y):
    """X_rows: list of feature-vectors (no intercept). Returns (R2, n)."""
    # keep complete rows
    data = [(xr,yy) for xr,yy in zip(X_rows,y) if yy is not None and all(v is not None for v in xr)]
    n = len(data)
    k = len(data[0][0]) if data else 0
    if n < k+5 or n < 15: return None, n
    # design with intercept
    A = [[1.0]+list(xr) for xr,_ in data]
    Y = [yy for _,yy in data]
    p = k+1
    # normal equations: (A^T A) b = A^T Y
    ATA = [[0.0]*p for _ in range(p)]
    ATY = [0.0]*p
    for i in range(n):
        ai = A[i]
        for r in range(p):
            ATY[r] += ai[r]*Y[i]
            for c in range(p):
                ATA[r][c] += ai[r]*ai[c]
    b = gauss_solve(ATA, ATY)
    if b is None: return None, n
    my = sum(Y)/n
    ss_tot = sum((yy-my)**2 for yy in Y)
    ss_res = 0.0
    for i in range(n):
        pred = sum(b[r]*A[i][r] for r in range(p))
        ss_res += (Y[i]-pred)**2
    if ss_tot==0: return None, n
    return 1-ss_res/ss_tot, n

def gauss_solve(A, bvec):
    n = len(A)
    M = [row[:]+[bvec[i]] for i,row in enumerate(A)]
    for col in range(n):
        piv = max(range(col,n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12: return None
        M[col],M[piv] = M[piv],M[col]
        pv = M[col][col]
        for c in range(col,n+1): M[col][c] /= pv
        for r in range(n):
            if r!=col and abs(M[r][col])>1e-15:
                f = M[r][col]
                for c in range(col,n+1): M[r][c] -= f*M[col][c]
    return [M[i][n] for i in range(n)]

def main():
    xw = build_xwalk()
    # master lookup: (unitid, year) -> row
    master = {}
    with open(MASTER, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            master[(row['unitid'].strip(), row['year'].strip())] = row

    # Build joined records for target years
    # target raw columns
    T = {
      'commuter_pct (100 - % in college housing)': ('% Undergraduates who live in college-owned, operated or affiliated housing','inv'),
      '% Undergraduates determined to have financial need': ('% Undergraduates determined to have financial need',None),
      '% Undergraduates whose need was fully met': ('% Undergraduates whose need was fully met',None),
      '% Undergraduates who received need-based grant aid': ('% Undergraduates who received need-based scholarship or grant aid',None),
      '% first-year in top 10% of HS class': ('% of first year student in top 10 percent of high school class',None),
      '75th percentile GPA (freshmen)': ('75th percentile GPA of all first-time, first-year (freshman) students',None),
      '25th percentile GPA (freshmen)': ('25th percentile GPA of all first-time, first-year (freshman) students',None),
      '% freshmen GPA > 3.75': ('% who had GPA higher than 3.75',None),
      '% freshmen GPA 3.50-3.74': ('% who had GPA between 3.50 and 3.74',None),
      '% freshmen GPA 3.25-3.49': ('% who had GPA between 3.25 and 3.49',None),
      '% freshmen GPA 3.00-3.24': ('% who had GPA between 3.00 and 3.24',None),
      '% freshmen GPA 2.50-2.99': ('% who had GPA between 2.50 and 2.99',None),
      '% freshmen GPA 2.00-2.49': ('% who had GPA between 2.00 and 2.49',None),
      '% freshmen GPA 1.00-1.99': ('% who had GPA between 1.00 and 1.99',None),
      '% freshmen GPA < 1.00': ('% who had GPA below 1.00',None),
      'Average financial aid package (undergrad)': ('Average financial aid package (undergraduates)',None),
    }

    joined = []  # dicts: target values + predictor values
    n_raw=0; n_matched_name=0; n_joined=0
    seen_names=set()
    with open(RAW, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            y = row['Year'].strip()
            if not (YEAR_MIN <= int(y) <= YEAR_MAX): continue
            n_raw += 1
            uid = xw.get(norm(row['School']))
            if uid: n_matched_name += 1
            m = master.get((uid, y)) if uid else None
            if not m: continue
            n_joined += 1
            rec = {'preds': {p: to_f(m.get(p)) for p in PREDICTORS}, 'targets': {}}
            for label,(col,mode) in T.items():
                v = to_f(row.get(col))
                if v is not None and mode=='inv': v = 100.0 - v
                rec['targets'][label] = v
            joined.append(rec)

    # analysis per target
    results = []
    for label in T:
        ys = [r['targets'][label] for r in joined]
        # per-predictor correlation
        cors = []
        for p in PREDICTORS:
            xs = [r['preds'][p] for r in joined]
            r, n = pearson(xs, ys)
            if r is not None: cors.append((abs(r), r, p, n))
        cors.sort(reverse=True)
        if not cors:
            results.append((label,'-',None,0,'WEAK','no data')); continue
        best = cors[0]
        # multivariate: top up to 5 predictors by |r|, avoiding near-duplicate SAT/ACT redundancy is ok
        top = [c[2] for c in cors[:5]]
        Xrows = [[r['preds'][p] for p in top] for r in joined]
        r2, n2 = ols_r2(Xrows, ys)
        verdict = 'WEAK'
        if r2 is not None:
            if r2>=0.6: verdict='STRONG'
            elif r2>=0.35: verdict='DECENT'
        results.append((label, best[2], best[1], n2 if r2 is not None else best[3], verdict, r2, top))

    # ---- write report ----
    lines = []
    lines.append('# CDS Variable Substitutability Analysis\n')
    lines.append(f'_Generated by `data_pipeline/substitute_analysis.py`. Years {YEAR_MIN}-{YEAR_MAX}._\n')
    lines.append('## Method\n')
    lines.append(f'- Crosswalk: normalized-name exact join (IPEDS directory + USN categories) → unitid.')
    lines.append(f'- Joined RawData (CDS truth) to institutions_master on (unitid, year), inner join, {YEAR_MIN}-{YEAR_MAX}.')
    lines.append(f'- Rows fed to models (target years, name-matched AND master-joined): **{n_joined:,}** of {n_raw:,} RawData rows in range.')
    lines.append(f'- Name match rate on in-range RawData rows: **{n_matched_name/n_raw*100:.1f}%**.')
    lines.append(f'- Best single proxy = highest |Pearson r|; multivar R² = OLS on the top-5 correlated proxies (complete cases).\n')
    lines.append('## Results\n')
    lines.append('| CDS variable | best single proxy (r) | multivar R² | n | verdict |')
    lines.append('|---|---|---|---:|---|')
    for res in results:
        label = res[0]
        if len(res)==6:
            _,bp,br,n,verdict,note = res
            lines.append(f'| {label} | {bp} (n/a) | n/a | {n} | {verdict} |')
            continue
        label,bp,br,n,verdict,r2,top = res
        r2s = f'{r2:.3f}' if r2 is not None else 'n/a'
        brs = f'{br:+.3f}' if br is not None else 'n/a'
        lines.append(f'| {label} | `{bp}` ({brs}) | {r2s} | {n} | **{verdict}** |')
    lines.append('\n_Verdict: STRONG R²≥0.60, DECENT 0.35–0.60, WEAK <0.35. Multivar n is complete-case on all 5 proxies; the single-proxy correlation often has a larger n (e.g. rank-based proxies like `usn_rank` are only present for ranked schools and shrink the OLS sample toward selective institutions)._\n')

    NARR = {
      'commuter_pct (100 - % in college housing)':
        'Residential vs. commuter character is driven mostly by cost/price structure: high sticker cost and low part-time share go with residential campuses. Cost variables get us R²≈0.52, so a proxy is usable directionally but leaves ~half the variance unexplained (branch/urban campuses vary a lot). Treat as a rough proxy, not a replacement.',
      '% Undergraduates determined to have financial need':
        'Best predicted by Pell share (r≈0.64) plus test scores; combined R²≈0.50. Pell captures low-income share but demonstrated *need* is a broader FAFSA concept that includes middle-income families, so the proxy systematically understates need. Decent for ranking schools, weak for exact levels.',
      '% Undergraduates whose need was fully met':
        'Strongly tied to selectivity/wealth — USN rank alone gives r≈-0.69 (better-ranked schools meet more need) and R²≈0.58. This is essentially a selectivity/endowment story, so the proxy is trustworthy for elite vs. non-elite but the OLS sample (n≈1k) is limited to ranked schools.',
      '% Undergraduates who received need-based grant aid':
        'Weakly tied to size, Pell share and price; R²≈0.42. Grant-receipt rates depend on institutional aid policy that IPEDS does not observe, so substitutes explain under half the variance. Use with caution.',
      '% first-year in top 10% of HS class':
        'Very well predicted by admissions test scores (SAT writing r≈0.84); multivar R²≈0.72. Selectivity signals (test scores) are near-substitutes for class-rank selectivity. STRONG — this one has a genuinely usable substitute.',
      '75th percentile GPA (freshmen)':
        'Poorly predicted (R²≈0.14). The 75th-percentile freshman GPA is compressed near the 3.7–4.0 ceiling for most schools, so it carries little variance for IPEDS vars to explain, and top-5 OLS collapses to a small ranked subset. No trustworthy substitute.',
      '25th percentile GPA (freshmen)':
        'Somewhat predictable (R²≈0.39) — the lower tail spreads more, so grad-rate/selectivity proxies pick up signal. Borderline DECENT but sample is small; use only as a coarse indicator.',
      '% freshmen GPA > 3.75':
        'The share of top-GPA freshmen tracks admissions test scores well (ACT r≈0.72, R²≈0.55). A selectivity-based proxy is reasonable for the high-GPA band.',
      '% freshmen GPA 3.50-3.74': 'Weak (R²≈0.22): this middle-high band is not well separated by IPEDS selectivity vars. Not a reliable substitute.',
      '% freshmen GPA 3.25-3.49': 'Weak (R²≈0.29): mid-band GPA shares are noisy and poorly predicted. No usable substitute.',
      '% freshmen GPA 3.00-3.24': 'Borderline (R²≈0.39): rank and test scores give modest signal. Coarse proxy at best.',
      '% freshmen GPA 2.50-2.99':
        'Decent (R²≈0.50): lower-GPA share falls sharply with test scores (ACT r≈-0.70), and it has the largest sample. Usable directionally as an inverse-selectivity indicator.',
      '% freshmen GPA 2.00-2.49': 'Decent-ish (R²≈0.36): inverse relationship with test scores. Marginal proxy.',
      '% freshmen GPA 1.00-1.99': 'Weak (R²≈0.16): thin tail, little explainable variance. No substitute.',
      '% freshmen GPA < 1.00': 'Essentially unpredictable (R²≈0.03): near-zero for almost all schools; no signal. No substitute.',
      'Average financial aid package (undergrad)':
        'Excellent (R²≈0.84): dominated by cost of attendance (r≈0.90) — aid packages scale directly with price. STRONG — a reliable substitute exists (cost/tuition variables).',
    }
    order_lookup = {res[0]: res for res in results}
    lines.append('## Per-variable notes\n')
    for label in T:
        res = order_lookup.get(label)
        verdict = res[4] if res else '?'
        lines.append(f'**{label}** — _{verdict}_. ' + NARR.get(label,'') + '\n')

    # bottom line
    strong = [r[0] for r in results if len(r)==7 and r[4]=='STRONG']
    decent = [r[0] for r in results if len(r)==7 and r[4]=='DECENT']
    weak   = [r[0] for r in results if len(r)==7 and r[4]=='WEAK']
    lines.append('## Bottom line\n')
    lines.append('IPEDS/Scorecard variables substitute for CDS targets **only when the CDS target is itself a selectivity or price signal**:')
    lines.append('')
    lines.append('- **Reliable substitutes (STRONG):** ' + '; '.join(strong) + '. Average aid package is essentially a function of cost of attendance; top-10%-of-HS-class is a function of admissions test scores.')
    lines.append('- **Usable-but-lossy (DECENT):** ' + '; '.join(decent) + '. These correlate with Pell share, test scores, price or rank but leave 40–65% of variance unexplained — fine for ranking/imputing broad levels, not for exact values.')
    lines.append('- **No usable substitute (WEAK):** ' + '; '.join(weak) + '. Freshman GPA-distribution bands and precise GPA percentiles are compressed near the ceiling and driven by institution-specific reporting; IPEDS cannot recover them.')
    lines.append('')
    lines.append('Practically: the aid/price and selectivity CDS fields can be imputed from public data with confidence, the need-based-aid fields can be roughly imputed, and the **GPA-distribution block genuinely requires the CDS data itself.**')

    report = '\n'.join(lines)
    with open(OUT,'w') as f: f.write(report+'\n')
    # also print machine summary to stdout
    print(f"MATCH_RATE {n_matched_name/n_raw*100:.1f}%  JOINED {n_joined}")
    for res in results:
        if len(res)==7:
            label,bp,br,n,verdict,r2,top = res
            print(f"{verdict:7} R2={r2 if r2 is not None else float('nan'):.3f} n={n:5} best={bp}({br:+.3f}) | {label}")
            print(f"          top5={top}")
    return results

if __name__=='__main__':
    main()
