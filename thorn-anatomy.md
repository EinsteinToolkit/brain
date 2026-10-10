# Thorn anatomy — the CCL files

The grammars at `repos/flesh/src/piraha/pegs/{interface,param,schedule,config}.peg` are
ground truth. The prose docs are incomplete in several places noted below.

For everything about `schedule.ccl` see [schedule-and-presync.md](schedule-and-presync.md).

---

## `interface.ccl`

```
implements: <name>
inherits:   <impl> [<impl> ...]      # space- or comma-separated; transitive
friend:     <impl> [...]             # transitive
```

`implements:` names an **implementation**, not the thorn. Several thorns may implement
the same one (only one may be active at a time). `inherits:` is what gives you read
access to another implementation's public variables — **a missing `inherits:` is the
usual cause of undefined-reference / link-order errors.**

Variable access levels are bare lines, not per-declaration: **`public:` / `protected:` /
`private:`** (default private). This vocabulary differs from `param.ccl`'s.

### Group declaration

```
<data_type> <group_name>[[<vector_size>]] [TYPE=SCALAR|GF|ARRAY] [DIM=n]
  [TIMELEVELS=n] [SIZE=...] [DISTRIB=DEFAULT|CONSTANT] [GHOSTSIZE=...]
  [TAGS='k=v ...'] [STAGGER=...] [CENTERING={...}]
{ var1, var2 } "description"
```

- Types: `CHAR BYTE INT REAL COMPLEX`, optional width suffix (`CCTK_INT1/2/4/8`,
  `CCTK_REAL4/8/16`, `CCTK_COMPLEX8/16/32`). `CCTK_` prefix optional, case-insensitive.
- Defaults: `TYPE=SCALAR`, `DIM=3`, 1 timelevel.
- Group types: `SCALAR` (never communicated), `GF` (grid function — driver-uniform size
  and ghostzones), `ARRAY` (own `SIZE`/`GHOSTSIZE`/`DISTRIB`).
- `TAGS='...'` is a free-form key/value string parsed by `Util_TableSetFromString`; the
  CST does not interpret it. Real driver-specific keys: `tensortypealias`,
  `tensorweight`, `Prolongation`, `checkpoint="no"`.
- `STAGGER=` / `CENTERING={VVV}` are real grammar productions used by CarpetX /
  multipatch thorns, and are **documented nowhere**.
- There is no `STRING` grid-scalar type — use a `CCTK_CHAR` array with `DISTRIB=CONSTANT`.

> **In Carpet a `SCALAR` or `ARRAY` group exists once per grid hierarchy, not once per
> refinement level.** `arrdata` is indexed `[group][map]`
> (`repos/carpet/Carpet/src/variables.hh`), and `Cycle.cc` advances scalars and arrays
> with a hard-coded reflevel `0` while grid functions get the current `reflevel`. So a
> grid scalar **cannot hold per-refinement-level state across iterations** — a finer
> level will overwrite what a coarser one left. It works only while one level's
> traversal owns it start to finish, which is how `MoL`'s substep counter
> (`MoL::MoL_Intermediate_Step`, an `OPTIONS: LEVEL` scalar) gets away with it.
> State that must persist per level between iterations needs your own storage keyed on
> the aliased `GetRefinementLevel(cctkGH)`.

### Includes

```
USES INCLUDE [SOURCE|HEADER]: <file>
INCLUDE[S]  [SOURCE|HEADER]: <file> in <file>
```

### Aliased functions (declared here, not in a separate file)

```
<ret> FUNCTION <alias>(<type> <IN|OUT|INOUT> [ARRAY] <arg>, ...)
REQUIRES FUNCTION <alias>    # caller, hard dependency, checked at startup
USES     FUNCTION <alias>    # caller, optional
PROVIDES FUNCTION <alias> WITH <impl_fn> LANGUAGE C|Fortran
```

- `SUBROUTINE` == `void FUNCTION`.
- Return types allowed:
  `void CCTK_INT CCTK_REAL CCTK_COMPLEX CCTK_POINTER CCTK_POINTER_TO_CONST`.
  Arguments may additionally be `STRING`; function-pointer arguments use
  `CCTK_FPOINTER` (no nesting).
- With `USES FUNCTION` you **must** guard the call with
  `CCTK_IsFunctionAliased("<alias>")` — calling an unregistered aliased function aborts.
- A provider commonly also `USES FUNCTION` its own alias so it can call it generically.

---

## `param.ccl`

Access levels: **`global:` / `restricted:` / `private:`** (default private).

```
shares: <implementation>
USES    <TYPE> <param>            # keep range, no default allowed
EXTENDS <TYPE> <param> { ... }    # add allowed values, no default allowed
```

