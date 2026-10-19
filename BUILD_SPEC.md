# BUILD_SPEC: Emerging Artist Exposure Dashboard (Phase 3 MVP)

**Instruction to the builder.** Build the Streamlit dashboard described here in a new `app/` folder. The data and all analysis already exist: read the aggregate files through `analysis.store`, rescore live with `analysis.scoring`, and aggregate segments with `analysis.segments.summarize_segments`. Do not recompute metrics from raw listens inside the app, and do not change `analysis/` unless a check in section 9 fails. Start with the demo data (`data/demo/aggregates/`), which is synthetic and already built.

## 1. Revised vision

**User.** A music editorial lead at a streaming platform who picks which emerging artists get extra playlist and promotional exposure each cycle.

**Decision.** Which 10 to 20 emerging artists to shortlist for exposure this cycle, and which listener segment to aim that exposure at.

**Why it improves current practice.** Editorial picks usually lean on raw play counts, charts and editors' taste. Raw counts reward artists who are already big, or who have one superfan replaying them. This tool shows whether *new* listeners **come back** (return rate), whether listeners play on more than one day (repeat rate), whether reach is growing within the window, and whether listens are concentrated in one person. All of it is limited to artists below an "established" ceiling, so emerging artists are compared with each other on staying power instead of size.

**Changes since Phase 1.**
- Vision A (editorial lead) stays primary. Vision B (listener segments) survives as a supporting view: it informs *who* to target, not a separate product.
- The data is ListenBrainz incremental dump 2686 (created 2026-09-29), not complete user histories (docs/DATA_DECISIONS.md). So the analysis uses a fixed 28-day window, treats older rows only as history, and shows a data sufficiency check.
- "Emerging" is defined by audience size in the window (a listener band), not career age. The MusicBrainz merge for career age is post-MVP because 95.6% of listens have no artist MBID.
- Findings are associations. The data has no exposure or impression records, so the dashboard never claims that promotion causes listening.

### Core use cases (each must work in the MVP)

| ID | User selects or inputs | Dashboard shows | User decides |
|---|---|---|---|
| UC1 Shortlist | Population, listener band, evidence minimum, score weights | Ranked candidates with score and its four components, a reach vs return scatter, and why other artists were excluded | Which artists go on the exposure shortlist (downloads it) |
| UC2 Vet one artist | An artist from the shortlist or the search box | Weekly listeners and new listeners, return and repeat rates with sample sizes, concentration, segment return rates | Keep, drop, or wait a cycle for more evidence |
| UC3 Lead track | The same artist | Entry tracks: which track new listeners heard first and how many came back | Which track to feature in the playlist slot |
| UC4 Target segment | The current shortlist (implicit) | Return rate of new listeners by activity segment across the shortlist | Which listener segment to aim the recommendations at |
| UC5 Trust check | Data Notes tab | Coverage per day, MBID coverage, heavy-user share, sufficiency check, definitions | Whether the numbers are solid enough to act on this cycle |

Every view below names the use case it serves. Features not tied to a use case are out of scope.

## 2. Data flow and architecture

```
9.listens (raw JSONL, 3.2 GB, never modified)
  -> clean_listens.py           -> outputs/listens_clean.csv + audit CSVs
  -> prepare_analysis_data.py   -> data/processed/listens.parquet (typed, one row per listen)
  -> build_aggregates.py        -> data/aggregates/*.parquet + manifest.json
  -> app/ (Phase 3)             reads aggregates only; rescoring and segment sums run live
```

Each piece has one job and a file contract, so it can be built and checked alone. Changing one piece means rerunning the steps after it, never editing them.

