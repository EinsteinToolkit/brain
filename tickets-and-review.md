# Tickets, review, and the release cycle

How a change actually gets into the Einstein Toolkit. This is the *social* protocol —
the technical gates it enforces live in [testsuite-authoring.md](testsuite-authoring.md)
and [thorn-anatomy.md](thorn-anatomy.md).

Read this before you open a ticket, before you ask for a review, and before you
interpret the state of an existing ticket.

---

## Where things live now

The ET is mid-migration off Bitbucket, and the shipped docs have not caught up — the
flesh's `Procedures.tex` still names BitBucket, and before that Trac. As of 2026-10-10:

| Thing | Now | Note |
|---|---|---|
| Issue tracker | `github.com/EinsteinToolkit/tickets` | Created 2026-09-03; issues only, no code |
| Wiki / policy pages | `github.com/EinsteinToolkit/wiki` wiki | `docs.einsteintoolkit.org/et-docs/*` 301s here — but to the wiki **home**, not the matching page, so every deep link in an old ticket is effectively dead |
| Many thorn repos | `github.com/EinsteinToolkit/*` | `Carpet`, `CarpetX`, `AsterX`, `SpacetimeX`, all `ExternalLibraries-*` |
| Flesh, `manifest` | still Bitbucket | Not in the GitHub org |
| Mailing list archive | `lists.einsteintoolkit.org` | Hyperkitty; `users@` is the public list |

Trac → Bitbucket → GitHub means a ticket can cite three different URLs for itself, and
old tickets and wiki pages cite all three. **The number never changed.** Trac was
redirected to Bitbucket by a bare `RedirectMatch ^/ticket/([^/]*)` onto the same id
(ticket 2240), and the GitHub import preserved the Bitbucket id as the issue number.
So `trac.einsteintoolkit.org/ticket/1717`, Bitbucket issue 1717 and GitHub issue 1717
are one ticket, and a bare `#1717` in a comment is resolvable as-is.

Clone the wiki rather than chasing redirects — it is a git repo of ~170 markdown
pages, and grepping it beats guessing page names:

```
git clone https://github.com/EinsteinToolkit/wiki.wiki.git
```

**The ET is a list, not a monorepo.** A component is "in the Einstein Toolkit" when a
correct checkout line for it exists in `einsteintoolkit.th` in the `manifest`
repository — nothing is copied anywhere. The thorn keeps living in its author's repo on
whatever host, which is why `manifest/einsteintoolkit.th` mixes Bitbucket and GitHub
`!URL` lines. Check what is where with:

```
grep '^!URL' manifest/einsteintoolkit.th | sed 's#.*= *\(https\?://[^/]*\).*#\1#' | sort | uniq -c
```

The practical consequence for a contributor: the ET needs either commit access for
maintainers to your repo (to cut the per-release `ET_YYYY_MM` branch and tag), or your
standing commitment to cut those branches yourself every six months. Donating the thorn
to a repo under `github.com/EinsteinToolkit` trades name-branding for not having to.

---

## Reading a migrated ticket

2970 of the 2984 tickets were imported by `et-bitbucket-to-github-migration[bot]`, so
almost every ticket has the bot as its GitHub author and no GitHub assignee. The real
metadata is in two places:

- **A quoted header at the top of the body** carrying the original reporter, assignee,
  state, kind, priority and dates. This is the authoritative provenance; the GitHub
  `user` field is not.
- **Labels**, which encode the Bitbucket fields:

| Label family | Meaning |
|---|---|
| `bb-state:*` | The Bitbucket state at migration — `new`, `open`, `resolved`, `closed`, `wontfix`, `invalid`, `duplicate`, `on-hold` |
| `bb-assignee:<Name>` | The original assignee. Most originals have no GitHub account, so this, not the assignee field, is who owns the ticket |
| `component:*` | `cactus`, `carpet`, `carpetx`, `einsteintoolkit-thorn`, `simfactory`, `getcomponents`, the websites, `other`, … |
| `kind:*` | `bug`, `enhancement`, `task`, `proposal` |
| `priority:*` | `blocker`, `critical`, `major`, `minor`, `trivial` |
| `version:*` | The release the problem was reported against, or `development-version` |
| `migration:missing-bitbucket-ticket` | A closed placeholder for a Bitbucket ticket that was deleted or never existed, keeping the numbering aligned. 8 of these |

Comments are migrated the same way: the bot is the GitHub author, and the real author
and date are in a leading blockquote line.

Two decoding traps:

