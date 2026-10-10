# Cactus Brain

A compact reference for the **Cactus Code** / **Einstein Toolkit** codebase, written to
be read by an AI coding assistant working in a Cactus checkout.

`index.md` is the entry point and is addressed to the assistant. This file is for you.

## Why this exists

Cactus is large, and the documentation it ships with is an unreliable guide to it:

- Several `MaintGuide` chapters (`CST.tex`, `Schedule.tex`, `Comm.tex`, `IO.tex`,
  `Util.tex`) are **empty stubs**.
- Around thirty API signatures in `CCTKReference.tex` disagree with the headers, and four
  of the six functions in `DriverReference.tex` are documented under names that do not
  exist.
- `ReleaseNotes` stops in 2014.
- Mechanisms that are entirely load-bearing — the CST's PEG-based CCL parsing, the
  `READS`/`WRITES` PreSync machinery, `presync_mode`, GetComponents, SimFactory — are
  documented **nowhere**.

So an assistant dropped into the tree either re-derives all of this from source every
session, burning context and time, or quietly gets it wrong. This is the distilled
version, verified against source.

## How to use it

Point your assistant at `repos/brain/index.md`. It reads the index, matches its task
against the routing table, and loads **one** topic file. The design target is minimal
context: the index is ~130 lines, and no single task should need more than one topic
file on top of it.

Humans get the most out of `troubleshooting.md` (symptom → cause → fix) and
`doc-traps.md` (where the shipped LaTeX will mislead you).

## Contents

| File | Covers |
|---|---|
| `index.md` | Entry point: mental model, routing table, ground-truth ranking, glossary |
| `layout.md` | Tree layout, the `repos/` ↔ `arrangements/` symlink layer, inside `configs/<cfg>/` |
| `thorn-anatomy.md` | The CCL files, grid variables, `CCTK_ARGUMENTS`, adding a thorn |
| `driver.md` | The `Driver` contract: overloads, GH extension, PUGH vs Carpet vs CarpetX |
| `driver-implementation.md` | Writing a driver: thorn skeleton, startup registration, SetupGH, checklist |
| `schedule-and-presync.md` | `schedule.ccl`, bins, READS/WRITES, `presync_mode`, poison/checksum checking |
| `cctk-api.md` | Which header holds what, the `Driver_*` API, signature traps |
| `build-system.md` | CRL vs CST thornlists, configure → CST → compile, make targets, optionlists |
| `external-libraries.md` | `detect.sh` vs `build.sh`, MPI, CUDA, ROCm/HIP, AMReX startup costs |
| `simfactory.md` | MDB, machine resolution, per-configuration files, `envsetup` vs runscript |
| `testsuite-authoring.md` | Writing a test case: `test/` layout, `test.ccl`, tolerances, design rules |
| `tickets-and-review.md` | The ET tracker, how patches and new components get reviewed, the release timeline |
| `troubleshooting.md` | Symptom → cause → fix, including performance surprises |
| `doc-traps.md` | Where `repos/flesh/doc/*` contradicts the source |

## Conventions for editing

- **One fact, one place.** If two files would state it, put it in the more specific one
  and link. The routing table is the only intentional duplication.
- **Cite a path and a grep-able symbol**, not a line number, unless the line is stable.
- Prefer *how to find out* over a snapshot that will drift — e.g. `cactus_<cfg> -S` for
  the schedule tree rather than a pasted list.
- **Nothing site-specific.** Machine names, cluster partitions, and one-off
  configurations do not belong here. This describes Cactus, not an installation.
- Verify before you write. Much of what is here exists precisely because a plausible
  secondary source turned out to be wrong.

## Provenance

Distilled from earlier source audits and re-verified against this checkout on
2026-09-17: flesh `ET_2026_05` / `Cactus_4.20.0_v0`.

`tickets-and-review.md` and `testsuite-authoring.md` were added on 2026-10-10 from a
full crawl of `github.com/EinsteinToolkit/tickets` (2984 tickets, 13094 comments) and
the `EinsteinToolkit/wiki` wiki, with every technical claim re-checked against
`repos/flesh/lib/sbin/RunTestUtils.pl` and the checkout.

Verification is a snapshot, not a guarantee. Anything here can go stale as the tree
moves; when this disagrees with the source, the source wins, and the fix is to update
the file.

## License

GNU Library General Public License, version 2 — the same license as the Cactus Flesh.
See [COPYING](COPYING).
