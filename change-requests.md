# Change requests

## Module 9 — Jay Lai — October 23, 2026

Audit: [my-audit.md](my-audit.md). App baseline: `98ff0a6b1efc473e52d5691f9783b15f166df510`, branch `jay-lai`. Draft requests for review; no app changes authorized or implemented in this audit. This file did not exist at the start of the audit; there were no existing entries to replace.

### JL-M9-01 — Retain population and low-evidence regression checks

- **Type / priority / status:** test-coverage improvement / medium / proposed, pending Jay's review.
- **Evidence:** Jay manually observed 945 → 771 → 945 when switching All listeners → Exclude heavy users → All listeners at default settings. For Synthetic Artist 0131, Track 01 showed 12 new, 5 eligible, 3 returned, 60%; Track 06 (4 eligible) and Track 05 (1 eligible) showed “too few.” The standalone audit check independently reproduced those UI values, aggregate counts, and a 3/5 small-example rate.
- **Expected versus actual:** values match `BUILD_SPEC.md` sections 6 and 9. No failing app behavior was found. Existing `test_demo_controls` checks population counts, and selection tests check Track 01; they do not explicitly assert both Track 06 and Track 05 masking as a dedicated entry-track threshold regression.
- **Requested change:** in a later implementation task, retain the audit's explicit population round-trip assertion and add durable automated checks for both masked entry-track rows, the inclusive evidence boundary at n = 5, and the small example's day-1/day-7 versus same-day/day-8 return rules. Reuse/extend existing tests rather than duplicating them wholesale.
- **Acceptance:** default demo UI gives 945, 771, 945 in sequence; Track 01 at n = 5 shows 60%; Track 06 at n = 4 and Track 05 at n = 1 show “too few” at minimum 5. The seven-user example produces 7 new, 5 eligible, 3 returned, rate 0.6, with same-day/day-8 and late-discovery cases excluded appropriately.
- **Limitation / ownership:** this request addresses protection against future regressions, not a current spec failure. Proposed owner: dashboard maintainer; unassigned.

### JL-M9-02 — Explain the entry-track return denominator

- **Type / priority / status:** optional usability enhancement / low / proposed, pending Jay's review.
- **Evidence:** Track 01 has 12 new listeners but only 5 eligible; the correct rate is 3/5 = 60%, while dividing by all 12 would incorrectly give 25%. Code inspection confirms eligibility and grouping by the first track, with subsequent returns allowed to any track of the same artist.
- **Expected versus actual:** the current rate, counts, “too few” labels, and caption meet the specification. The entry-track caption does not itself explain the September 21 cutoff or explicitly state that return can be to another track. Data Notes provides additional definitions.
- **Requested change:** consider a short caption or help text beside Entry tracks explaining “returned / eligible,” the full seven-day follow-up requirement, and that a return is to the artist. Preserve existing counts, low-evidence masking, and the spec-required caption.
- **Acceptance:** the explanation lets a reader derive 60% from 3 returned / 5 eligible and understand why seven of the 12 new listeners do not enter the denominator, without changing computed values or implying that promotion caused a return.
- **Limitation / ownership:** this is an editorial proposal, not evidence that a user misunderstood the metric. Proposed owner: dashboard maintainer/editorial reviewer; unassigned.
