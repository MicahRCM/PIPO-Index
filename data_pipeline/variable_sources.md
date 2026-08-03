# Variable → Source → Field Map

Authoritative mapping for the data pipeline. Test institution for all probes: **UNITID 100663 (UAB)**.
Legend: **[curl✓]** value returned live this session · **[dict]** from official Scorecard data dictionary, not curl-verified · **[Urban✓]** curl-verified against Urban Institute API.

Scorecard base: `https://api.data.gov/ed/collegescorecard/v1/schools` — field paths use per-year prefix `{year}.<path>`.
Urban base: `https://educationdata.urban.org/api/v1/college-university/ipeds/{topic}/{year}/?unitid=...`
Year semantics: Scorecard `{year}` and Urban `{year}` both = IPEDS data-collection/academic year → **join directly by year**.
USN "2026" edition ≈ 2024–25 IPEDS collection.

## Consolidated table

| Variable | Scorecard field (`varname`) | IPEDS/Urban endpoint + field | Year coverage | Notes |
|---|---|---|---|---|
| 6-yr grad rate (overall) | `completion.completion_rate_4yr_150nt` (C150_4) [curl✓] | `grad-rates/{year}/` → `completion_rate_150pct`, filter `institution_level=4`, `race=99,sex=99` [Urban✓] | SC ~2003→latest; Urban **1996→2022** | 150%-of-time BA rate. Use `..._less_than_4yr_150nt` (C150_L4) for <4yr schools |
| Pell vs non-Pell grad rate | Pell `completion.completion_rate_four_year_150_pell` (C150_4_PELL); non-Pell = `_150_loan_nopell` + `_150_noloan_nopell` [dict] | `grad-rates-pell/{year}/` → `completion_rate_150pct`, `fed_aid_type` (1=Pell,4=NotPell,99=Total) [Urban✓] | SC first ≈**2016** prefix; Urban **2015→2017 only** | No single combined non-Pell rate in SC (split). Urban window only 3 cohort yrs. SC boundary unconfirmed (rate-limited) |
| SAT 75th pct | `admissions.sat_scores.75th_percentile.critical_reading` (SATVR75)=680 [curl✓]; `.math` (SATMT75)=708 [curl✓]; `.writing` (SATWR75) | (Scorecard preferred; IPEDS ADM source) | SC 2005+; null pre-2005 | spotty pre-2005 |
| ACT 75th pct | `admissions.act_scores.75th_percentile.cumulative` (ACTCM75)=30 [curl✓]; `.english/.math/.writing` [dict] | (Scorecard preferred) | same as SAT | — |
| US News rank | **ABSENT (confirmed)** | absent | n/a | USN-only — scrape/license |
| Acceptance rate | `admissions.admission_rate.overall` (ADM_RATE)=0.8854 [curl✓]; suppressed `admission_rate_suppressed.overall` | `admissions-enrollment/{year}/` (IPEDS ADM) | SC ~2003→latest | — |
| % part-time | `student.part_time_share` (PPTUG_EF)=0.2197 [curl✓] | `fall-enrollment/{year}/{level}/race/sex/` → `enrollment_fall`, split `ftpt` (1=FT,2=PT,99=Total) [Urban✓] | SC ~2003→latest; Urban **1986→2022** | SC gives ratio directly; Urban needs compute |
| % minority / race | `student.demographics.race_ethnicity.*` (UGDS_WHITE=0.5297 [curl✓], UGDS_BLACK, _HISP, _ASIAN, _AIAN, _NHPI, _2MOR, _NRA, _UNKN) | `fall-enrollment/{year}/{level}/race/sex/` → `enrollment_fall` by `race` (8=NRA,9=Unknown,99=Total) [Urban✓] | SC ~2003→latest; Urban 1986→2022 | %minority = 1−white−NRA−unknown. Pre-2009 uses `*_pre2010`/`*_2000` varnames |
| % international (NRA) | `student.demographics.race_ethnicity.non_resident_alien` (UGDS_NRA)=0.0233 [curl✓] | same endpoint, **`race=8`** [Urban✓] | SC ~2003→latest | intl = race code 8 (NOT 9=Unknown) |
| % Pell | `aid.pell_grant_rate` (PCTPELL)=0.3253 [curl✓]; `ftft_pell_grant_rate` (FTFTPCTPELL) | all-UG `sfa-all-undergraduates/{year}/` `percent_of_students` where `type_of_aid=5`; FTFT `sfa-ftft/{year}/` [Urban✓] | SC ~2003→latest; Urban all-UG **2007→2021**, FTFT **1999→2021** | use PCTPELL directly. PELL_EVER null recently |
| Net price by income band (5) | `cost.net_price.{control}.by_income_level.{band}` bands 0-30000/30001-48000/48001-75000/75001-110000/110001-plus = NPT41–45 + suffix `_PUB`/`_PRIV`/`_PROG`/`_OTHER` [curl✓ public: 13862/15370/16847/18230/20054] | `sfa-grants-and-net-price/{year}/` → `net_price` per `income_level` (1=<30k…5=110k+,99=All), filter `type_of_aid=9` [Urban✓] | SC ~2009→latest; Urban **2008→2021** | **per-school branch: only one control suffix populated** |
| Median loan debt at grad | `aid.median_debt.completers.overall` (GRAD_DEBT_MDN, NSLDS) = null 2021 [curl✓]; suppressed `median_debt_suppressed.completers.overall` | (NSLDS, not IPEDS) | **frozen — null recent; last-populated yr ~2014–2017 UNCONFIRMED** | SC moved debt to field-of-study files; re-probe |
| Cost / tuition | `cost.attendance.academic_year` (COSTT4_A)=26248 [curl✓]; `cost.tuition.in_state` (TUITIONFEE_IN)=8568; `.out_of_state` (TUITIONFEE_OUT)=20400; avg net `cost.avg_net_price.{public/private}` (NPT4_PUB/PRIV) | IPEDS IC/SFA | SC ~2003→latest | — |
| (helper) UG size | `student.size` (UGDS)=13284 [curl✓] | fall-enrollment totals | ~2003→latest | denominator |
| (helper) retention FT 4yr | `student.retention_rate.four_year.full_time` (RET_FT4) [curl✓] | `fall-retention/{year}/` → `retention_rate`, filter `ftpt=1` [Urban✓] | SC ~2005→latest; Urban **2003→2020** | existing repo field. Urban endpoint = `fall-retention` (not `student-faculty-retention-rate`) |

