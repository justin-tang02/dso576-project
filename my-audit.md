# My Module 9 audit

## Context

- Name: Jay Lai
- Team app and version checked: Emerging Artist Exposure Dashboard, branch `jay-lai`, commit `98ff0a6b1efc473e52d5691f9783b15f166df510`.
- Intended user and decision: A music editorial lead choosing emerging artists for playlist or promotional exposure.

## 1. Feature audit

- Feature and intended behavior: The population filter should update the shortlist when heavy users are excluded.
- Inputs and steps: I used the demo data with the default settings: listener band 5–200, evidence minimum 5, single-fan exclusion on, and equal weights. I switched from All listeners to Exclude heavy users, then back.
- Expected behavior: The shortlist should show 945, then 771, then 945 artists.
- Actual behavior and evidence: I observed 945 → 771 → 945 and captured screenshots. Codex also reproduced this sequence with an automated check.
- Conclusion and recommended change: This matched BUILD_SPEC.md. I recommend keeping a test for switching back and forth so future changes do not break it. This is request JL-M9-01.

## 2. Number audit

- Number and meaning: Track 01’s return rate for Synthetic Artist 0131. This measures how many eligible new listeners came back to the artist within seven days.
- Formula, units, population, and window: Returned / eligible new listeners × 100. It is a percentage from 0%–100%. I used All listeners and the September 1–28, 2026 UTC demo window.
- Assumptions: Eligible listeners need seven full follow-up days, so their first observed listen must be by September 21. Same-day replays do not count. A return can be to another track by the same artist. “New” means first observed in the available data.
- Code checked: Codex inspected `analysis/pairs.py::listener_artist_pairs` and `analysis/entry.py::entry_tracks`. The return condition is `(gap >= 1) & (gap <= cfg.return_horizon_days)`.
- What the code does: It identifies eligible listeners, checks whether they return on days 1–7, and groups them by the first track they heard.
- Small test and expected result: Codex helped create seven example listeners. Five were eligible and three returned, giving 3/5 = 60%. The example included same-day and day-8 replays that should not count, plus late discoveries that should not be eligible.
- Actual result: Codex reported that the example returned 5 eligible, 3 returned, and 60%. In the dashboard, Track 01 showed 12 new listeners, 5 eligible, 3 returned, and 60%.
- My calculation: 3 / 5 × 100 = 60%, matching the display. Using all 12 new listeners would give 25%, but that includes people without a complete follow-up window.
- What remains uncertain: I did not trace the demo listeners back to their original records or test the full real dataset. These checks support the selected calculation, not every number in the app.
- Recommended change: Explain the eligible-listener denominator beside the table. This would make the difference between 12 new and 5 eligible easier to understand. This is JL-M9-02. I did not find a calculation bug.

## My contribution

- I manually checked the population filter, displayed counts, return-rate arithmetic, and “too few” labels for tracks below the evidence minimum.
- Codex helped build the app before the audit, inspect the code, run the example and automated checks, and draft the report. It reported three targeted tests passed. I did not independently verify the original listener classifications.

## Reproducible check

The code below checks the stored Track 01 values and the small example.