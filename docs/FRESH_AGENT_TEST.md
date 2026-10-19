# Fresh-Agent Test Log

Two fresh coding agents with no project context got the repository and were told to follow BUILD_SPEC.md and record every question or guess.

## Pass 1: full build (agent built `app/` from the spec against demo data)

Result: all demo acceptance checks 1 to 8 passed with the spec's numbers (945 and 771 shortlisted, 0131 scores 87.2 and 88.7, weekly 13/19/21/33, segment rates 23/34/52%, 945-row CSV). Check 9 needs the real dump.

Important gaps it logged, all now settled in BUILD_SPEC.md:

| Gap | Fix in spec |
|---|---|
| Does selecting a row jump to Artist Detail? | No auto switch; hint text; state written only on selection change (§6 Tab 1) |
| Clicks cannot be tested headless | AppTest handler calls plus one manual browser check (§9) |
| Streamlit 1.35 too old for features used | 1.66+ (§3, requirements.txt) |
| "Window listeners" tile scope | Renamed "Active listeners in population" (§6 Tab 1) |
| Exclusion expander overlap and missing statuses | One row per non-shortlisted stored artist with a defined Reason per status (§6 Tab 1) |
| Search scope, CSV format | Search whole shortlist then top 50; raw snake_case CSV columns listed (§6 Tab 1) |
| All weights 0 with other controls changed; Reset scope | Last valid weights, other controls apply; Reset is sidebar only (§6 sidebar) |
| Segment counts are not distinct people | Column named "listener-artist pairs" (§6 Tab 3) |
| Thin segments in shortlist bars | Same evidence minimum applies (§6 Tab 3) |
| Selected artist missing after population change; default selection | Fallback to rank 1 without writing state; drop missing compare artists (§6 Tab 2) |
| Badge states, compare chart placement | Five badge states listed; separate compare chart including current artist (§6 Tab 2) |
| Bad `EAE_DATA_DIR` silently falls back to demo | `st.error` and stop (§3) |
| Funnel text with single-fan filter off | Wording given (§6 Tab 1) |

## Pass 2: spec and code consistency review (no build)

It recomputed every §9 number from `analysis/` and confirmed column names match `analysis.store.TABLE_COLUMNS`. Remaining items it raised were fixed: status rule order wording, empty-search row count, selection-callback rule, single-fan funnel count definition, empty-shortlist fallback, `first_seen_day` meaning, no-manifest-anywhere error, heavy-user share label, percentile caption, entry-track omission note, using `summarize_segments` for one artist's segments, expander sort order.
