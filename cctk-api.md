# CCTK API map

**Do not trust `doc/ReferenceManual/CCTKReference.tex` for a signature.** ~30 of its
entries are wrong. Read the header in `repos/flesh/src/include/`. This file tells you
*which* header, plus the traps.

---

## Header → contents

| Header | Contains |
|---|---|
| `cctk.h` | Umbrella; pulls in the rest. Always include first |
| `cctk_core.h` | `CCTK_GFINDEX1D–4D`, `CCTK_VECTGFINDEX1D–4D`, the `CCTK_WARN`/`ERROR`/`INFO`/`V*` macros |
| `cctk_Arguments.h` | `CCTK_ARGUMENTS`, `DECLARE_CCTK_ARGUMENTS[_CHECKED]`, `CCTK_PASS_CTOC`/`FTOF` |
| `cctk_Parameters.h` | `DECLARE_CCTK_PARAMETERS`, `CCTK_ParameterGet/Set/Walk/Data/Level/ValString`, `CCTK_PARAMWARN` |
| `cctk_Groups.h` | Static group/variable metadata: `CCTK_GroupIndex`, `FirstVarIndex`, `FullName`, `GroupData`, `NumGroups/Vars`, `VarIndex/Name/TypeI`, `DeclaredTimeLevels`, `GroupTagsTable` |
| `cctk_GroupsOnGH.h` | *Dynamic*, per-cGH data: `CCTK_GroupDynamicData`, `ActiveTimeLevels`, `CCTK_Group{gsh,lsh,ash,lbnd,ubnd,bbox,nghostzones}{GI,GN,VI,VN}`, `CCTK_VarDataPtr[B,I]`, `CCTK_QueryGroupStorage` |
| `cctk_Comm.h` | `CCTK_SyncGroup[I]`, `SyncGroupsI`, `CCTK_ArrayGroupSize[I]` |
| `CommOverloadables.h` | The **overloadable** driver entry points: `CCTK_MyProc`, `nProcs`, `Barrier`, `Abort`, `Exit`, `Enable/DisableGroupStorage`/`Comm`, `GroupStorageIncrease/Decrease`, `CCTK_InterpGridArrays`. Who replaces them: [driver.md](driver.md) |
| `cctk_Reduction.h` | `CCTK_ReduceGridArrays`, `ReduceArraysGlobally`, `ReduceLocalArrays`, `ReductionHandle`, the `Register*ReductionOperator` macros |
| `cctk_Interp.h` | `CCTK_InterpLocalUniform`, `InterpHandle`, `InterpRegisterOpLocalUniform`, plus undocumented `InterpOperator`, `InterpOperatorImplementation`, `NumInterpOperators` |
| `cctk_IOMethods.h` | `CCTK_RegisterIOMethod` + `...OutputGH/OutputVarAs/TimeToOutput/TriggerOutput`, `CCTK_OutputGH/Var/VarAs[ByMethod]` |
| `cctk_GHExtensions.h` | `CCTK_RegisterGHExtension[SetupGH/InitGH/ScheduleTraverseGH]`, `CCTK_GHExtension[Handle]`, undocumented `CCTK_UnregisterGHExtension` |
| `cctk_Schedule.h` | `CCTK_ScheduleTraverse`, `ScheduleQueryCurrentFunction`, `SchedulePrintTimes[ToFile]` |
| `cctk_WarnLevel.h` | `CCTK_Error/VError/Warn/VWarn/Info/VInfo`, `WarnCallbackRegister` |
| `cctk_Timers.h` | `CCTK_Timer[I]`, `TimerCreate[I]`, `TimerStart/Stop/Reset/Destroy[I]`, `CCTK_TimerClockName/Resolution/Seconds`, `NumTimerClocks` |
| `cctk_ActiveThorns.h` | `CCTK_IsThornActive/Compiled`, `IsImplementationActive/Compiled`, `NumCompiledThorns/Implementations`, `ThornImplementation`, `ActivatingThorn` |
| `cctk_Loop.h` | `CCTK_LOOP{1,2,3}_{ALL,INT,BND,INTBND}` + `CCTK_ENDLOOP*` |
| `cctk_Misc.h` | `CCTK_Equals`, `CCTK_RunTime`, `CCTK_CommandLine`, `CCTK_CreateDirectory`, `CCTK_RegexMatch`, `CCTK_FortranString` |
| `cctk_Complex.h` | `CCTK_Cmplx*` — nominally deprecated (see below) |
| `cctk_Coord.h` | `CCTK_Coord*` — **all deprecated**, superseded by thorn `CoordBase` |
| `util_Table.h` | `Util_Table{Create,FromString,Clone,Destroy}`, `Set/Get<Type>[Array]`, iterators `Util_TableIt*`, introspection `Util_TableQuery*`, debug `Util_TablePrint*` |
| `util_String.h` | `Util_StrCmpi`, `Strlcat/Strlcpy`, `StrSep`, + undocumented `Util_SplitString`, `SplitFilename`, `StrMemCmpi`, `asnprintf` |