- `needs-triage` is all but identical to `bb-state:new`, not an independent judgement —
  the migration applied it to every ticket never triaged on Bitbucket. 437 carry
  `bb-state:new`; 438 carry `needs-triage`, the extra one being a natively filed ticket
  that has no `bb-state:*` at all. It means "nobody ever looked", not "recently filed".
- GitHub has only open/closed, so the Bitbucket distinction between `resolved` (acted
  on, change applied) and `closed` (no further work) survives **only** in the label.
  `resolved` + `closed` + `wontfix` + `invalid` + `duplicate` are GitHub-closed;
  `new`, `open` and `on-hold` are GitHub-open, with six stragglers where the two
  disagree. Never infer "was it fixed?" from the GitHub state alone.

Migrated attachments are committed into the tracker repo itself, under
`attachments/bitbucket/<ticket>/<hash>/<filename>`, and linked from the body.

---

## Ticket metadata, as the project defines it

From the wiki's `Tickets` page, which is itself marked a work-in-progress.

**Kind** — `bug`: it does not do what it is supposed to. `enhancement`: a new feature
proposal. `task`: something to be done that changes no code. `proposal`: used in
practice for "include component X in the ET", which has its own review path (below).

**State** — `new` (untriaged) → `open` (someone will oversee it, usually doing the work)
→ `resolved` (change applied) / `closed` (no more work will be done). Plus `duplicate`,
`invalid`, `wontfix`, `on hold`.

**Priority** — these are release-oriented, not severity-oriented:

| | |
|---|---|
| `blocker` | The ET does not build, or development cannot continue. Immediate attention |
| `critical` | An important thorn is unusable or something is severely broken. If not addressed quickly, **the offending change should be reverted** |
| `major` | Must be fixed before the next release, or documented as broken in the release notes |
| `minor` | Not necessarily worth looking at before a release |
| `trivial` | Very low priority — not a claim that the fix is easy |

**Priority carries no information before 2019.** Every ticket created from 2010 through
2017 is `minor` — 100% of them, year after year — because that was the tracker's
default and nobody changed it. The field only starts being used at the Trac→Bitbucket
move: `minor` falls to 48% of new tickets in 2019 and 17% by 2025. So on an old
ticket read `priority:minor` as "unset", and on a recent one read it as a judgement.

**Assignee** means "expected to do the next piece of work, on a timescale of about a
week". It is a polite request, declinable, and should be cleared if a week passes with
no progress. **Milestone** is an `ET_YYYY_MM` release and means only "we would like this
looked at for that release"; it is not a commitment and routinely slips.

**Triage** is a maintainer action: check that the title and description make sense, set
priority and the other metadata, possibly assign, then move `new` → `open`.

---

## Asking for a review

The modern (post-Bitbucket) protocol, and it is short:

1. Open a ticket in `EinsteinToolkit/tickets` describing the problem.
2. Push the fix as a pull request **in the component's own repository** — never in the
   tickets repo, which holds no code.
3. Put the PR URL in the ticket, and suggest a reviewer on the PR.
4. Post a comment whose text is **`Please review`**.
5. Contact the reviewer out of band. Being suggested on a PR does **not** notify anyone.

Step 4 is not a figure of speech. The standing agenda of the weekly ET call links a
literal text search for that phrase, so it is the project's ready-for-review queue:

```
gh search issues --repo EinsteinToolkit/tickets --state open 'Please review'
```

When the review passes, approve and merge the PR, then set the ticket `resolved`,
ideally naming the resulting commit.

### The two-week rule

For changes that do not attract a reviewer, the project runs on lazy consensus. The
established form is a comment reading:

> Unless objected I will apply this after *YYYY-MM-DD*

where the date is **two weeks out**. "Unless objected" appears 133 times across the
tracker; of the 120 that name an explicit date, 108 are exactly 13 or 14 days out.
Silence is consent. The same construction is used to close a stale ticket, not just to
land a patch.

This is a convention, not a rule enforced by anything, and historically essentially one
maintainer drives it. If you are landing something uncontroversial and nobody has
reviewed it, this is the sanctioned way through — announce, wait the two weeks, apply.

### How the project wants you to review

From the wiki's `How to Review a Patch`, which is unusually explicit about the *spirit*
and is worth following literally.

What a review is for: a second pair of eyes on infrastructure many people depend on;
keeping contributions roughly aligned with where the ET is going; and the plain
deterrent effect of knowing the change will be read.

