# Change requests

## Claims

- Name: Jay Lai
- Feature checked: Population filter
- Number checked: Track 01’s return rate for Synthetic Artist 0131
- App commit: `98ff0a6b1efc473e52d5691f9783b15f166df510`
- Details: [my-audit.md](my-audit.md)

## Request 1: Keep tests for the filters

I switched from All listeners to Exclude heavy users and back. The shortlist showed 945 → 771 → 945, which matched the specification.

I also checked the entry-track table with the evidence minimum at 5. Track 01 had 5 eligible listeners and showed 60%. Tracks 06 and 05 had fewer than 5 eligible listeners and showed “too few.”

These checks passed. I suggest keeping automated tests for these cases so they still work after future updates. Codex helped run the automated checks.

Status: Suggested; no app changes made.

## Request 2: Explain “eligible listeners”

Track 01 showed 12 new listeners, but only 5 eligible listeners. With 3 returned listeners, the rate was 3/5 = 60%.

The calculation matched what I expected, but I think a short explanation beside the table would help users understand why the denominator is 5 instead of 12.

Suggested text: “Return rate uses new listeners with a full seven-day follow-up window. A return can be to any track by the same artist.”

This is a suggestion to make the table clearer, not a calculation error.

Status: Suggested; no app changes made.