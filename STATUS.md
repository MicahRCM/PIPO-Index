# PIPO-Index — Current State (resume point)

_Durable checkpoint so context can compact / a fresh session can resume. See PLAN.md for the full plan, doc_map.md for file relationships, data_pipeline/variable_sources.md for the field map._

## DONE
- **Data pipeline (IPEDS + Scorecard):** `data/institutions_master.csv` (48,076 rows · 1,249 schools · 2003–2024 · 33 vars + directory + Reiter rank) + `_long`/`_wide` + `coverage_report.csv`. Validated.
- **Directory + Reiter:** `data/ipeds_directory.csv` (6,072, coords), `data/usn_rank_history.csv` (Nat'l+LAC ranks w/ UNITID).
- **Web app (`web/`, Next.js 16):** ALL 6 tools live + on the merged dataset — Retention, VAI, VAM, VAC, CAS, **Map** (`institutions.json` via `build_app_dataset.py`). Editorial "Privilege Atlas" design system; zoom/pan on scatters; shared `InstitutionPicker`; all `max-w-7xl px-6`. tsc/eslint clean, all routes 200. Dev server runs on :3000.
- **USN scrape (first pass):** all 10 categories scraped → `data/usn_categories.csv` (1,436 schools, 99% matched) + `data/usn_match_review.csv`. Match script `data_pipeline/match_usn.py`.
- **CDS (National Universities free-tier):** `data/cds_data.csv` (142) + `data/cds_blocked.csv` (232) via `data_pipeline/fetch_cds.py`.

## RUNNING (background agents)
- **USN finish + matcher-harden** (browser): re-scraping National Universities (was 390/436) + National LAC (201/207), fixing wrong matches (CU-Denver→Univ of Denver, CSU LB/Fullerton swap, branch campuses), regenerating clean `usn_categories.csv` + `usn_match_review.csv`. → produces the **match-review table for user validation**.
- **CDS parser-harden** (no browser): recovering `pdf_parse_fail` (74, AcroForm/two-column), `stale_only` (21), xlsx; widening year window to 2025-26.

## QUEUED (needs the browser; waits for USN finish agent)
- **Browser tier**: Cloudflare/Box/JS-viewer CDS schools + **US News profile scrape for HS GPA / % top-10% class** (user wants GPA from USN, not CDS).
- **Scale CDS** to the other ~875 schools (regional + LAC categories).
- User's **max-push** CDS decision is logged: free tier + parser recovery + browser tier + USN profiles.

## NEXT USER-FACING STEP
Present the cleaned **USN match-review table** for manual validation of duplicate-name/ambiguous schools.

## NOTES
- Scorecard API key in `data_pipeline/.scorecard_key` (gitignored).
- USN scraping via Playwright MCP browser bypasses Akamai; usnews ad scripts spawn malvertising popup tabs — agents auto-close them.
- Data ceiling = 2024 (IPEDS 2025/26 not released). USN "2026" edition ≈ 2024 collection.