Types: `INT REAL KEYWORD STRING BOOLEAN`. Ranges: `lower:upper:stride` with `(`/`)`/`[`/`]`
for open/closed and `*` for infinity (INT/REAL); quoted list or regex (KEYWORD/STRING);
none (BOOLEAN).

Per-parameter modifiers on the declaration line:

- `AS <alias>`
- `STEERABLE=NEVER|ALWAYS|RECOVER` — **only these three spellings.** The docs' prose says
  `RECOVERY`; that is a fatal build error.
- `ACCUMULATOR=<expr in x,y>` and `ACCUMULATOR-BASE=<param>` (may be fully qualified
  `thorn::param`). Canonical pair: `MoL::MoL_Num_Evolved_Vars` fed by
  `ML_BSSN`'s `ACCUMULATOR-BASE=MethodofLines::MoL_Num_Evolved_Vars`.

Only **`restricted:`** and **`global:`** parameters can be shared. `USES`/`EXTENDS` of
another thorn's `private:` parameter is a CST error —
`Thorn "X" attempted to EXTEND or USE non-restricted parameter "P" from implementation "I"`
(`lib/sbin/ImpParamConsistency.pl`); the bindings bear this out, exposing only
`ParameterCRestricted<IMPL>.h` and the global struct to consumers. If you need a thorn
to react to someone else's `private:` parameter, that parameter has to move to
`restricted:` in its own thorn. Doing so is source-compatible: the parameter keeps its
`Thorn::name` spelling and existing parfiles are unaffected.

Array-parameter sizes must be compile-time integer literals, not other parameters
(Fortran needs fixed-size arrays).

---

## `configuration.ccl` (optional — only if you need an external capability)

```
PROVIDES <Capability> { SCRIPT <script> [VERSION <ver>] LANG <lang> [OPTIONS <opt>,...] }
REQUIRES <Capability> [(<op><version>)]        # op ∈ << <= = >= >>
REQUIRES THORNS: <Arr/Thorn> ...
OPTIONAL <Capability> { DEFINE <macro> }
```

`VERSION` and `OPTIONS` are real and pervasive despite the main chapter showing only
`SCRIPT`/`LANG`. Output vocabulary a config script may emit: `BEGIN/END DEFINE`,
`INCLUDE_DIRECTORY`, `BEGIN/END MAKE_DEFINITION`, `BEGIN/END MAKE_DEPENDENCY`,
`LIBRARY`, `LIBRARY_DIRECTORY`. See [external-libraries.md](external-libraries.md).

This file is also the *only* way to force thorn-level build ordering. File-level
ordering goes in `src/make.code.deps` (`using.F90.o: module.F90.o` — note the `.o`).

---

## Grid variables in code

Timelevels rotate each step: current level has no suffix, previous are `_p`, `_p_p`, …

