# Requirements

Running record of instructions given by the user. Revisit periodically to confirm
we are still on track.

## R1 — Crawl the Einstein Toolkit ticket tracker (2026-10-10)

> "Crawl this site: https://github.com/EinsteinToolkit/tickets/issues, learn what
> you can about ticket reviews and other things about Cactus and Einstein
> Toolkit, and document them in this directory."

Acceptance:

- [x] Survey the tracker systematically (not a handful of sampled tickets) — all 2984
      tickets and 13094 comments pulled via `gh api`.
- [x] Extract what the tickets teach about **ticket review** — states, triage, the
      "Please review" queue, the two-week lazy-consensus rule, patch review vs.
      new-component review → `tickets-and-review.md`.
- [x] Extract other durable facts about Cactus / ET — the release cycle, where the ET's
      infrastructure now lives, and how to author a testsuite test (a review gate) →
      `tickets-and-review.md`, `testsuite-authoring.md`.
- [x] Document in this directory following the brain's conventions: routed from
      `index.md`, listed in `README.md`, glossary entries added, nothing site-specific,
      queries documented instead of snapshots that drift.
- [x] Technical claims re-verified against the checkout, not just the wiki — in
      particular `repos/flesh/lib/sbin/RunTestUtils.pl` for everything about `test/`
      and `test.ccl`.

Deliberately out of scope (see `notes.md` for why): a snapshot of currently-open
tickets, the wiki's per-person responsibility table, release code names.

Constraints inherited from `CLAUDE.md`:

- No software installs without asking. (None were needed; `gh` and `git` were present.)
- Never catch-and-ignore exceptions in any code written.
- Keep files small; refactor repeated logic into shared helpers.
- Write tests to verify behavior and avoid regressions.

## Standing: keep the brain's wiring intact

`tests/test_brain_consistency.py` checks that every relative link resolves, that every
topic file is reachable from `index.md`, that `README.md` lists them all, that no
markdown file contains tabs, and that no inline `` `code` `` span is wrapped across a
line break. Run it after editing:

```
python3 -I tests/test_brain_consistency.py
```

All five checks pass. (It briefly failed on a missing `driver.md`, linked from five
files but never committed; the user supplied the original and it is restored.)