| Piece | Job | Input to output | Check |
|---|---|---|---|
| `clean_listens.py` | Parse, standardize, deduplicate, flag | raw JSONL to cleaned CSV | `record_checks.csv`, audits |
| `prepare_analysis_data.py` | Type and slim the cleaned data | CSV to `listens.parquet` (`analysis.load.LISTENS_SCHEMA`) | row count equals cleaned rows |
| `analysis/keys.py` | Canonical artist and track keys | text to key | `tests/` |
| `analysis/load.py` | Population, window and non-artist filters | listens to filtered listens | `tests/` |
| `analysis/pairs.py` | Listener by artist discovery and return | listens to pair table | `tests/` |
| `analysis/artists.py`, `trends.py`, `entry.py`, `segments.py` | One aggregate each | pairs and listens to one table | `tests/` |
| `analysis/quality.py` | Coverage facts | listens to dict and daily table | manifest |
| `analysis/scoring.py` | Status, shortlist, score (live) | `artist_metrics` + `ScoringParams` to scored table | `tests/` |
| `analysis/store.py` | Aggregate file contract | tables to Parquet and back, with column validation | `read_aggregates` |
| `app/` (to build) | UI only | aggregates to screens | section 9 |

**App structure (to build).** `app/streamlit_app.py` wires everything and first adds the project root to `sys.path` so `analysis` imports under `streamlit run`; `app/data.py` holds the cached loaders; `app/controls.py` turns the sidebar into a `ScoringParams` and a population; `app/fmt.py` holds number formatting; `app/views/shortlist.py`, `artist.py`, `segments.py`, `notes.py` each expose `render(ctx)`. `ctx` is a dataclass holding the population's tables, the scored artist table, the params, and the manifest. Views never import each other. The only state views share is `st.session_state["selected_artist"]` (an `artist_key`, set only by a user action) and `["compare_artists"]` (a list); widget keys and the last valid weights are private to their module.

## 3. Technical design

| Choice | Decision and reason |
|---|---|
| Language and libraries | Python 3.10+, pandas, pyarrow, Streamlit 1.66+ (tested version; needed for `on_select` on tables and charts and `st.badge`), Plotly. Minimums in `requirements.txt`. |
| Heavy work | Offline in `build_aggregates.py`: about 16 s and 3 GB peak RAM for 5 M rows (stress test on scaled demo data). Runs once per data refresh, never in the app. |
| Storage | Parquet (zstd). The app reads 6 small tables (demo: about 260 KB total). Real aggregates keep only artists with 2+ window listeners, so they should stay in the tens of MB. If any file exceeds 50 MB, raise `AnalysisConfig.store_min_listeners`. |
| Memory and caching | Load all tables once with `st.cache_data`, keyed on the aggregate folder and manifest `generated_at_utc`. Rescoring (`score_artists`) and `summarize_segments` take milliseconds on about 100k artists, so they run on every rerun, uncached. |
| Data folder | Env var `EAE_DATA_DIR` (relative paths resolve from the project root). If the variable is set and that folder has no `manifest.json`, show `st.error` and stop. If it is not set, use `data/aggregates`, or `DEMO_DIR / "aggregates"` (`data/demo/aggregates`) when that has no manifest; if neither has one, show `st.error` and stop. Whenever `manifest["is_demo"]` is true, show a persistent yellow banner: "Synthetic demo data. Artists are invented; do not use for decisions." |
| Deployment | Streamlit Community Cloud from the repo. Commit `data/aggregates/` (built from the real dump) and never the raw dump, the cleaned CSV, or `listens.parquet` (all git-ignored). |

## 4. Data definitions

| Term | Definition |
|---|---|
| Listen | One cleaned row of the dump. |
| Window | UTC days 2026-09-01 to 2026-09-28 inclusive (`AnalysisConfig`). Rows outside it count only as history. |
| Early / late | Window days 1 to 14 / 15 to 28. |
| Artist | `artist_key` = whitespace-collapsed, NFKC, casefolded credit string. Collaborations are one entity. Credits in `NON_ARTIST_KEYS` ("various artists", "unknown") are excluded. Display name = most common raw name for the key; `primary_artist_mbid` (often empty) only adds a MusicBrainz link. |
| Population | `all`, or `exclude_heavy` (drops users the cleaner flagged above the 99.5th percentile of listens in the whole dump). Every table except `daily_coverage` (always all users) has both. |
| Listener of an artist | A user with at least one window listen of that artist. |
| New listener | Their first listen of the artist in all cleaned history falls inside the window. It is the first *observed* listen, not a proven discovery. |
| Eligible new listener | New listener whose first day is on or before 2026-09-21, so all 7 follow-up days fall inside the window. |
| Returned | Eligible new listener who played the artist again 1 to 7 days after their first day. |
| Segment | Listener's window listens across all artists: light < 50, moderate 50 to 499, heavy 500+. A "heavy" segment listener is not the same as a flagged heavy user, so the heavy segment still has members under `exclude_heavy`. |
| Stored artist | Artists with 2+ window listeners. Only these are in the aggregates, so the funnel total is below `window_artists` in Data Notes. |
| Status (live) | `below_floor`: listeners < min. `established`: listeners > max. `insufficient_evidence`: eligible new listeners < evidence minimum. Otherwise `candidate`. Checked in the listed order; the first matching rule wins. |
| Shortlisted | `candidate`, and not `single_fan_risk` when "Exclude single-fan risk" is on. |