What to look at: is something obviously wrong — a corner case in C/C++/Fortran/Perl/Bash,
something that breaks on the stranger supercomputers, a bad interaction with a component
that has known bugs? Is the change a step in the wrong direction for the ET as a whole?

**A review is not a test.** The page is emphatic: in most cases you need neither apply
the patch nor run it. "Reviewing a paper doesn't require repeating a calculation
presented in the paper." Corner cases are found by reading code, not by running it.

Explicitly listed as *not* the reviewer's job, and as signs the review has gone off the
rails: checking that the patch still applies cleanly; running it to confirm it does what
it says; rejecting it merely because a cleaner implementation is imaginable (unless you
are volunteering to write that one); demanding the patch be split up when it is not
genuinely necessary; and nit-picking while accepting anyway. Reviewing is the project's
bottleneck, and the page frames a contribution as a gift: "We only want to make sure
there is no poison in there."

The one point the project openly disagrees with itself on is tests and docs. The page
says to accept and remind afterwards; an inline maintainer note argues that in practice
nobody ever does step in, so new *features* should be blocked until tests and docs
exist, while a *bugfix* matters more than its test case. Expect to be held to the
stricter reading for new functionality.

Changes to code that is new or under active development, and "obvious" corrections, do
not need review at all.

---

## Proposing a new component

A different, heavier path, documented on the wiki's `How to Review a new component`.
The authoritative requirements are the three on `einsteintoolkit.org/contribute.html`:
good enough for peer-reviewed published science; of current interest to the community;
and under an open-source licence.

**Formal criteria** — a reviewer checks these mechanically:

- A `README` in Cactus format, listing a maintainer who agrees to look after the
  component, an open-source licence, and a brief description. Authors are recommended.
- A `doc/documentation.tex` — **mandatory**. It must use the Cactus style file and carry
  the magic markers `% START CACTUS THORNGUIDE` / `% END CACTUS THORNGUIDE`, or the
  thorn silently does not appear in the online ThornGuide. It must build under
  `gmake <Thorn>-ThornDoc` and `gmake <Thorn>-ThornDocHTML`.
- Test cases in the thorn's test directory — see
  [testsuite-authoring.md](testsuite-authoring.md). The wiki page calls it `tests`; the
  flesh looks in `test`. Trust the flesh.
- Sensible descriptions for every parameter, scheduled routine and grid variable in
  `param.ccl`, `schedule.ccl`, `interface.ccl`.

**Quality criteria** — clarity, English comments, no dead or large commented-out
blocks, no obvious bugs; it compiles, it runs, it does not break anything already in the
ET. Plus the Cactus symbol rule: every externally visible symbol must be prefixed with
the thorn name (`MyThorn_DoSomething`, not `DoSomething`), unless it sits in a C++
namespace or Fortran 90 module whose *name* carries the prefix. The tests are also held
to explicit time and size limits — see [testsuite-authoring.md](testsuite-authoring.md).

**Correctness is explicitly out of scope.** Prior use in a peer-reviewed publication is
taken as sufficient evidence; the reviewer is not asked to re-derive the physics. The
publication and the demonstrated community interest are the release chair's business,
not the reviewer's.

Optionally, the reviewer may ask for a gallery example — which buys a fully worked
example re-tested every six months, and front-page visibility.

Related: **retiring** anything is also a process. A thorn or parameter must be marked
deprecated for at least one full release, with the notice carried in the **release
announcement**; deprecated thorns are marked as such in the thornlist and listed on the
ET website. No other active thorn's testsuite may depend on it — unless that test exists
only to test the doomed thorn. Both the deprecation and the retirement must come out of
a public discussion, usually on one of the calls. (`param.ccl` still has no way to mark
a parameter deprecated; the wiki lists that as wanted and unimplemented.)

---

## The release cycle

Two releases a year, nominally May and November, plus a code name. The cadence slips —
there was no `ET_2025_11`. Every component repo carries, for each release, a **branch**
`ET_YYYY_MM` and a **tag** `ET_YYYY_MM_v0`; `_v0` is the initial tag, not a respin
marker, and a respin becomes `_v1` (`ET_2013_11_v1`, `ET_2015_05_v1`, `ET_2020_05_v1`
all exist). Needing that branch and tag in your repo every six months is why the ET
wants commit access.

The schedule is written as offsets from release day. It is stable across *some* release
pairs — `ET_2024_11` and `ET_2025_05` match gate for gate — but it is not fixed: the
`ET_2026_05` cycle on the same wiki page is a coarser five-step plan that pulls
regeneration and the start of testing roughly three weeks earlier. Read the current
cycle's own entry in `Release-Details`; the table below (`ET_2025_05`) is the typical
shape, not a contract:

