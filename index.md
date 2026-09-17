# Cactus / Einstein Toolkit — Brain

Entry point for an AI working on this codebase. **Read this file, then load
exactly one topic file** from the routing table. Files are deliberately small and
non-overlapping; do not load them all.

---

## The 30-second model

Cactus is **flesh + thorns**.

- **Flesh** (`repos/flesh`, symlinked as `src/`, `lib/`, `Makefile`, `doc/`) is a small
  core: parameter parsing, scheduling, grid-variable bookkeeping, and the
  driver/IO/reduction/interpolation *interfaces*. It computes nothing physical.
- **Thorns** are the application code. A thorn lives in an **arrangement** and is
  always addressed `Arrangement/Thorn` (e.g. `CactusBase/CartGrid3D`) — in ThornLists,
  in `ActiveThorns`, everywhere.
- A thorn declares itself in four **CCL** files (`interface.ccl`, `param.ccl`,
  `schedule.ccl`, optional `configuration.ccl`). The **CST** reads those plus the
  ThornList and *generates all the glue* (bindings) that makes the thorn exist.
- A **driver** thorn (PUGH, Carpet, CarpetX) actually owns the grid, storage,
  ghost-zone communication and AMR. The flesh only defines the overload points.
- A **configuration** is one build: `configs/<name>/`, its own optionlist, thorn
  selection, bindings, objects and `exe/cactus_<name>`.
- The **Einstein Toolkit (ET)** is a curated set of arrangements/thorns for numerical
  relativity on top of the flesh, plus its own tooling (GetComponents, SimFactory) that
  the flesh's own UsersGuide does *not* document.

Pipeline:

```
GetComponents (CRL .th)  →  repos/* clones, symlinked into arrangements/
        ↓
gmake <cfg>-config  (optionlist → autoconf; ThornList + CCL → CST → bindings)
        ↓
gmake <cfg>         (libthorn_<Thorn>.a per thorn, then link)
        ↓
exe/cactus_<cfg> <parfile>     (usually launched via simfactory)
```

---

## Routing table

| Your task | Load |
|---|---|
| Find where something lives; understand `repos/` vs `arrangements/` vs `configs/` | [layout.md](layout.md) |
| Write or modify a thorn; CCL syntax; grid variables; aliased functions | [thorn-anatomy.md](thorn-anatomy.md) |
| Schedule bins, `READS`/`WRITES`, `SYNC`, `STORAGE`, `presync_mode`, poison/validity checking | [schedule-and-presync.md](schedule-and-presync.md) |
| Call `CCTK_*` / `Util_*` from thorn code; find the right header | [cctk-api.md](cctk-api.md) |
| Configure/compile; make targets; optionlists; CST; clean-vs-delete | [build-system.md](build-system.md) |
| HDF5 / AMReX / MPI / CUDA / HIP dependencies; `detect.sh` vs `build.sh` | [external-libraries.md](external-libraries.md) |
| `sim build` / `create-run` / `submit`; machine `.ini`; MDB; testsuite | [simfactory.md](simfactory.md) |
| Something is broken — symptom → cause → fix | [troubleshooting.md](troubleshooting.md) |
| A run is slower than the physics warrants (debug checks, GPU startup cost) | [troubleshooting.md](troubleshooting.md) → *Performance* |
| The shipped LaTeX docs disagree with the source | [doc-traps.md](doc-traps.md) |

---

## Ground-truth ranking

When two things disagree, believe them in this order:

1. **Source** — `repos/flesh/src/`, `repos/flesh/lib/sbin/`, the thorn itself.
2. **PEG grammars** — `repos/flesh/src/piraha/pegs/{interface,param,schedule,config,par}.peg`.
   These *are* the CCL language definition; the prose docs are a lossy summary.
3. **This brain.**
4. **`repos/flesh/doc/*` (UsersGuide / ReferenceManual / MaintGuide / FAQ).** Large parts
   are stale, several MaintGuide chapters are empty stubs, and ~50 API signatures are
   wrong. See [doc-traps.md](doc-traps.md) before trusting an edge case from them.

---

## Rules that prevent real damage

- **Never** `rm -rf simfactory/mdb/*`, an arrangement tree, or `repos/*` to clear a
  compile error. Use `gmake <cfg>-delete` or reconfigure.
- **Never** hand-write `simfactory/etc/defs.local.ini` — it must come from
  `sim setup-silent`.
- Before renaming a `public`/`protected` group, a `restricted`/`global` parameter, or an
  aliased-function signature: **grep the whole checkout**. CCL gives almost no
  cross-thorn compile-time checking; other thorns break silently.
- Changing an optionlist file does **not** affect an already-configured
  `configs/<cfg>/`. You must reconfigure.
- `arrangements/*/*` are **symlinks** into `repos/*`. Editing a file there edits the
  real git checkout. Check `git -C repos/<x> status` before and after.
- A green build does **not** mean the GPU backend initialized, that the right MPI was
  used, or that the right CPU arch was targeted. Verify at runtime.

---

## Glossary

| Term | Meaning |
|---|---|
| **CCTK** | Cactus Computational Toolkit — the flesh's API (`CCTK_*`) |
| **CCL** | Cactus Configuration Language — the four `*.ccl` thorn declaration files |
| **CST** | Cactus Specification Tool (`lib/sbin/CST`) — parses CCL + ThornList, generates bindings |
| **Thorn** | One compile unit / module |
| **Arrangement** | Directory grouping thorns; first half of `Arrangement/Thorn` |
| **Implementation** | The *interface* name a thorn `implements:`; several thorns may implement the same one |
| **Configuration** | A named build tree under `configs/` |
| **Driver** | The thorn that owns grid/storage/communication (PUGH, Carpet, CarpetX) |
| **Bindings** | CST-generated glue under `configs/<cfg>/bindings/` |
| **CRL** | Component Retrieval Language — GetComponents `.th` checkout files |
| **ThornList** | *Compile* list: plain `Arrangement/Thorn` lines. **Not** the same as a CRL file |
| **Capability** | `configuration.ccl` `PROVIDES`/`REQUIRES` name; a build-dependency graph node, not a path |
| **USESTHORNS** | Make variable: thorns whose include/lib flags feed this thorn's compile |
| **SCRATCH_BUILD** | `configs/<cfg>/scratch` — external library builds and intermediates |
| **PreSync** | The `READS`/`WRITES`-driven automatic sync machinery, gated by `presync_mode` |
| **GF / ARRAY / SCALAR** | Grid-variable group types (grid function / distributed array / non-communicated scalar) |

---

## Maintaining this brain

Distilled from `~/workenv/etc/cactus-docs.md` and `~/workenv/etc/cactus-build-ref.md`
(one-time source audits), re-verified against this checkout on 2026-09-17: flesh
`ET_2026_05` / `Cactus_4.20.0_v0`, clean working tree.

Rules for editing it:

- **One fact, one place.** If two files would say it, put it in the more specific one and
  link. The routing table is the only intentional duplication.
- **Cite a path, not a line number**, unless the line is genuinely stable. Line numbers
  rot; `grep`-able symbol names do not.
- Prefer "here is how to find out" over a snapshot of a list that will drift (e.g.
  `cactus_<cfg> -S` for the schedule tree, `@schedule_bins` for valid bin names).
- Anything that is true only of one machine, cluster, or configuration does **not**
  belong here. This describes Cactus, not a site.

`README.md` is the human-facing introduction to this directory; you do not need it.
Licensed LGPL v2, same as the Cactus Flesh — see [COPYING](COPYING).
