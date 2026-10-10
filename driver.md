# Driver Thorns in Cactus

A **driver** is a special kind of Cactus thorn. The flesh (core Cactus
runtime) deliberately does **not** allocate memory for grid variables,
decompose the domain across processors, exchange ghost zones, or decide
how adaptive mesh refinement (AMR) and multi-patch grids work. All of
that is the job of a driver.

Exactly one active thorn must provide the `Driver` implementation at
runtime. Three drivers ship with this tree:

| Thorn | Arrangement | Role |
|-------|-------------|------|
| **PUGH** | `CactusPUGH` | Parallel unigrid driver (MPI). The classic default. |
| **Carpet** | `Carpet` | Parallel Berger–Oliger style AMR driver (MPI). |
| **CarpetX** | `CarpetX` | Parallel block-structured AMR driver built on [AMReX](https://amrex-codes.github.io). |

Application thorns never depend on a specific driver thorn by name.
They depend on the **`Driver` implementation** (and on flesh APIs such
as `CCTK_SyncGroup` / `CCTK_MyProc`). At compile time you may include
more than one driver thorn; at runtime the parameter file activates
exactly one of them.

Writing a driver of your own is a separate, rarer task: the thorn skeleton,
the startup / SetupGH / ScheduleTraverse anatomy and a checklist live in
[driver-implementation.md](driver-implementation.md).

---

## What a driver does

From the Users Guide glossary and Infrastructure chapter, a driver:

1. **Creates and owns the grid hierarchy**  
   It decides the global grid size, local subdomains, ghost zones,
   periodicity, processor topology, and (for AMR drivers) refinement
   levels, components/patches, and time refinement.

2. **Manages memory for grid variables**  
   Scalars, grid functions (GFs), and grid arrays only get storage when
   the driver allocates it (via schedule `STORAGE` clauses, explicit
   enable/increase calls, or driver-internal policy).

3. **Implements parallel operations**  
   Ghost-zone exchange (synchronisation), barriers, process rank/count,
   and orderly exit/abort on all ranks.

4. **Fills the `cGH` structure** for scheduled routines  
   Before a scheduled function runs, the driver must make
   `cctkGH->data[var][tl]`, `cctk_lsh`, `cctk_gsh`, `cctk_lbnd`,
   `cctk_nghostzones`, etc. describe the *current* local grid piece
   (level, component, tile, …).

5. **Optionally drives the main loop**  
   Unigrid drivers may keep the flesh’s default initialise/evolve loop.
   AMR drivers almost always **overload** `CCTK_Initialise`,
   `CCTK_Evolve`, and `CCTK_Shutdown` so they can traverse levels,
   prolongate/restrict, regrid, and cycle time levels correctly.

6. **Optionally provides related services**  
   Local/global interpolation, reductions, I/O methods, checkpoint
   recovery, valid-region / PreSync bookkeeping
   ([schedule-and-presync.md](schedule-and-presync.md)), and boundary-condition
   selection hooks (`Driver_*` APIs used by application thorns).

If no driver is active, flesh dummy routines abort with messages such as
*“No driver thorn activated to provide storage for variables”*
(`repos/flesh/src/main/Dummies.c`).

---

## How the flesh plugs in a driver

### Implementation name

Every driver thorn’s `interface.ccl` must contain:

```ccl
implements: Driver
```

(or `IMPLEMENTS: Driver`). Parameters declared in that thorn under the
`restricted:` section become available to other thorns as
`driver::<name>` (implementation-scoped parameters), for example
`driver::periodic`.

How `restricted:`/`global:` sharing works, and why a `private:` parameter
cannot be shared, is [thorn-anatomy.md](thorn-anatomy.md).

### Overloading vs registration

The flesh guarantees a fixed API surface. Drivers fill it in by
**overloading** (exactly one provider wins — first overload succeeds):

- **Main layer** (`MainOverloadables.h`):  
  `CCTK_Initialise`, `CCTK_Evolve`, `CCTK_Shutdown`,  
  `CCTK_MainLoopIndex`, `CCTK_SetMainLoopIndex`
- **Comm layer** (`CommOverloadables.h`): storage, sync, ranks, …  
  (full list under *Functions a driver must overload*, below)

Drivers also **register a GH extension**: opaque, per-`cGH` state that
holds all grid-dependent bookkeeping.

### GH extension callbacks

At startup the driver typically does:

```c
int handle = CCTK_RegisterGHExtension("MyDriver");
CCTK_RegisterGHExtensionSetupGH(handle, MySetupGH);
CCTK_RegisterGHExtensionInitGH(handle, MyInitGH);           /* optional */
CCTK_RegisterGHExtensionScheduleTraverseGH(handle, MyTraverseGH);
```

| Callback | When | Responsibility |
|----------|------|----------------|
| **SetupGH** | When a `cGH` is created (`CCTK_SetupGH`) | Allocate the extension; set up domain decomposition and group descriptors. Return the extension pointer. |
| **InitGH** | After the scheduler is initialised on that GH | Finish initialisation that needs a live schedule. |
| **ScheduleTraverseGH** | Whenever the flesh walks a schedule bin on a GH | Point `GH->data[...]` at the correct memory, fill geometry fields on `cGH`, then call `CCTK_ScheduleTraverse`. |

For multi-level / multi-patch drivers, schedule traversal is often
driven by a custom **CallFunction** hook so each scheduled routine can
run once per component (or tile) with a correctly filled `cGH`.

### Startup schedule name

By convention, drivers schedule their startup routine as
`Driver_Startup`:

```ccl
schedule MyDriver_Startup at STARTUP as Driver_Startup
{
  LANG: C
} "Start up the driver"
```

Other thorns can schedule `BEFORE Driver_Startup` / `AFTER Driver_Startup`
when they must run relative to driver registration (for example setting
group tags). Shutdown is often aliased as `Driver_Terminate` or
`Driver_Shutdown`.

---

## Functions a driver must overload

The Infrastructure Thorn Writers Guide lists the required overload set.
In modern code, **group storage increase/decrease** is preferred over the
older enable/disable pair; **`SyncGroupsByDirI`** is preferred over
**`SyncGroup`**.

### Core communication / storage API

| Overload | Purpose |
|----------|---------|
| `CCTK_OverloadGroupStorageIncrease` | Allocate (more) time levels for groups; return previous active levels. |
| `CCTK_OverloadGroupStorageDecrease` | Free time levels. |
| `CCTK_OverloadQueryMaxTimeLevels` | Max time levels ever allocated for groups (size of `GH->data[var]`). |
| `CCTK_OverloadEnableGroupStorage` / `DisableGroupStorage` | Legacy on/off storage (still overloaded by Carpet/CarpetX). |
| `CCTK_OverloadEnableGroupComm` / `DisableGroupComm` | Mark groups for communication; prepare comm metadata. |
| `CCTK_OverloadSyncGroupsByDirI` | Exchange ghost zones for a list of groups, optionally by direction. |
| `CCTK_OverloadSyncGroup` | Deprecated single-group sync (PUGH still supports it). |
| `CCTK_OverloadArrayGroupSizeB` | Local size of a GF/array group in one direction. |
| `CCTK_OverloadQueryGroupStorageB` | Whether a group currently has storage. |
| `CCTK_OverloadGroupDynamicData` | Fill a `cGroupDynamicData` (gsh/lsh/lbnd/ubnd/bbox/ghosts/timelevels). |
| `CCTK_OverloadBarrier` | Global barrier across processes. |
| `CCTK_OverloadMyProc` / `CCTK_OverloadnProcs` | Rank and communicator size. |
| `CCTK_OverloadParallelInit` | Early parallel initialisation (PUGH). |
| `CCTK_OverloadExit` / `CCTK_OverloadAbort` | Collective exit / abort. |

Prototypes follow `repos/flesh/src/include/CommOverloadables.h`. Notable
signatures:

```c
int GroupStorageIncrease(const cGH *GH, int n_groups,
                         const int *groups, const int *timelevels,
                         int *status);
int SyncGroupsByDirI(const cGH *GH, int num_groups,
                     const int *groups, const int *directions);
int GroupDynamicData(const cGH *GH, int group, cGroupDynamicData *data);
const int *ArrayGroupSizeB(const cGH *GH, int dir, int group,
                           const char *groupname);
```

### Main-loop overloads (optional for unigrid, required for AMR)

| Overload | Purpose |
|----------|---------|
| `CCTK_OverloadInitialise` | Create GHs, run initial-data schedule bins, recover if needed. |
| `CCTK_OverloadEvolve` | Time-step loop: cycle time levels, evolve, restrict/prolongate, regrid, output. |
| `CCTK_OverloadShutdown` | Tear down driver state after evolution. |

The flesh supplies defaults (`CactusDefaultInitialise`,
`CactusDefaultEvolve`, `CactusDefaultShutdown`) that are adequate for a
simple unigrid driver (PUGH often only overloads **Evolve**). Carpet and
CarpetX overload all three.

### Optional extras

| Overload / registration | Purpose |
|-------------------------|---------|
| `CCTK_OverloadInterpGridArrays` | Driver-aware interpolation of grid arrays. |
| `CCTK_OverloadOutputGH` | Driver-controlled output pass each iteration. |
| `CCTK_InterpRegisterOpLocalUniform` | Local interpolator (CarpetX). |
| I/O method registration | `CCTK_RegisterIOMethod*` (usually companion IO thorns). |
| Reduction / interpolation operators | Often separate thorns (`PUGHReduce`, `CarpetReduce`, …). |

### Application-facing `Driver_*` helpers

Application thorns call higher-level helpers. A PreSync-aware driver
provides them as **aliased functions**, which is a different mechanism from
the overload macros above: evolution thorns call these, nobody registers
them with the flesh.

| Function | Role |
|----------|------|
| `Driver_SelectGroupForBC` / `Driver_SelectVarForBC` | Record how BCs should be applied when the driver syncs. |
| `Driver_RequireValidData` / `Driver_NotifyDataModified` | Request or report validity of interior/boundary/ghost regions. |
| `Driver_GetValidRegion` / `Driver_SetValidRegion` | Query or set validity masks (`WH_INTERIOR`, `WH_BOUNDARY`, `WH_GHOSTS`, …). |

**Signatures live in [cctk-api.md](cctk-api.md), not here.** So does the
warning that the Reference Manual's `DriverReference.tex` documents four of
these under `CCTK_*` names that do not exist — do not take the names from
it. What validity means and how `presync_mode` gates it is
[schedule-and-presync.md](schedule-and-presync.md).

Carpet wires PreSync into its `CallFunction` path; schedule groups such as
`Driver_BoundarySelect` / `Driver_ApplyBCs` appear in Carpet's
`schedule.ccl`.

---

## Comparing the three drivers

### PUGH (`CactusPUGH/PUGH`)

- **Model**: single regular grid, domain-decomposed across MPI ranks.
- **Startup**: registers GH extension Setup/Init/ScheduleTraverse;
  overloads storage, sync, barrier, ranks, exit; optionally Evolve.
- **Parameters**: `PUGH::global_n*`, `local_n*`, `ghost_size*`,
  `partition*`, and restricted `driver::periodic*`.
- **Strengths**: simple, robust, good for tests and problems that do not
  need AMR.
- **Companion thorns**: `PUGHReduce`, `PUGHInterp`, `PUGHSlab`,
  `CactusPUGHIO/*`.

### Carpet (`Carpet/Carpet`)

- **Model**: Berger–Oliger AMR with multiple levels and components;
  full overloads of Initialise/Evolve/Shutdown/OutputGH.
- **Startup**: `CarpetStartup` as `Driver_Startup`; multi-model MPI
  split can run `BEFORE Driver_Startup`.
- **Extras**: PreSync, poisoning, checksums, schedule wrappers,
  regridding hooks, time refinement.
  Depth on all of that: [schedule-and-presync.md](schedule-and-presync.md).
- **Companion thorns**: `CarpetLib`, `CarpetRegrid*`, `CarpetIO*`,
  `CarpetReduce`, `CarpetInterp*`, …

### CarpetX (`CarpetX/CarpetX`)

- **Model**: AMReX-backed block-structured AMR; GPU-aware loops via
  companion loop headers.
- **Startup**: same GH-extension + overload pattern as Carpet, plus
  AMReX initialisation inside SetupGH, local interpolator registration,
  and `InterpGridArrays` overload.
- **Interface**: richer `PROVIDES FUNCTION` surface (domain
  specification, loop boxes, Poisson solve, `DriverInterpolate`, …).
- **Companion thorns**: `Loop`, `AMReX` external, `ODESolvers`,
  `CoordinatesX`, various `*X` physics thorns.

### Feature matrix (approximate)

| Capability | PUGH | Carpet | CarpetX |
|------------|:----:|:------:|:-------:|
| Unigrid MPI | yes | yes (1 level) | yes (1 level) |
| AMR | no | yes | yes (AMReX) |
| Overloads main loop | Evolve optional | yes | yes |
| PreSync / valid regions | limited | yes | yes |
| GPU / AMReX boxes | no | no | yes |
| Implementation name | `Driver` | `Driver` | `Driver` |

---

## Minimal mental model

```
Parameter file activates thorn PUGH | Carpet | CarpetX
                │
                ▼
        Driver_Startup
        registers GH extension + overloads flesh APIs
                │
                ▼
        CCTK_Initialise  (default or overloaded)
            SetupGH → build domain & descriptors
            run INITIAL / BASEGRID / … schedule bins
                │
                ▼
        CCTK_Evolve      (default or overloaded)
            each step / level / component:
              ScheduleTraverseGH fills cGH
              user thorns read/write GH->data
              SyncGroupsByDirI exchanges ghosts
                │
                ▼
        CCTK_Shutdown
```

Everything application authors write — MoL, BSSN, I/O, analysis —
assumes this contract: **the driver owns memory and parallelism; the
flesh owns scheduling and the API names; physics thorns own the PDE.**

---

## Primary references in this tree

The four `doc/` rows are **LaTeX sources that the brain does not trust** —
see [doc-traps.md](doc-traps.md) before relying on any of them, and prefer
the header and the real driver source underneath.

| Topic | Location | Trust |
|-------|----------|-------|
| Driver concept (Users Guide) | `repos/flesh/doc/UsersGuide/InfrastructureThorns.tex` (§ Drivers) | Implies a driver overloads `Enable`/`DisableGroupStorage`. PUGH does not |
| Parallelisation for app writers | `repos/flesh/doc/UsersGuide/ApplicationThorns.tex` (§ Parallelisation) | Broadly sound |
| Glossary entry | `repos/flesh/doc/UsersGuide/Appendices.tex` (`driver`) | Broadly sound |
| `Driver_*` API reference | `repos/flesh/doc/ReferenceManual/DriverReference.tex` | **Four of six functions are under `CCTK_*` names that do not exist.** Use [cctk-api.md](cctk-api.md) |
| Comm overload list | `repos/flesh/src/include/CommOverloadables.h` | Source. Authoritative |
| Main overload list | `repos/flesh/src/include/MainOverloadables.h` | Source. Authoritative |
| Dummy errors without a driver | `repos/flesh/src/main/Dummies.c` | Source. Authoritative |
| PUGH startup / storage / comm | `arrangements/CactusPUGH/PUGH/src/` | Source. Smallest complete driver |
| Carpet startup / evolve | `arrangements/Carpet/Carpet/src/CarpetStartup.cc`, `Evolve.cc` | Source |
| CarpetX startup | `arrangements/CarpetX/CarpetX/src/driver.cxx` | Source |

`arrangements/*/*` are symlinks into `repos/*`; editing either edits the real
git checkout. See [layout.md](layout.md).

---

## Practical notes

1. **One driver at runtime.** Multiple drivers may appear in a
   configuration’s thorn list for convenience, but `ActiveThorns` must
   enable only one `Driver` implementation.

2. **Depend on the implementation, not the thorn.** Other thorns should
   `inherits:` / use parameters from `driver`, not `#include` PUGH- or
   Carpet-specific headers, unless they are deliberately driver-specific
   companion thorns.

3. **Schedule `STORAGE` is a driver request.** The flesh records intent;
   the driver allocates. Dynamic
   `CCTK_EnableGroupStorage` / `GroupStorageIncrease` must go through the
   same path.

4. **AMR complexity lives in Evolve + CallFunction**, not in physics
   thorns. If your driver needs per-box loops, put them in the driver’s
   schedule traversal / call-function wrapper so existing scheduled
   routines keep using a single local `cGH`.

5. **Study PUGH first.** It is the smallest complete driver. Carpet and
   CarpetX are large, but their *startup overload lists* are deliberately
   parallel to PUGH’s — they mainly add a sophisticated main loop and
   grid hierarchy on top of the same contract.