## 5. Metrics

All from `artist_metrics` (one row per artist and population) unless noted. Filters: population always; band, evidence minimum and single-fan settings only where marked *live*.

| Metric | Question it answers | Calculation (columns) |
|---|---|---|
| Listeners | How big is the audience now? | `window_listeners` = distinct listeners in window |
| New listeners | Is it reaching people who had not played it? | `new_listeners` |
| Return rate | Do new listeners come back within a week? | `returned_new_listeners / eligible_new_listeners`; empty when eligible = 0. Shown with "n = eligible". |
| Repeat rate | Do listeners play it on more than one day? | share of listeners with 2+ active window days (`repeat_listener_rate`) |
| Growth | Is reach rising within the window? | `growth_ratio = (late_listeners + 1) / (early_listeners + 1)`; above 1 means growing |
| Top-listener share | Is it one superfan? | `top_listener_share` = top user's listens / artist listens; above 0.5 sets `single_fan_risk` (*live*) |
| Exposure score | Overall rank among candidates | percentile (0 to 100) of new listeners, return rate, repeat rate and growth *within the current shortlist*, weighted average with the sidebar weights (default 0.25 each). Ties: new listeners, then key. (*live*, `score_artists`) |
| Weekly series | When did listening happen? | `artist_weekly`: `listens`, `listeners`, `new_listeners` per week (4 weeks, `week_start`) |
| Entry track return | Which first track keeps people? | `entry_tracks`: new, eligible, returned and `return_rate` per (artist, first track heard) |
| Segment return | Which segment sticks after discovery? | `artist_segments` counts summed by `summarize_segments(table, artist_keys)`; rate = returned / eligible |
| Coverage facts | Can the numbers be trusted? | `manifest["data_quality"]`, `daily_coverage` |

## 6. Dashboard specification

### Global layout and controls

Page title "Emerging Artist Exposure", wide layout. A header line under the title: "Window: Sep 1 to Sep 28, 2026 (UTC) | Population: <choice> | Data built <generated_at_utc as YYYY-MM-DD HH:MM UTC>". Show the demo banner (section 3) and, if `data_quality.retention_sufficient` is false, a red banner: "Few listeners were active on 2+ days in this window, so return and repeat rates are unreliable. See Data Notes."

Sidebar (all changes rerun scoring instantly):

| Control | Widget | Default | Maps to |
|---|---|---|---|
| Population | radio: "All listeners" / "Exclude heavy users" | All listeners | `all` / `exclude_heavy` |
| Listener band | range slider 2 to 1000 | 5 to 200 | `min_listeners`, `max_listeners` |
| Evidence minimum | slider 1 to 30 | 5 | `min_eligible_new` |
| Exclude single-fan risk | checkbox | on | `exclude_single_fan` |
| Score weights (expander) | four sliders 0 to 1, step 0.05 | 0.25 each | `weights`; if all are 0, show an error and score with the last valid weights (other controls still apply) |
| Reset | button | | restores sidebar defaults only (not the selected artist, compare list or search box) |

Tabs in this order: **Shortlist** (starting view), **Artist Detail**, **Listener Segments**, **Data Notes**. Formatting: artist rates and top-listener share as whole percents, Data Notes shares with 1 decimal, growth as "x1.25", score with 1 decimal, counts with thousands separators, empty rates as "n/a".

