# schedule.ccl, storage, and presync

Grammar: `repos/flesh/src/piraha/pegs/schedule.peg`. Parser: `lib/sbin/ScheduleParser.pl`
(also the home of the authoritative bin list) and, independently, `lib/sbin/rdwr.pl`.

---

## Syntax

```
schedule [GROUP] <name> [AT <bin> | IN <group>] [AS <alias>] [WHILE <var>] [IF <var>]
         [BEFORE|AFTER <item> | (<item> <item> ...)]
{
  LANG:        C | FORTRAN
  OPTIONS:     <opt>[,...]
  TAGS:        <key=value>[,...]
  STORAGE:     <group>[[timelevels]][,...]
  READS:       <group-or-var>[(region)][,...]
  WRITES:      <group-or-var>[(region)][,...]
  INVALIDATES: <group-or-var>[,...]
  SYNC:        <group>[,...]
  TRIGGERS:    <group>[,...]
} "description"
```

- `LANG: C` covers C++ too (`extern "C"` linkage).
- **`AT`/`IN` are both optional.** A bare `schedule GROUP Foo { } "..."` declares a group
  with no location, to be populated `IN Foo` by other thorns (this is how
  `CactusBase/Boundary`'s `ApplyBCs` group works).
- Top-level `STORAGE: group[,...]` outside any block toggles storage for the whole run,
  independent of file position.
- `STORAGE:` timelevels may be a literal or an **unqualified, thorn-local** integer
  parameter name (`0` deactivates). `thorn::param` is *not* allowed here (unlike
  `param.ccl`'s `ACCUMULATOR-BASE`).
- `OPTIONS`: `meta[-early|-late]`, `global[-early|-late]`, `level`, `singlemap`, `local`
  (default), plus at most one of `loop_meta|loop_global|loop_level|loop_singlemap|loop_local`.
- Conditionals wrap whole statements: `if (CCTK_Equals(param,"value")) { ... }`, and
  **`else` / `else if` chains are legal** even though the main chapter only shows a bare
  `if` (real 4-way chain: `repos/cactusbase/Time/schedule.ccl`). In upstream Cactus this
  form cannot appear *inside* a `SCHEDULE {...}` body around individual clauses.
- `INVALIDATES:` is grammar-valid and undocumented; essentially unused.

---

## Schedule bins, in execution order

Authoritative source: `CCTK_SchedulePrint()` in `repos/flesh/src/main/ScheduleInterface.c`
— the same structure `cactus_<cfg> -S` (`--print-schedule`) prints for a real
configuration. Run that on your own build rather than trusting any flat list.

```
if (recover initial data)
  Recover parameters                 [CCTK_RECOVER_PARAMETERS]
endif

[CCTK_STARTUP]                       startup routines (no grid hierarchy yet)
[CCTK_WRAGH]                         startup routines that need a grid hierarchy
[CCTK_PARAMCHECK]

if (NOT (recovering AND recovery_mode == 'strict'))
  [CCTK_PREREGRIDINITIAL]
  ...set up grid hierarchy...
  [CCTK_POSTREGRIDINITIAL]
  [CCTK_BASEGRID]
  [CCTK_INITIAL]
  [CCTK_POSTINITIAL]
  ...initialise finer grids recursively, restrict from finer grids...
  [CCTK_POSTRESTRICTINITIAL]
  [CCTK_POSTPOSTINITIAL]
  [CCTK_POSTSTEP]
endif
if (recover initial data)
  [CCTK_BASEGRID]
  [CCTK_RECOVER_VARIABLES]
  [CCTK_POST_RECOVER_VARIABLES]
endif
if (checkpoint initial data)  [CCTK_CPINITIAL]   endif
if (analysis)                 [CCTK_ANALYSIS]    endif
...output grid variables...

do loop over timesteps
  [CCTK_PREREGRID]
  ...change grid hierarchy...
  [CCTK_POSTREGRID]
  ...rotate timelevels; iteration += 1; t += dt...
  [CCTK_PRESTEP]
  [CCTK_EVOL]
  ...evolve finer grids recursively, restrict from finer grids...
  [CCTK_POSTRESTRICT]
  [CCTK_POSTSTEP]
  if (checkpoint)  [CCTK_CHECKPOINT]  endif
  if (analysis)    [CCTK_ANALYSIS]    endif
  ...output grid variables...
enddo

[CCTK_TERMINATE]
[CCTK_SHUTDOWN]

[CCTK_POSTREGRID]                    also run after any grid-hierarchy change
```

Note what a flat list hides: `BASEGRID` and `POSTSTEP` each appear in **two** places,
`ANALYSIS` in three, `POSTREGRID` runs after *every* regrid, and the recovery path is a
genuine branch, not a later phase.

The set of **valid** bin names (as opposed to their order) is `@schedule_bins` in
`lib/sbin/ScheduleParser.pl`; its array order is a grouping convenience and does **not**
match execution order. `MaintGuide/Schedule.tex` is an empty stub — do not look there.

Special cases:

- `CCTK_STARTUP`, `CCTK_SHUTDOWN`, `CCTK_RECOVER_PARAMETERS` take **no** `CCTK_ARGUMENTS`
  (signature `int fn(void)`). No grid hierarchy exists. `CreateScheduleBindings.pl`
  special-cases them.
- `CCTK_RECOVER_PARAMETERS` is declared as a group in the flesh's own
  `repos/flesh/src/schedule.ccl` and runs before everything else, only when recovering.
  It ignores `BEFORE`/`AFTER`/`WHILE`/`IF` and runs routines alphabetically by thorn
  until one returns positive.
- In `CCTK_ANALYSIS` only: if two routines trigger on the same variable, the first
  scheduled one runs and the second is skipped. By design.

---

## READS / WRITES regions

Real, complete set (grammar + Appendix):

```
EVERYWHERE | ALL | INTERIOR | IN | INTERIORWITHBOUNDARY | BOUNDARY | scalar
```

Defaults: **`EVERYWHERE` for READS, `INTERIOR` for WRITES.** The main UsersGuide chapter
lists only three of these and no defaults.

What these clauses actually *do* at runtime depends entirely on `Cactus::presync_mode`
— from nothing at all up to nulling grid-function data pointers.

### Two independent consumers of READS/WRITES

1. `lib/sbin/CreateScheduleBindings.pl` (`ScheduleSelectRDWR`/`SelectGroups`/
   `SelectRoutines`/`SelectVars`) → the auto-sync / auto-boundary machinery.
2. `lib/sbin/rdwr.pl` (`do_schedules`/`create_macros`) → the per-function
   `bindings/include/<Thorn>/cctk_Arguments_Checked.h` macros.

They walk the same parse tree separately. If you ever touch the schedule grammar or
parsing, both must be updated; `rdwr.pl` is keyed by function name and unions clauses
across every scheduling of that name.

---

## `presync_mode` — the five values

Declared in the flesh at `repos/flesh/src/param.ccl` (`STEERABLE = RECOVER`,
**default `off`**): `off | warn-only | mixed-warn | mixed-error | presync-only`.

### Flesh layer (`src/main/RDWR.cc`)

| mode | RDWR lists built? | duplicate clause for a var | invalid var/group name | nulls undeclared vars' pointers? |
|---|---|---|---|---|
| `off` | **no** (early return) | — | — | no |
| `warn-only` | yes | warn | warn | no |
| `mixed-warn` | yes | **abort** | warn | no |
| `mixed-error` | yes | **abort** | **fatal** | no |
| `presync-only` | yes | **abort** | **fatal** | **yes** |

- `off` is total: READS/WRITES become inert metadata; the lists are never constructed.
- Note the name trap: **`mixed-warn` aborts** on a duplicate clause. Only `warn-only`
  downgrades that check. The *invalid-name* check is the one that treats both
  `warn-only` and `mixed-warn` as warnings.

### Driver layer — old Carpet (the only driver implementing all five)

| mode | tracks validity | auto-sync from READS | honors explicit `SYNC:` | reading invalid data |
|---|---|---|---|---|
| `off` | no | no | yes | — |
| `warn-only` | yes | **no** | yes | warn |
| `mixed-warn` | yes | yes | yes | warn |
| `mixed-error` | yes | yes | yes | **error** |
| `presync-only` | yes | yes | **ignored** | **error** |

"Mixed" means explicit `SYNC:` and READS/WRITES-driven auto-sync coexist.
`presync-only` drops explicit `SYNC:` entirely and derives all communication from the
clauses. `warn-only` is diagnosis-only — it tracks and complains but syncs nothing.

### Driver layer — CarpetX

Accepts **only `mixed-error` and `presync-only`**; anything else is a startup
`CCTK_ERROR`. Under `presync-only` it also auto-syncs groups whose ghosts a READS clause
needs, skips already-valid groups, and pre-syncs timelevel 0 during cycling.

---

## Access control vs. validity — the distinction that causes misdiagnosis

**Access** (is the pointer non-NULL?) — only under `presync-only`:

`CCTKi_VarDataPtrI` (`src/main/GroupsOnGH.c`), which every generated
`DECLARE_CCTK_ARGUMENTS_<fn>` macro calls, returns **NULL** when
`!CCTK_HasAccess(GH, vindex)`. `CCTK_HasAccess` (`src/main/RDWR.cc`) looks the variable
up in `CCTK_ScheduleQueryCurrentFunction(cctkGH)->RDWR` — the RDWR list of the
*registration currently executing*. But it short-circuits to `true` in a non-`CCTK_DEBUG`
build unless `presync_mode` is exactly `"presync-only"`:

```c
static bool presync_only = CCTK_Equals(presync_mode, "presync-only");
#ifndef CCTK_DEBUG
  if (!presync_only) return true;
#endif
```

Vector groups are all-or-nothing: access to any member grants the whole vector.

**Validity** (does the data mean anything?) — enforced from `mixed-error` up by the
driver. CarpetX requires a `READS:` target to have been validly written by some earlier
routine (`Grid function "X" is invalid ...; required:`), and requires a
`WRITES: g(everywhere)` clause to actually be written everywhere — writing only the
interior (e.g. `loop_int_device`) against an `(everywhere)` clause trips
`contains ... nans ... expected valid` on the boundary/ghost region.

Because CarpetX's error message names `mixed-error` first, it is easy to land in a mode
where undeclared access silently works and conclude the driver "doesn't do this".
Old Cactus4/PUGH has neither check.

---

## Value-level checking: poison and checksums (CarpetX)

A third axis on top of access and validity: are the *bits* meaningful? CarpetX fills
undefined grid points with a poison pattern and scans for it.

One parameter controls the whole apparatus:

**`CarpetX::poison_undefined_values`** — `BOOLEAN`, `STEERABLE=always`, **default `yes`**
(`CarpetX/param.ccl:9`). There is no `CCTK_DEBUG` requirement and no second guard at any
call site, so this machinery **is active in an ordinary optimized build**.

| Gate site | What it turns off |
|---|---|
| `valid.cxx:160,218` | the poisoning itself (`set_to_poison`) |
| `valid.cxx:273` | `check_valid_gf` |
| `valid.cxx:482` | the same check for `CCTK_ARRAY` / `CCTK_SCALAR` |
| `valid.cxx:571,644` | `calculate_checksums` / `check_checksums` |
| `schedule.cxx:2059` | poisoning output variables that are not also inputs, before each routine |
| `schedule.cxx:2121,2169` | checksum before each routine, verify after |
| `driver.cxx:1947` | poisoning at setup |
| `io_openpmd.cxx:1017,1034,1225` | poison handling in openPMD I/O |

### `check_valid_gf` is a sweep, not per-access instrumentation

It does **not** add a check to each memory access; user kernels compile identically
whether it is on or off. For one (group, variable, timelevel) it launches a separate
read-only `grid.loop_device_idx` over the valid region, compares each point's bit
pattern against a fixed poison value (`0xfff8000000000000 + 0xdeadbeef`, a NaN payload —
`valid.hxx:248`), and on a hit does `#pragma omp atomic write` of NaN into a 1-element
flag `FArrayBox`.

What makes it expensive is frequency, not per-point cost: `schedule.cxx` calls it once
per `READS` clause before each scheduled routine ("checking input", `:2021`) and once per
`WRITES` clause after ("checking output", `:2205`), plus at `INVALIDATES`, sync, restrict,
regrid and timelevel cycling — 12 sites in `schedule.cxx`, 5 in `driver.cxx`, 1 in
`ODESolvers/src/solve.cxx`. Cost model: **one extra full-array pass per grid function per
clause per scheduled routine.**

> `check_valid_gf` currently ignores its own argument. The parameter is `nan_handling1`,
> but a local `constexpr nan_handling_t nan_handling = forbid_nans` shadows it under a
> `#warning "TODO"` (`valid.cxx:268-283`). The callers' choice between
> `do_checkpoint ? forbid_nans : allow_nans` (e.g. `schedule.cxx:2006-2008`) is
> therefore dead code.

### The checksum pair is a different check

`calculate_checksums` (`valid.cxx:565`) runs before each scheduled routine over every
group/variable/timelevel, checksumming the regions the routine declared it would **not**
write; `check_checksums` re-verifies afterwards. This is what catches "you declared
`WRITES: g(interior)` but also clobbered the boundary."

It is narrower than it first looks — the guard is
`if (!(wr.valid_any() && to_check.valid_any())) continue`, so variables the routine does
not write *at all* are skipped, and only partially-written variables are checksummed.

> Note the checksum loops use `grid.loop_idx` (**host**), while `check_valid_gf` uses
> `grid.loop_device_idx` (device). On a GPU build the checksum path therefore reads grid
> data from the host — migration traffic, not a device sweep. If poison overhead looks
> larger than a device-side NaN scan should cost, look here first.

### Steering is asymmetric

Turning it **off** mid-run is fine. Turning it **on** mid-run gives false confidence:
data allocated and written earlier was never poisoned, so `check_valid_gf` finds nothing
and silently passes. For benchmarking or bisecting, set it in the parfile from the start.

### What stays on regardless

`error_if_invalid` (`valid.cxx:101`) — the `Grid function "X" is invalid ...; required:`
error — has **no gate at all**. It is pure metadata comparison against the `valid_t`
bookkeeping. So `poison_undefined_values = no` disables *value-level* checking (are these
bits poison?) but not *state-level* checking (was this variable validly written before
being read?). You keep the cheap correctness net and drop the expensive one.

---

## STORAGE traps

- **CarpetX ignores runtime `STORAGE:` toggling entirely.** `GroupStorageIncrease`/
  `Decrease` is a stub in `repos/CarpetX/CarpetX/src/schedule.cxx` (`GroupStorageCrease`,
  commented `// TODO: actually do something`): it returns a status and allocates nothing.
  Every declared group has full storage from the start. Do not port a PUGH-era
  "toggle storage to make a group unavailable" trick to CarpetX, and do not read a
  non-null pointer there as proof that storage toggling worked.
- Several common `EinsteinBase` groups have **no storage by default**:
  `ADMBase::shift`/`dtlapse`/`dtshift` (gated on `initial_shift`/`initial_dtlapse`/
  `initial_dtshift != "none"`) and `HydroBase::Bvec` etc. (gated on
  `initial_Bvec != "none"`). Touch one without setting the relevant parameter in the
  parfile and its pointer is silently NULL, regardless of READS/WRITES.
- You cannot sync individual group members or non-current timelevels — only a whole
  group's current timelevel.
- **Declared timelevels and active timelevels are different numbers.**
  `CCTK_DeclaredTimeLevelsGI` is the `TIMELEVELS=` maximum from `interface.ccl`;
  `CCTK_ActiveTimeLevelsGI`/`VI` is how many currently have storage. `STORAGE: group[n]`
  sets the latter, and so does `CCTK_GroupStorageIncrease`/`Decrease` at runtime — which
  is a real, supported way to size a group from a thorn, under any driver except CarpetX
  (above). Everything that scales with timelevel count, including the driver's rotation,
  keys off the *active* number.
- **Storage requested inside a scheduled block is scoped to that block**, so a group can
  exist for part of an evolution step and not the rest. `MoL::ScratchSpace` is the
  canonical case: `MoL_AllocateScratchSpace` runs in `MoL_StartStep` and
  `MoL_FreeScratchSpace` at the end of `MoL_Evolution`
  (`arrangements/CactusNumerical/MoL/schedule.ccl`), so MoL scratch **does not survive a
  timestep** and cannot carry state from one step to the next. That same lifetime is
  what makes MoL's trick of indexing scratch by *timelevel* safe — see the rotation note
  in [thorn-anatomy.md](thorn-anatomy.md#grid-variables-in-code).
- A parameter used in a `schedule.ccl` `if (...)` must be one the thorn can see: its own,
  or another thorn's via `shares:` + `USES` in `param.ccl`. Otherwise the generated
  `bindings/Schedule/Schedule<Thorn>.c` fails to compile with `'<param>' undeclared`.

---

## Iterating fast on schedule/grammar changes

Three levels, cheapest first (no full build needed for the first two):

1. **Grammar only.** From Perl: `piraha::parse_peg_file($peg)` then
   `piraha::parse_src($grammar, $rule, $ccl_file)` (see `lib/sbin/Piraha.pm`) against a
   scratch `.ccl` snippet. `$m->matches()`, `$m->showError()`, `$m->{gr}->dump()`.
2. **Parser logic, no compile.** Call `create_schedule_database(%thorns)` from
   `ScheduleParser.pl` directly. Two constraints: the calling script must live in (or be
   run from) `repos/flesh/lib/sbin/` (the `.peg` path is resolved via `$FindBin::Bin`),
   and each `%thorns` value must be a path with **at least two components** before
   `schedule.ccl` (any `.../SomeArr/SomeThorn/` scratch dir works).
3. **Real build + run, fast.** A minimal PUGH executable (no MPI/HDF5/AMReX) builds in
   under a minute:
   ```
   CactusPUGH/PUGH
   CactusBase/{CoordBase,CartGrid3D,SymBase,Boundary,IOUtil,IOBasic,InitBase}
   <your test thorn>
   ```
   then `gmake <newcfg>-config THORNLIST=<path> options=<existing plain optionlist> PROMPT=no`
   and `gmake <newcfg>-delete PROMPT=no` to clean up.

> **PEG authoring rule.** Whitespace-skip insertion is driven purely by literal
> whitespace in the rule's own source text. Always write `( A | B | C )*`, never
> `(A|B|C)*` — the compact form silently drops the skip before every non-first
> alternative, and only fails when two *different* alternatives match back-to-back.
