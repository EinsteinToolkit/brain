# Notes (working memory)

## Crawl of 2026-10-10 — what was actually fetched

Everything below came from `gh api`, not HTML scraping. Raw dumps are in the session
scratchpad (`issues.jsonl`, `comments.jsonl`, `etwiki/`); they are *not* committed.

- `EinsteinToolkit/tickets`: 2984 issues (618 open / 2366 closed), 13094 comments.
  Repo created 2026-09-03; 2970 of the issues are Bitbucket migrations, 14 native.
- `EinsteinToolkit/wiki` wiki (`git clone https://github.com/EinsteinToolkit/wiki.wiki.git`):
  173 pages. `docs.einsteintoolkit.org/et-docs/*` now 301-redirects here.
- `EinsteinToolkit` GitHub org: 50 repos. No `manifest`, no flesh — those are still
  on Bitbucket. Migration is partial.

## Numbers worth not re-deriving

- "Unless objected" appears 133 times, **all** by Roland Haas. Of the 120 naming an
  explicit date: 14 d ×84, 13 d ×24 (= 108 at 13–14), 7 d ×3, 15 d ×3, 16 d ×3, 18 d ×1,
  plus 0/−352 outliers. → the two-week rule. The exact total is regex-sensitive; quote
  the 133 / 120 / 108 split rather than a single number.
- `bb-state:new` = 437 tickets, `needs-triage` = 438. They agree on 2983 of 2984; the
  extra `needs-triage` is #2970, filed natively and carrying no `bb-state:*`. Near-
  identical, not identical — do not call them the same set.
- Open tickets whose text contains "Please review": 32. My dump and the live GitHub
  search agree exactly — the dump is trustworthy.
- Patch-delivery eras, by comment year: attached patches 2010–2014 (131),
  Bitbucket PRs 2015–2025 (306), GitHub PRs 2024–2026 (93).

## Facts verified against the local checkout, not just the wiki

- Test directory is `test/`, **not** `tests/` — `RunTestUtils.pl` builds
  `arrangements/<Arr>/<Thorn>/test`. The wiki's review page says "tests"; it is wrong.
- `test.ccl` keywords (`RunTestUtils.pl::ParseTestConfigs`): ABSTOL, RELTOL, POSTPROC,
  NPROCS, EXTENSIONS, and `TEST <name> { ... }` blocks. A `config` file is the dead
  predecessor: the harness *only prints a warning* for it and never parses it, so a
  thorn with only `config` silently gets defaults. Do not write "still works".
- Tests are discovered by globbing `*.par` in `test/`; the stem must resolve to a
  directory **or** a `.tar/.tar.gz/.tgz/.tar.bz2/.tbz/.tar.xz/.txz` archive.
- The harness runs from `TEST/<config>/<Thorn>/` (`TESTS_DIR` default
  `$CCTK_HOME/TEST`), not the Cactus root — that is why test parfiles use `../../../`.
- The skip regex is `^(\.\#.*|\.|\.\.|.*\.par|CVS|.svn|.*~)$`. Generic dotfiles are
  **not** skipped.
- The multi-regex-match `die` fires at 4 tolerance sites (thorn-wide + per-test ×
  ABSTOL/RELTOL) plus 1 for POSTPROC — not thorn-wide only.
- Release tags: branch `ET_YYYY_MM`, tag `ET_YYYY_MM_v0`. `_v0` is the *initial* tag;
  respins are `_v1` (ET_2013_11_v1, ET_2015_05_v1, ET_2020_05_v1 exist).
- `manifest/einsteintoolkit.th` has 38 bitbucket `!URL` lines and 18 github ones.

## Deliberately left out

- The list of currently-open high-priority tickets. It drifts weekly; the brain's own
  rule is to document the query, not the snapshot. `tickets-and-review.md` has the query.
- `Organization-and-Responsibilities` wiki page: a stale per-person table. Site/people
  specific, so out of scope per the brain's conventions.
