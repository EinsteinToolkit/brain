# Known documentation traps

`repos/flesh/doc/*` (UsersGuide, ReferenceManual, MaintGuide, FAQ, ReleaseNotes) ships
with the flesh and is the obvious thing to read. Large parts of it are wrong. This file
exists so you do not waste a debugging session trusting it.

**Verify any signature against `repos/flesh/src/include/*.h` before using it.**

---

## Structurally missing — not just wrong, absent

| Topic | Where it actually lives |
|---|---|
| How CCL files are parsed (Piraha PEG engine + `src/piraha/pegs/*.peg`) | Nowhere in the docs. `lib/sbin/Piraha.pm`, the `.peg` files |
| The CST's architecture | `MaintGuide/CST.tex` is an **empty stub**. Read `lib/sbin/CST` |
| The schedule-bin list and ordering | `MaintGuide/Schedule.tex` is an **empty stub**. `@schedule_bins` in `lib/sbin/ScheduleParser.pl` |
| The READS/WRITES (PreSync) auto-sync machinery | Nowhere. `CreateScheduleBindings.pl`, `rdwr.pl`, `src/main/RDWR.cc` |
| `presync_mode` semantics | Nowhere. `src/main/RDWR.cc`, `Carpet/src/PreSync.cc`, `CarpetX/src/schedule.cxx` |
| GetComponents / CRL `.th` files | ET tooling; not in the flesh UsersGuide at all |
| SimFactory | Same |
| `MaintGuide/{Comm,IO,Util}.tex` | Also empty stubs |

Also empty-ish or self-admittedly stale: `Procedures.tex` (its own line 14 says the
chapter is "out-dated and needs a rewrite"; still names BitBucket as the issue tracker).

---

## `CCTKReference.tex` — wrong API signatures

Grouped; all verified against the headers.

**Wrong constness / types**
- `CCTK_Abort` — doc `const cGH*`; real non-const `cGH *`.
- `CCTK_Enable/DisableGroupStorage`, `Enable/DisableGroupComm` and their `I` variants —
  doc uses non-const `cGH *` for 7 of the 8; real is `const cGH *`
  (`CCTK_DisableGroupStorageI` is the one it gets right).
- `CCTK_ArrayGroupSize[I]` — real return is `const int *`.
- `CCTK_ImpFromVarI` — real return is `const char *`.
- `CCTK_VarDataPtr` — 3rd argument is `const char *`.
- `Util_StrSep` — real return is `const char *`.
- `CCTK_FortranString` length parameter is `CCTK_FORTRAN_STRLEN_T` (can be 64-bit), not `int`.
- `CCTK_Warn` and `CCTK_RegisterBanner` return `int`, not `void`.
- `CCTK_NumTimerClocks` returns `unsigned int`.
- `CCTK_CmplxAbs` returns `CCTK_REAL`, not `CCTK_COMPLEX`.
- `CCTK_IsFunctionAliased` returns `CCTK_INT` with parameter named `function`.
- `CCTK_SetupGH` takes `tFleshConfig *config` (pointer), not by value.
- `CCTK_RegisterGHExtensionInitGH` callback is `int (*)(cGH*)`, not `void *(*)(cGH*)`.
- `CCTK_RegisterReductionOperator` is a 2-argument macro; the doc shows a 0-argument call.

**Functions that do not exist**
- `CCTK_GetClockName`, `CCTK_GetClockResolution`, `CCTK_GetClockSeconds` — use
  `CCTK_TimerClockName` / `CCTK_TimerClockResolution` / `CCTK_TimerClockSeconds`.
- `CCTK_PrintGroup` / `CCTK_PrintVar` are Fortran-linkage wrappers only; the doc's
  C example cannot link.
- `CCTK_InterpLocalWarped` and its registration function are `%notyet`-commented in the
  LaTeX source — not callable.

**Incomplete struct listings**
- `cGroup` omits `centeringtable`.
- `cGroupDynamicData` omits `alignment`, `alignment_offset`, `maxtimelevels` (14 real
  members vs 11 documented) — this matters for manual indexing/padding.

**Real but undocumented**
- `CCTK_InterpOperator`, `CCTK_InterpOperatorImplementation`, `CCTK_NumInterpOperators`.
- `CCTK_UnregisterGHExtension`.
- `Util_TableSet/GetPointerToConst` (+ Array variants); `INT16` is missing from the
  Set/Get type-family lists although `Util_TableSetInt16` etc. exist.
- `Util_SplitString`, `Util_SplitFilename`, `Util_StrMemCmpi`, `Util_asnprintf`.