### Tab 1: Shortlist (starting view; UC1)

1. **KPI tiles**: Shortlisted artists (count); Active listeners in population (sum of `segment_users.users`, not limited to the shortlist); Median return rate of shortlist; Median growth of shortlist.
2. **Funnel caption** from `status_counts`, plus the count of `status == "candidate" & single_fan_risk`: "1,070 candidates, 375 insufficient evidence, 13 established, 876 below floor; 125 single-fan risk removed". With the single-fan filter off, the last part reads "N single-fan risk kept (filter off)".
3. **Scatter** (Plotly) of shortlisted artists: x = new listeners (log scale), y = return rate, color = log2(growth) on a diverging red to gray to blue scale centered at 0, legend labelled in growth units, size = listeners. Hover: name, score, rank and the four components. Clicking a point sets `selected_artist`.
4. **Ranked table** (`st.dataframe`, single-row selection): Rank, Artist, Score, New listeners, Return rate, Eligible n, Repeat rate, Growth, Listeners, Top-listener share, MBID (yes/no). A text search box above it filters the whole shortlist by artist name (case-insensitive substring); the table shows the top 50 by rank (empty search) or up to 50 matches by rank. Selecting a row (or clicking a scatter point) sets `selected_artist` and shows the hint "Selected <name>. Open the Artist Detail tab." The app does not switch tabs automatically. Write `selected_artist` only inside the `on_select` callback when the selection changes (scatter hover data carries `artist_key`); a deselect does nothing.
5. **Download** button: full shortlist as `shortlist_<population>.csv`, raw values (rates as fractions 0 to 1, unrounded) with snake_case columns: `rank, artist_key, artist_name, exposure_score, new_listeners, return_rate, eligible_new_listeners, repeat_listener_rate, growth_ratio, window_listeners, top_listener_share, primary_artist_mbid`.
6. **Expander "Why isn't an artist here?"**: one row per stored artist that is not shortlisted, sorted by listeners descending then name, with a search box and columns Artist, Listeners, Eligible n, Top-listener share, Reason. Reason by status: below_floor "Fewer than <min> listeners"; established "More than <max> listeners"; insufficient_evidence "Only <n> eligible new listeners (need <min>)"; candidate with single-fan risk "Top listener has <x>% of listens". Artists with one listener are not stored; say so in a caption.

Empty state: if nothing is shortlisted, say "No artists meet these settings. Widen the listener band or lower the evidence minimum."

### Tab 2: Artist Detail (UC2, UC3)

1. **Artist picker**: searchable selectbox over all stored artists in the population, sorted by listeners (desc) then name, labelled "Name (listeners)". Default `selected_artist`; if unset or absent from the current population, show shortlist rank 1 (or the stored artist with most listeners if the shortlist is empty) without writing it to state. A user change updates `selected_artist`. Compare artists absent from the population are dropped.
2. **Header**: name; status badge, one of Shortlisted, Candidate (single-fan risk, excluded), Insufficient evidence, Established, Below floor; "Rank r of N, score s" if shortlisted; MusicBrainz link `https://musicbrainz.org/artist/<mbid>` if an MBID exists; "First observed in data YYYY-MM-DD" (`first_seen_day`: earliest listen in this population, all history, so imports can make it early).
3. **Metric tiles**: Listeners, New listeners, Return rate (n = eligible), Repeat rate, Growth, Top-listener share (red if single-fan risk).
4. **Weekly chart**: lines for listeners and new listeners per week from `artist_weekly`, x labels "Sep 1", "Sep 8", "Sep 15", "Sep 22".
5. **Compare** multiselect (up to 3 more artists, stored in `compare_artists`): a separate line chart of new listeners per week for the current artist plus those selected, and a side-by-side table of the tile metrics.
6. **Entry tracks** table (UC3): top 10 by new listeners: Track, New listeners, Eligible, Returned, Return rate. Show the rate only when eligible >= the evidence minimum, else "too few". Caption: "First track each new listener played, and whether they came back within 7 days. Listeners with an unknown first track are omitted."
7. **Segment bars**: return rate for this artist by segment (light, moderate, heavy) from `summarize_segments(artist_segments, [artist_key])` (fills missing segments with 0), labelled with eligible n; segments under the evidence minimum (including n = 0) show a text label "too few (n = k)" and no bar.