| Offset | Gate |
|---|---|
| −18 wk | Propose functionality for inclusion |
| −15 wk | Choose features; **ask for review volunteers**; open a ticket per item; fix the list of release-critical machines |
| −10 wk | All proposed code must be **in the master branch** — review may still be running |
| −6 wk | All reviews finished; regenerate Kranc and NRPy+ generated thorns; testing starts (testsuites, gallery examples, SimFactory on clusters, Docker/VM) |
| −5 wk | Decide the code name |
| −4 wk | **Feature freeze**; first draft of release notes; announce the date |
| −2 wk | Draft the release announcement |
| −1 wk | Testing done; **hard freeze**; cut branches; test-send the announcement |
| 0 | Release |

Two consequences worth internalising. The −10 wk / −6 wk pair is why an inclusion
proposal filed late in a cycle gets deferred: the code must be merged to **master** four
weeks before review ends, so that testers can exercise it while the review runs — the
release process says so explicitly, "code is present in master before final positive
review". And the regeneration step means Kranc- and NRPy+-generated thorns are rebuilt
from their generators before every release: if you hand-edit generated code, that is
when it is silently reverted.

The weekly ET call (Thursdays) is where reviewers are recruited, retirements are agreed,
and the ready-for-review queue is worked. Its agenda and minutes are the wiki's
`Meeting-agenda` page; minutes go to the `users@` list.

---

## Querying the tracker

Use `gh`, not the web UI; the ticket text is where the knowledge is, and the labels are
migration artifacts.

```
# Has someone already hit this? Full-text; search closed too, most of the tracker is.
# Terms are ANDed across the whole ticket, so two or three words beats a sentence.
gh search issues --repo EinsteinToolkit/tickets 'GetComponents certificate' --state closed

# The ready-for-review queue, same query the ET call uses
gh search issues --repo EinsteinToolkit/tickets --state open 'Please review'

# Everything open against one component at a given priority (labels AND together)
gh issue list --repo EinsteinToolkit/tickets --state open \
  --label component:carpetx --label priority:major

# Never triaged — the same set as --label bb-state:new. Oldest first:
gh issue list --repo EinsteinToolkit/tickets --state open --label needs-triage \
  --search 'sort:created-asc'

# One ticket with its full discussion. `gh issue view --comments` currently fails on
# this repo with a Projects-classic GraphQL deprecation error; go through the REST API.
gh api repos/EinsteinToolkit/tickets/issues/2747 --jq '.title, .body'
gh api 'repos/EinsteinToolkit/tickets/issues/2747/comments?per_page=100' --paginate \
  --jq '.[].body'
```

For bulk analysis, pull it all down once rather than paginating interactively — the
whole tracker is a few MB:

```
gh api 'repos/EinsteinToolkit/tickets/issues?state=all&per_page=100' --paginate \
  --jq '.[] | {number,title,state,labels:[.labels[].name],body}' > issues.jsonl
gh api 'repos/EinsteinToolkit/tickets/issues/comments?per_page=100' --paginate \
  --jq '.[] | {issue:(.issue_url|split("/")|last|tonumber), user:.user.login, body}' \
  > comments.jsonl
```

Searching closed tickets is the high-value move. Four fifths of the tracker is closed,
the problems recur — external-library detection, compiler-specific miscompiles,
GetComponents and certificates, Carpet/PreSync interactions — and the closing comment
usually names the commit that fixed it.

---

## What the tracker is good for, beyond its tickets

A few things only the tracker records:

- **Where undocumented semantics got pinned down.** The PreSync / `presync_mode` /
  READS-WRITES machinery that [schedule-and-presync.md](schedule-and-presync.md)
  describes appears in no shipped manual, and its corner cases — scoping, what a
  wrong `READS` declaration does, behaviour at `presync_mode = "off"` — were
  settled in tickets and nowhere else.
  `gh search issues --repo EinsteinToolkit/tickets presync` finds them.
- **Known-broken, still open.** Several long-standing defects are filed, triaged and
  simply not fixed. Before concluding you have found a new bug in Carpet, CarpetX or an
  `ExternalLibraries-*` thorn, search the tracker — the answer is often a ticket with a
  workaround in the comments.
- **Deprecations in flight.** Tickets are where a parameter or thorn is first proposed
  for removal, one release before the release notes mention it.