**Ambiguity the doc does not flag**
- Two incompatible `CCTK_CoordRegisterSystem` macros exist (2-arg in `cctk_Coord.h`,
  3-arg in `cctk_core.h` expanding to a 4-arg call matching no prototype). The second
  looks like dead code.

**Copy-paste artifacts (cosmetic but misleading)** — `CCTK_NumCompiledThornss` in a code
sample; `CCTK_ThornImplementationThorn` in a synopsis; `CCTK_GetClockValueI`'s synopsis
missing its `I`; `CCTK_TimerCreateI`'s synopsis showing `CCTK_TimerCreate`;
`CCTK_TimerReset` and `CCTK_TimerStop` both described as "Gets values from all the
clocks"; `CCTK_GroupTagsTable`'s Fortran synopsis showing `CCTK_VarIndex`;
`CCTK_GroupStorageDecrease` with a duplicated parameter entry; `CCTK_GHExtension`'s
synopsis typing its argument `const GH *`; `CCTK_VERROR`/`CCTK_VWARN` Discussion text
misdescribing their own expansions.

---

## `DriverReference.tex`

Four of the six documented functions show `CCTK_*` names that do not exist. The real
names are `Driver_GetValidRegion`, `Driver_SetValidRegion`, `Driver_NotifyDataModified`,
`Driver_RequireValidData`, and all take `cctkGH` first. `Driver_SelectGroupForBC` /
`Driver_SelectVarForBC` have a literal syntax error (`int table handle,`) and a stray
`where_list` parameter. See [cctk-api.md](cctk-api.md).

---

## UsersGuide (`ApplicationThorns.tex` / `Appendices.tex`)

| Issue | Reality |
|---|---|
| `READS`/`WRITES` region list is incomplete in the main chapter (3 keywords, no defaults) | Real set: `EVERYWHERE ALL INTERIOR IN INTERIORWITHBOUNDARY BOUNDARY scalar`; defaults `EVERYWHERE` for READS, `INTERIOR` for WRITES. `scalar` is in neither location |
| `configuration.ccl` `PROVIDES {}` shown with only `SCRIPT`/`LANG` | `VERSION` and `OPTIONS` are real and pervasive (Appendix only) |
| `STEERABLE=RECOVERY` in prose | Parser accepts only `RECOVER`; `RECOVERY` is a fatal build error |
| `STAGGER=` / `CENTERING={...}` group attributes | Real grammar productions used by CarpetX/multipatch thorns; documented nowhere |
| `INVALIDATES:` | Grammar-valid, documented nowhere, essentially unused |
| Schedule conditionals shown only as a bare `if` | `else` / `else if` chains are legal and widely used |
| `InfrastructureThorns.tex` implies a driver overloads `Enable/DisableGroupStorage` | PUGH actually overloads `GroupStorageIncrease`/`Decrease` — a different overload point |
| `Appendices.tex` references `.emacs`/`grdoc` tooling | No `grdoc*` file ships in the repo |

---

## MaintGuide

| Claim | Reality |
|---|---|
| `Makesystem.tex` refers to `configure.in`, `config.h.in`, `config.h` | Real files are `configure.ac`, `cctk_Config.h.in`, `cctk_Config.h` |
| `Makesystem.tex` writes `CCTK_functions.sh` | Real filename is `CCTK_Functions.sh` (capital F) |
| `Style.tex` mandates opening braces on their own line | `repos/flesh/.clang-format` sets `BreakBeforeBraces: Attach`, and real code follows that. **Match the surrounding code, not the style guide** |
| `Style.tex` mandates a single return point | Violated by actively-maintained code (e.g. `Boundary.c`) |

---

## Wholesale stale

- **`ReleaseNotes` is dead.** Newest entry is 16 May 2014 (ET_2014_05_v0). The only
  substantive logged change is native C99/C++ complex support deprecating `CCTK_Cmplx*`.
- **`README.Windows` is fully obsolete** — Cygwin on WinXP/NT/2000, GNU make 3.77–3.81,
  MSVC 6.0. No modern-Windows guidance, and not flagged as outdated.
- **The FAQ** contains much that is still correct (most of
  [troubleshooting.md](troubleshooting.md) is distilled from it) mixed with entries tied
  to defunct compilers and OSes (old Intel/Absoft/Pacific-Sierra Fortran, SGI/Irix,
  RedHat 8/9 glibc bugs, MacOS Absoft F90). Nothing marks which is which.
- A few FAQ/Appendix entries point at ~20-year-old `cactuscode.org` URLs.