Aliased-function helpers (`CCTK_IsFunctionAliased`) have **no static header** — they are
generated at build time by `lib/sbin/CreateFunctionBindings.pl`.

---

## The Driver_* API (PreSync-aware drivers)

Used by Carpet/CarpetX; prototypes in the driver's own `Carpet_Prototypes.h`. Real names
start `Driver_`, **not** `CCTK_`, and all take `cctkGH` first:

```
CCTK_INT Driver_GetValidRegion(const CCTK_POINTER_TO_CONST cctkGH, CCTK_INT vi, CCTK_INT tl)
void     Driver_SetValidRegion(cctkGH, CCTK_INT vi, CCTK_INT tl, CCTK_INT where)
CCTK_INT Driver_NotifyDataModified(cctkGH, int *vars, int *tls, int nvars, int *where)
CCTK_INT Driver_RequireValidData(cctkGH, ...)
CCTK_INT Driver_SelectGroupForBC(...)  /  Driver_SelectVarForBC(...)
```

`DriverReference.tex` shows `CCTK_*` names for four of these. They do not exist.

---

## Conventions

- Pass `const cGH *cctkGH` to every `CCTK_` call unless the call mutates the GH.
- Two grid-array groups with identical size/ghostzones/distribution are guaranteed
  identical local shapes (`lsh`) even with different types or timelevel counts.
- `CCTK_MyProc`/`CCTK_nProcs` accept `NULL` safely.
- There is **no point-to-point or broadcast API**. Fan a scalar out with
  `CCTK_ReduceLocalScalar` + `"sum"` (zero everywhere else). True point-to-point needs
  raw MPI, which thorns are discouraged from calling directly (it locks out drivers).
- Check for MPI with the makefile variable `HAVE_MPI` or the macro `CCTK_MPI`.
- `CCTK_Exit`/`CCTK_Abort` need a `cctkGH`; passing `NULL` deep in a call stack works if
  the driver tolerates it.
- There is no way to recover the exact source version from a binary — use the
  `Formaline` thorn to embed the full source.
- `MPI_Init` is called once by the flesh, before argv parsing (MPI may mangle argv).

---

## Signature traps worth memorizing

| Call | Reality |
|---|---|
| `CCTK_Abort` | first arg is **non-const** `cGH *` (unlike almost everything else) |
| `CCTK_Enable/DisableGroupStorage`/`Comm` (+`I`) | first arg is `const cGH *` — the docs say otherwise for 7 of the 8 |
| `CCTK_SetupGH` | takes `tFleshConfig *config` (**pointer**), not by value |
| `CCTK_RegisterGHExtensionInitGH` | callback is `int (*)(cGH*)`, not `void *(*)(cGH*)` |
| `CCTK_GetClockName/Resolution/Seconds` | **do not exist.** Use `CCTK_TimerClockName/Resolution/Seconds` |
| `CCTK_PrintGroup` / `CCTK_PrintVar` | Fortran-linkage wrappers only; no plain-C symbol |
| `CCTK_RegisterReductionOperator(a,b)` | a 2-arg macro, not a 0-arg call |
| `CCTK_CmplxAbs` | returns `CCTK_REAL`, not `CCTK_COMPLEX` |
| `CCTK_IsFunctionAliased` | returns `CCTK_INT` (config-dependent width), not plain `int` |
| `CCTK_FortranString` length param | `CCTK_FORTRAN_STRLEN_T`, possibly 64-bit — not `int` |
| `CCTK_Warn`, `CCTK_RegisterBanner` | return `int`, not `void` |
| `CCTK_NumTimerClocks` | returns `unsigned int` |
| `cGroup` struct | has a `centeringtable` field the docs omit |
| `cGroupDynamicData` struct | has `alignment`, `alignment_offset`, `maxtimelevels` — 14 members, not 11 |

Full list with citations: [doc-traps.md](doc-traps.md).

### The complex-number situation

`CCTK_Cmplx*` is labelled deprecated "in favour of native C99/C++ complex", but
`cctk_Complex.h` deliberately avoids `<complex.h>` in plain C (to keep `I` out of the
global namespace), so no native replacement is actually wired up for C thorns. The
deprecation is aspirational. For checkpointing complex grid variables, `IOHDF5` supports
them and `IOFlexIO` does not.
