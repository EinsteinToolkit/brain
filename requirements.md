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

## R2 — Integrate the restored driver.md (2026-10-10)

> "push it and then work on the follow-ups"

The three follow-ups raised after `driver.md` was restored:

- [x] Its reference table pointed at `DriverReference.tex` with no caveat, although
      `doc-traps.md` records that four of six functions there are under names that do
      not exist. The table now carries a per-row trust column.
- [x] It had no links to sibling files, and its `Driver_*` section duplicated
      `cctk-api.md`. The signatures now live in `cctk-api.md` alone, and the file links
      out to `cctk-api.md`, `schedule-and-presync.md`, `thorn-anatomy.md`,
      `build-system.md`, `layout.md` and `doc-traps.md`.
- [x] At 565 lines it was a third of the brain's prose, against `index.md`'s promise of
      one topic file per task. Split by audience: `driver.md` (362) keeps the contract
      and the driver comparison, matching its existing routing-table entry;
      `driver-implementation.md` (218) takes the thorn anatomy and the
      write-your-own checklist, which is a much rarer task. Numbered headings dropped —
      no other file in the brain uses them.

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