## CDS / USN-only gaps (confirmed in NEITHER IPEDS nor Scorecard)
- **HS GPA** (CDS C7) · **% top-10% HS class** (CDS C9) · **% commuter** (CDS F1) · **% need met** (CDS H2) · **merit-vs-need aid split** (CDS H2/H2A) · **total aid package** (CDS H2).
- IPEDS/Scorecard give *average grant / net price* (partial overlap) but NOT need/merit decomposition or "% need met".

## Scorecard items to RE-PROBE with a real API key (DEMO_KEY rate-limited)
1. **Latest populated year-prefix per variable** — site claims 1996-97→2025-26 (upd. 2026-06-10) but cohort-lagged vars (grad/retention) lack 2024/25. Probe `2022..2025.{tuition,retention}` for the real edge.
2. **Median-debt boundary** (GRAD_DEBT_MDN) — null at 2021; find last populated year (test 2014/2016/2017/2018).
3. **Pell-completion boundary** (C150_4_PELL) — likely first 2016; confirm 2014/2015/2016.

## Implications for pullers
- **Scorecard is the primary backbone** for SAT/ACT/admit/%PT/race/%intl/%Pell/cost/net-price — shares/ratios come pre-computed, single request per school-year batch.
- **Urban/IPEDS** = cross-check + reaches **2003** for retention and **1996** for grad rates (deeper history than some SC fields), and is the fallback where SC is null.
- **Net price requires a per-school control-suffix branch** (`_PUB` vs `_PRIV` vs `_PROG`/`_OTHER`).
- **Hard historical limits:** net price starts 2008 (IPEDS-wide); Pell grad rates only 2015–2017 (Urban) / 2016+ (SC). Document as known gaps in `coverage_report.csv`.

## US News (from feasibility spike)

**Access:** `www.usnews.com` is behind **Akamai** — plain `curl`/WebFetch are silently dropped; **requires headless browser** (Playwright/Puppeteer + human-like pacing). Listing cards paywall academics ("Unlock with Compass") but **individual profile pages are server-rendered and show them free**.

**10 category listing pages** (2026 edition), pattern `https://www.usnews.com/best-colleges/rankings/<slug>`:
`national-universities` (436), `national-liberal-arts-colleges` (207), `regional-universities-{north,south,midwest,west}` (~120–170 ea), `regional-colleges-{north,south,midwest,west}` (~30–80 ea). Lists are React-virtualized (scroll/Load-More needed). Cards give: rank, name, city+state, public/private, founded, tuition, enrollment. **~1,500–1,800 ranked schools total.**

**Free on profile pages:** acceptance rate, SAT/ACT 25–75 range, **HS GPA**, 4-yr grad rate, student-faculty ratio, % first-years w/ need-based aid, avg need-based aid package, avg net price, tuition, **% international + race breakdown**, **city/state/ZIP**, median salary 6yr.
**Paywalled (Compass):** first-year retention, **6-yr grad rate**, **% top-10% class**, % part-time, **% need fully met**, **merit-vs-need split**, itemized cost.

**No UNITID** anywhere on USN (its school id is a proprietary slug, e.g. Princeton=`2627`). Match via **name + ZIP/city/state** against `ipeds_directory.csv`.

**Third-party shortcuts:**
- **Andy Reiter (andyreiter.com/datasets):** USN rank history — **National Univ top-150 & LAC, 1984–2026; LAC carries UNITID.** Skips scraping + matching for those. **No regional categories.**
- frishberg/Archive-of-US-News (National ranks 1984–2024, no UNITID), kaijchang scraper (old internal `/best-colleges/api/search` JSON, freshness unknown), Chenzilla (all-category ~1,790 but ~2010s/old), Kaggle mirrors of Reiter.

**Strategy (paywall mostly irrelevant):** retention/6-yr-grad/%PT/%intl that USN paywalls are all in IPEDS already. So USN work = (1) Reiter ingest for Nat'l+LAC rank history (UNITID free), (2) headless scrape of 10 listing pages for **category membership + rank + ZIP** (esp. the 8 regional Reiter lacks), (3) optional targeted profile scrape for **HS GPA** (free, otherwise CDS-only). Compass paywall ≈ not needed.
