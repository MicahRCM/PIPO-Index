# PIPO-Index — Data Update & Tool Overhaul Plan

Owner: Micah. Deadline-sensitive on **data**; website overhaul follows.
Decisions locked (2026-06-30):
- **Build everything** (data pipeline + full website/backend overhaul).
- **Next.js on Vercel** for the new app (read-only backend, no writes).
- **US News: aggressive scrape, user accepts ToS/legal risk.**
- **CDS: gap-fill only** (prefer USN/IPEDS/Scorecard; chase CDS only where no other source).

---

## 0. The two efforts

**Effort A — Data acquisition pipeline** (deadline item)
Goal: validated CSVs in a repo directory, one row per institution per year, keyed by **UNITID**, covering all variables below for **2003–2026** (USN labeling; IPEDS calls latest 2024/2025) across all in-scope USN categories.

**Effort B — Tool overhaul** (Next.js on Vercel)
Goal: modern app with a real data backend (API routes over the new dataset), unified schema, better charts + navigation, consolidating the 5 legacy tools and killing the embedded-JSON / magic-number architecture.

---

## 1. Scope: which schools

All institutions US News ranks in, for the latest (2026) edition:
- National Universities
- National Liberal Arts Colleges
- Regional Universities × 4 regions (North, South, Midwest, West)
- Regional Colleges × 4 regions (North, South, Midwest, West)

= 10 category lists. Categories shift yearly as criteria change → schools move in/out.
We need the **current** category membership per school, plus historical where available.
Today's data has only a `nationalu` binary + a rank; **category labels are net-new.**

## 2. Scope: which years
2003–2026. Realistically, source depth varies:
- College Scorecard: ~1996→present (deep, reliable).
- IPEDS / Urban Institute API: deep, reliable.
- USN: edition-by-edition; historical mostly via third-party repos.
- CDS: per-institution, spotty.
Coverage will be **logged per variable per year** — no silent gaps.

## 3. Variables (DV + IV) and sourcing

| Variable | Primary source | Notes |
|---|---|---|
| 1st→2nd yr retention (DV) | IPEDS/Scorecard | have 2016–2024 already |
| 6-yr graduation rate (DV) | IPEDS/Scorecard | |
| SAT 75th pct | IPEDS/Scorecard/USN | |
| ACT 75th pct | IPEDS/Scorecard/USN | |
| HS GPA | CDS/USN | **gap-fill / USN** |
| % top-10% of HS class | CDS/USN | **gap-fill / USN** |
| US News rank | USN | scrape |
| Acceptance rate | IPEDS/Scorecard/USN | |
| % commuter | USN | USN-only |
| % part-time | IPEDS | |
| % minority | IPEDS/Scorecard/USN | |
| % international | IPEDS/Scorecard/USN | |
| % w/ demonstrated need | CDS/USN | |
| % need fully met | CDS/USN | |
| aid merit-vs-need split | CDS/USN | |
| total aid package ($) | CDS/USN | |
| loan debt at graduation | College Scorecard/USN | |
| % Pell | IPEDS | computed |
| Pell graduation rates | IPEDS/USN | starts 2016–17 |
| Net cost by income band | IPEDS/Scorecard | 5 bands: 0-30k / 30-48k / 48-75k / 75-110k / 110k+ |

Exact field paths captured in `data_pipeline/variable_sources.md` (filled by feasibility spike).

## 4. The hard problem: UNITID matching
USN data has **no UNITID**. Many shared names (Saint Joseph's, Saint Mary's, …).
Plan:
1. Seed from existing 1,249 name→UNITID pairs already in `university_data.json`.
2. Build a deterministic+fuzzy matcher: normalize name + (state, city) → IPEDS UNITID
   (IPEDS HD institutional directory as the authority).
3. Auto-accept high-confidence unique matches; **flag every ambiguous/low-confidence/duplicate-name case** to a review table.
4. Deliver a **match-review table** (CSV + a rendered table) showing USN row → chosen UNITID → confidence → alternatives, for Micah to validate before it's locked.

## 5. Deliverables (Effort A)
- `data_pipeline/` scripts (Python), each source isolated and re-runnable.
- `data/` output: per-source raw CSVs + a merged `institutions_long.csv` (UNITID × year × variable) + `institutions_wide.csv`.
- `data/coverage_report.csv` — variable × year × source × % populated.
- `data/unitid_match_review.csv` — for manual validation.
- All keyed by UNITID; CSVs in a directory here for Micah to validate.

---

## 6. Subagent / workflow decomposition

### Phase 0 — Feasibility spike (IN PROGRESS)
- [agent] USN reachability + third-party-repo hunt → verdict on aggressive scrape.
- [agent] Scorecard + IPEDS/Urban exact field & year-coverage map.
Gate: confirm sourcing strategy before committing big fan-outs.

### Phase 1 — Reliable backbone (low risk, parallelizable)
- [agent] Extend Scorecard puller → all Scorecard variables, all UNITIDs, all years.
- [agent] IPEDS/Urban puller → retention, grad, Pell grad, part-time, demographics, net price by band.
- [agent] IPEDS HD directory pull → authoritative UNITID + name + city/state for matching.

### Phase 2 — USN acquisition + matching (RESHAPED by spike — paywall mostly irrelevant)
USN paywalls retention/6-yr-grad/%PT/%intl, but those are all in IPEDS already, so the USN job shrinks to:
- [agent, RUNNING] Reiter ingest → Nat'l U + LAC rank history 1984–2026 (LAC carries UNITID free).
- [agent] Headless-browser scrape of the **10 category listing pages** (Akamai → Playwright req'd) → category membership + rank + name + ZIP/city/state, esp. the **8 regional** lists Reiter lacks.
- [agent] Optional targeted USN **profile** scrape for **HS GPA** (free on profile, otherwise CDS-only).
- [agent] UNITID matcher (name + ZIP vs `ipeds_directory.csv`) → match-review table; auto-accept unique, flag duplicates (Saint Joseph's/Mary's).
- Gate: Micah validates the match-review table.

### Phase 3 — CDS gap-fill (targeted, fragile)
- [workflow] For variables with NO other source, on the highest-value schools only:
  pipeline over institutions → locate CDS PDF/page → extract → CSV. Log every miss.

### Phase 4 — Merge + validate
- [agent] Join all sources on UNITID×year → long + wide CSVs + coverage report.

### Phase 5 — Website overhaul (Next.js on Vercel) — Effort B
- [agent] Scaffold Next.js + TypeScript app, data layer reads merged dataset via API routes.
- [agent] Unified data schema + component-ize the 5 legacy tools (kill embedded JSON, magic numbers, single-letter keys; consolidate VAM/VAC).
- [agent] Modern charts (Chart.js v4 / ECharts / Recharts) + better nav + filter UX.
- Deploy to Vercel.

---

## 7. Risks / honesty
- **USN scrape**: legally on Micah's accepted risk; technically, much is client-rendered/paywalled — third-party repos may be the real unlock. Spike resolves this.
- **CDS**: 1000+ heterogeneous sites; expect partial coverage; gap-fill only.
- **UNITID matching**: duplicate names need human validation — that's the review table.
- **Year depth 2003–2026**: not every variable goes back to 2003; coverage report makes gaps explicit.

## 8. Cross-file / docs
Update `doc_map.md` as scripts and data files are added. Each script tested; one-off probes live in `test_scripts/`.