### Tab 3: Listener Segments (UC4)

1. **Segment table** from `segment_users`: Segment, Users, Window listens, Share of listens.
2. **Grouped bar**: return rate by segment over (a) the current shortlist and (b) all stored artists, from `summarize_segments` with and without the shortlist keys; label bars with eligible n; a segment under the evidence minimum shows "too few".
3. **Counts table** for the shortlist: artists, listener-artist pairs (a person counts once per artist), new, eligible, returned per segment.
4. **Caption**: "Aim exposure at the segment with the highest shortlist return rate, and check it beats the all-artist baseline." No other recommendation text.

### Tab 4: Data Notes (UC5)

1. **Daily coverage** bar chart: listens per day for the 60 days to Sep 28 (`daily_coverage`, all users), with a gray band behind the window days.
2. **Facts table** from `data_quality`: listen range, total and window listens, window share, window listeners and artists, MBID share, share of window listens from flagged heavy users, flagged heavy users in window, multi-day listener share, sufficiency (pass/fail, threshold 20%), last eligible discovery day, listener percentiles (p50, p90, p99, max) to help set the band, captioned "Over stored artists (2+ listeners), all users."
3. **Definitions**: the section 4 table, condensed.
4. **Limits**: ListenBrainz users are not a random sample of streaming listeners; first observed listen is not true discovery; name keys can merge namesakes; associations only, not the effect of exposure.

## 7. Build order

1. `app/data.py` and `app/streamlit_app.py`: folder choice, cached loading, demo banner, header, empty tabs. Run against demo data.
2. `app/controls.py`: sidebar to `ScoringParams` and population; scored table in `ctx`.
3. Shortlist tab: tiles, funnel caption, table with selection and search, download, exclusions expander, then the scatter.
4. Artist Detail tab: picker, header, tiles, weekly chart, entry tracks, segment bars, then compare.
5. Listener Segments tab.
6. Data Notes tab and the sufficiency banner.
7. Real data: run the full pipeline (README), check section 9 against the real manifest, commit `data/aggregates/`, deploy.

## 8. Out of scope for the MVP

MusicBrainz enrichment (career age, genre), splitting collaboration credits, segmentation beyond activity level, editing the window in the app (it is an offline setting), user accounts, and any causal estimate.

## 9. Acceptance checks

Run `python -m pytest -q` first (all tests pass). Then, on demo data with default controls. Click behavior may be verified with Streamlit's AppTest by calling the selection handlers, plus one manual browser check.

1. **Population "All listeners"**: funnel reads 1,070 candidates, 375 insufficient evidence, 13 established, 876 below floor, 125 single-fan risk removed; 945 shortlisted; rank 1 is Synthetic Artist 0131 with score 87.2, 42 new listeners, return rate 59%.
2. **"Exclude heavy users"**: 771 shortlisted; rank 1 is Synthetic Artist 0131 with score 88.7; rank 3 becomes Synthetic Artist 0178.
3. **Listener band 5 to 1000**: established drops from 13 and the shortlist grows; score and rank recompute without reloading data.
4. **Selecting** Synthetic Artist 0131 in the table or scatter, then opening Artist Detail, shows it with weekly listeners 13, 19, 21, 33 and new listeners 11, 8, 8, 15, and the top entry track "Track 01" (12 new, 5 eligible, 3 returned, 60%).
5. **Listener Segments** (All listeners): shortlist return rates are light 23%, moderate 34%, heavy 52%.
6. **All weights 0** shows an error and keeps the previous ranking (with other controls unchanged); Reset restores the defaults and check 1.
7. The **demo banner** shows on every tab; with `EAE_DATA_DIR` pointing to real aggregates it disappears and the header shows the real build time; pointing it at an empty folder shows an error.
8. **Download** gives a CSV with 945 data rows under check 1 settings.
9. With **real aggregates**, `manifest.data_quality.total_listens` equals the cleaned row count (5,022,599 if no rows are removed) and the Data Notes facts match `manifest.json`.