- Release code names (Hypatia, Kruskal, ...). Trivia; the wiki page is the pointer.

## driver.md was missing from the repo (resolved)

Commit `c9224f5` "Add driver info" moved the driver content *out* of `thorn-anatomy.md`
and replaced it with a pointer to `driver.md`, but never `git add`ed the new file — so
`index.md` (twice), `README.md`, `cctk-api.md`, `doc-traps.md` and `thorn-anatomy.md`
all linked to a file that was not in the tree. **Watch for this on the next commit:**
`driver.md` is still untracked, so it can be lost the same way again.

**Resolved 2026-10-10**: the user had the original in `~/Downloads/driver.md`. Restored
byte-identical (547 lines, 22 KB); the whole suite is green. Spot-checked against the
tree before placing it: PUGH really does overload `GroupStorageIncrease`/`Decrease` and
not `Enable`/`DisableGroupStorage`; all six `Driver_*` names in its table are real
aliased functions; all three drivers `implements: Driver` and schedule startup
`as Driver_Startup`. Only change made: one `&lt;` HTML entity on line 330 → `<`.

## Priority is era-dependent (worth remembering)

Every ticket created 2010–2017 is `priority:minor` — 100%, every year. It was the
tracker default and nobody touched it. Real use starts at the Trac→Bitbucket move:
48% minor in 2019, 34% in 2020, 17% in 2025. Filtering old tickets by priority is
therefore meaningless; filtering recent ones is not.

## test.ccl usage in a full checkout (corrects a wrong first guess)

104 `test.ccl` files under `repos/`: 70 set a tolerance, 53 set `NPROCS`. Keyword
occurrences: TEST 158, NPROCS 117, RELTOL 96, ABSTOL 79, EXTENSIONS 12, POSTPROC 5.
So loosening tolerances is the *normal* reason the file exists, not an edge case — I
first wrote the opposite. (An earlier pass here printed TEST 154 / NPROCS 111 from a
narrower shell glob that missed some thorns; `find . -name test.ccl` is the right scope.)
Avoid "N files are nothing but an NPROCS pin" — the answer swings between 10 and 26
depending on whether a bare `TEST { }` wrapper counts. The 70/53 split is unambiguous.

## Open questions

- (none)

## Fact-check pass (2026-10-10)

A verification pass over both new files against the flesh source, the live tracker and
the wiki found 14 errors in my first draft; all are fixed. The ones most worth not
repeating: `config` files do *not* still work; tests are found by globbing `*.par`, not
by scanning directories; the harness runs from `TEST/<config>/<Thorn>/`, not the Cactus
root; `_v0` is the initial tag, not a respin marker; the −10 wk gate is "in master
**branch**", not "in the master thornlist"; the review page's 1 GB limit is *memory*,
not file size; and the −Nwk schedule is not actually stable across all releases
(ET_2026_05 departs from it).

## driver.md integration (2026-10-10)

Split by audience, not by size: `driver.md` = the contract (what the flesh expects,
what each overload means, PUGH/Carpet/CarpetX comparison), which is what the routing
table already promised; `driver-implementation.md` = thorn anatomy + write-your-own
checklist. 362 and 218 lines, in range with the rest of the brain.

Verified nothing was lost: every non-blank line of the committed 565-line original is
present in the pair, modulo heading renumbering and three blocks rewritten on purpose
(the `Driver_*` section, the references table, one PreSync sentence).

`cctk-api.md` already owned the `Driver_*` signatures **and** the warning that
`DriverReference.tex` names four of them wrongly. driver.md had been restating the
table without the warning — a "one fact, one place" violation that also lost the
caveat. Signatures now live in `cctk-api.md` only.

Watch the typography when editing `driver.md`: it uses curly quotes, em-dashes and `…`
throughout, so exact-string matching on text containing an apostrophe will miss.