> **The rotation is the driver's, and it is unconditional.** Carpet's `CycleTimeLevels`
> (`repos/carpet/Carpet/src/Cycle.cc`) rotates *every* group that has storage and more
> than one **active** timelevel, once per iteration. There is no tag, parameter or
> group attribute to opt out — `Prolongation="None"` and `Checkpoint="no"` do not
> exempt a group. Consequence: a group's timelevels can only be repurposed as a
> general-purpose index (rather than as history) if the group has **no storage at the
> moment the driver cycles**. That is exactly the condition `MoL::ScratchSpace`
> satisfies — see the storage-lifetime note in
> [schedule-and-presync.md](schedule-and-presync.md#storage-traps).

C data is laid out Fortran-style (first index fastest). Index with
`CCTK_GFINDEX3D(cctkGH,i,j,k)` (also 1D/2D/4D, and `CCTK_VECTGFINDEX*D(...,n)`), or use
the loop macros from `repos/flesh/src/include/cctk_Loop.h`:

```c
CCTK_LOOP3_ALL(name, cctkGH, i,j,k) {
  ...
} CCTK_ENDLOOP3_ALL(name);
```

Variants: `CCTK_LOOP{1,2,3}_{ALL,INT,BND,INTBND}`. Typically wrapped in
`#pragma omp parallel`. In Fortran a grid function is just `rho(i,j,k)`.

> **Vector groups expose ONE pointer.** A declaration like
> `CCTK_REAL Bvec[3] TYPE=GF { Bvec[0], Bvec[1], Bvec[2] }`, referenced by group name in
> `schedule.ccl`, yields a single `CCTK_REAL *const Bvec` (the 0th/representative
> component) — **not** an array of three pointers. The `Bvec[1]` syntax exists in
> `interface.ccl` and in `READS`/`WRITES` clauses for naming a component; it does not
> give you a pointer array in C.

---

## `CCTK_ARGUMENTS` and parameters in a routine

```c
#include "cctk.h"
#include "cctk_Arguments.h"
#include "cctk_Parameters.h"

void MyThorn_Routine(CCTK_ARGUMENTS) {
  DECLARE_CCTK_ARGUMENTS_CHECKED(MyThorn_Routine);   /* or DECLARE_CCTK_ARGUMENTS */
  DECLARE_CCTK_PARAMETERS;
  ...
}
```

- `DECLARE_CCTK_ARGUMENTS` declares **all** thorn-visible variables;
  `DECLARE_CCTK_ARGUMENTS_CHECKED(fn)` declares only those named in that routine's
  `READS`/`WRITES`, as `const`/`intent(in)` where appropriate. It literally expands to
  the CST-generated macro `DECLARE_CCTK_ARGUMENTS_<fn>` (`lib/sbin/rdwr.pl`), which
  thorns may also invoke directly.
- The `_CHECKED` macro is keyed purely by **function name** and accumulates the union of
  clauses from *every* place that name is scheduled in the thorn.
- Declaration order matters: arguments macro first, then parameters.
- Standard `CCTK_ARGUMENTS` fields: `cctkGH`, `cctk_dim`, `cctk_lsh`, `cctk_ash`,
  `cctk_gsh`, `cctk_iteration`, `cctk_delta_time`, `cctk_time`, `cctk_delta_space`,
  `cctk_nghostzones`, `cctk_origin_space`.
- Parameters are **read-only local copies**. `CCTK_ParameterSet` does not change the
  value already seen by the calling routine.
- KEYWORD/STRING parameters are opaque C string pointers in Fortran — use
  `CCTK_Equals` / `CCTK_FortranString`, never Fortran string operations. BOOLEAN
  parameters are not Fortran `LOGICAL`.
- **No grid variables exist at `CCTK_STARTUP` / `CCTK_SHUTDOWN` / `CCTK_RECOVER_PARAMETERS`.**
  Those routines are `int fn(void)` — declaring them `CCTK_ARGUMENTS` segfaults right
  after the schedule tree prints.
- Same-thorn C→C / F→F calls: pass `CCTK_PASS_CTOC` / `CCTK_PASS_FTOF` and repeat
  `CCTK_ARGUMENTS` in the callee.

---

## Driver / infrastructure thorns

A driver is a thorn that `implements: Driver`. What it must register and
overload, and how PUGH, Carpet, and CarpetX differ: [driver.md](driver.md).

I/O methods self-register via `CCTK_RegisterIOMethod` plus
`...OutputGH/TimeToOutput/TriggerOutput/OutputVarAs`. Checkpoint hooks write at
`CCTK_CPINITIAL`/`CCTK_CHECKPOINT`/`CCTK_TERMINATE` and read at
`CCTK_RECOVER_PARAMETERS`/`CCTK_RECOVER_VARIABLES`.

---

## Workflow: adding or modifying a thorn

1. `gmake newthorn`, or create the directory under an arrangement.
2. Declare **every** grid variable/group you touch (own or inherited) in
   `interface.ccl`; every parameter you read in `param.ccl` (own, or `shares:` +
   `USES`/`EXTENDS`).
3. Schedule with the narrowest `STORAGE`/`READS`/`WRITES`/`SYNC` that is correct.
4. Write the routine (includes and declaration order as above).
5. List sources in `src/make.code.defn` (`SRCS = ...`, `SUBDIRS = ...`) unless you supply
   a custom `src/Makefile`.
6. Add the thorn to the configuration's `ThornList` and to the parfile's `ActiveThorns`.
7. Any CCL change requires a CST rerun — see [build-system.md](build-system.md).

### Gotchas that cost hours

- `#if 0 ... #endif` around a block containing `DECLARE_CCTK_ARGUMENTS`/`_PARAMETERS`
  breaks the CST's automatic closing-brace insertion. Keep commented-out code in
  matched `{}`.
- A missing `DECLARE_CCTK_PARAMETERS` **in Fortran** gives silently wrong parameter
  values with no compile error.
- F77 and F90 sources must use the same compiler (name mangling / calling convention).
- No C++ `//` comments in C thorn code (portability convention).
- Fortran calls to macros (`CCTK_EQUALS`, `CCTK_INFO`, `CCTK_WARN`) need C-style
  backslash continuation, not Fortran `&`/column-6 — they are preprocessor macros.
- Prefer `CCTK_IsThornActive(...)` over `#ifdef ARRANGEMENT_THORN`.
