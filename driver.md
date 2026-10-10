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

---

## 1. What a driver does

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
   recovery, valid-region / PreSync bookkeeping, and boundary-condition
   selection hooks (`Driver_*` APIs used by application thorns).

If no driver is active, flesh dummy routines abort with messages such as
*“No driver thorn activated to provide storage for variables”*
(`repos/flesh/src/main/Dummies.c`).

---

## 2. How the flesh plugs in a driver

### 2.1 Implementation name

Every driver thorn’s `interface.ccl` must contain:

```ccl
implements: Driver
```

(or `IMPLEMENTS: Driver`). Parameters declared in that thorn under the
`restricted:` section become available to other thorns as
`driver::<name>` (implementation-scoped parameters), for example
`driver::periodic`.

### 2.2 Overloading vs registration

The flesh guarantees a fixed API surface. Drivers fill it in by
**overloading** (exactly one provider wins — first overload succeeds):

- **Main layer** (`MainOverloadables.h`):  
  `CCTK_Initialise`, `CCTK_Evolve`, `CCTK_Shutdown`,  
  `CCTK_MainLoopIndex`, `CCTK_SetMainLoopIndex`
- **Comm layer** (`CommOverloadables.h`): storage, sync, ranks, …  
  (full list in §3)

Drivers also **register a GH extension**: opaque, per-`cGH` state that
holds all grid-dependent bookkeeping.

### 2.3 GH extension callbacks

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

### 2.4 Startup schedule name

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

## 3. Functions a driver must overload

The Infrastructure Thorn Writers Guide lists the required overload set.
In modern code, **group storage increase/decrease** is preferred over the
older enable/disable pair; **`SyncGroupsByDirI`** is preferred over
**`SyncGroup`**.

### 3.1 Core communication / storage API

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

### 3.2 Main-loop overloads (optional for unigrid, required for AMR)

| Overload | Purpose |
|----------|---------|
| `CCTK_OverloadInitialise` | Create GHs, run initial-data schedule bins, recover if needed. |
| `CCTK_OverloadEvolve` | Time-step loop: cycle time levels, evolve, restrict/prolongate, regrid, output. |
| `CCTK_OverloadShutdown` | Tear down driver state after evolution. |

The flesh supplies defaults (`CactusDefaultInitialise`,
`CactusDefaultEvolve`, `CactusDefaultShutdown`) that are adequate for a
simple unigrid driver (PUGH often only overloads **Evolve**). Carpet and
CarpetX overload all three.

### 3.3 Optional extras

| Overload / registration | Purpose |
|-------------------------|---------|
| `CCTK_OverloadInterpGridArrays` | Driver-aware interpolation of grid arrays. |
| `CCTK_OverloadOutputGH` | Driver-controlled output pass each iteration. |
| `CCTK_InterpRegisterOpLocalUniform` | Local interpolator (CarpetX). |
| I/O method registration | `CCTK_RegisterIOMethod*` (usually companion IO thorns). |
| Reduction / interpolation operators | Often separate thorns (`PUGHReduce`, `CarpetReduce`, …). |

### 3.4 Application-facing `Driver_*` helpers

Application thorns call higher-level helpers (documented in the
Reference Manual *Driver\_\* Functions* chapter). Drivers that support
PreSync / automated boundaries implement the corresponding behaviour:

| Function | Role |
|----------|------|
| `Driver_SelectGroupForBC` / `Driver_SelectVarForBC` | Record how BCs should be applied when the driver syncs. |
| `Driver_RequireValidData` / `Driver_NotifyDataModified` | Request or report validity of interior/boundary/ghost regions. |
| `Driver_GetValidRegion` / `Driver_SetValidRegion` | Query or set validity masks (`WH_INTERIOR`, `WH_BOUNDARY`, `WH_GHOSTS`, …). |

These are not the same as the overload macros; they are fleshy or
driver-provided functions used by evolution thorns. Carpet wires PreSync
into its `CallFunction` path; schedule groups such as
`Driver_BoundarySelect` / `Driver_ApplyBCs` appear in Carpet’s
`schedule.ccl`.

---

## 4. Anatomy of an implementation

The flesh guide’s recommended structure matches all three real drivers.

### 4.1 Thorn skeleton

```
MyDriver/
  interface.ccl      # implements: Driver
  param.ccl          # restricted: (driver::*) + private grid parameters
  schedule.ccl       # Driver_Startup, optional terminate/shutdown
  configuration.ccl  # optional MPI / library requirements
  src/
    Startup.c(c)     # register GH extension + overloads
    SetupGH...       # domain + group setup
    Storage...       # GroupStorageIncrease/Decrease, queries
    Comm...          # SyncGroupsByDirI, Barrier, MyProc, nProcs
    Evolve...        # optional main loop
    ...
```

### 4.2 Startup (register everything)

Minimal pattern (compare `PUGH/src/Startup.c`,
`Carpet/src/CarpetStartup.cc`, `CarpetX/src/driver.cxx`):

```c
int MyDriver_Startup(void)
{
  int ext = CCTK_RegisterGHExtension("MyDriver");
  CCTK_RegisterGHExtensionSetupGH(ext, MySetupGH);
  CCTK_RegisterGHExtensionInitGH(ext, MyInitGH);
  CCTK_RegisterGHExtensionScheduleTraverseGH(ext, MyScheduleTraverseGH);

  CCTK_OverloadGroupStorageIncrease(MyGroupStorageIncrease);
  CCTK_OverloadGroupStorageDecrease(MyGroupStorageDecrease);
  CCTK_OverloadQueryMaxTimeLevels(MyQueryMaxTimeLevels);
  CCTK_OverloadSyncGroupsByDirI(MySyncGroupsByDirI);
  CCTK_OverloadEnableGroupComm(MyEnableGroupComm);
  CCTK_OverloadDisableGroupComm(MyDisableGroupComm);
  CCTK_OverloadBarrier(MyBarrier);
  CCTK_OverloadMyProc(MyMyProc);
  CCTK_OverloadnProcs(MynProcs);
  CCTK_OverloadExit(MyExit);
  CCTK_OverloadAbort(MyAbort);
  CCTK_OverloadArrayGroupSizeB(MyArrayGroupSizeB);
  CCTK_OverloadQueryGroupStorageB(MyQueryGroupStorageB);
  CCTK_OverloadGroupDynamicData(MyGroupDynamicData);

  /* AMR drivers also: */
  /* CCTK_OverloadInitialise(MyInitialise); */
  /* CCTK_OverloadEvolve(MyEvolve); */
  /* CCTK_OverloadShutdown(MyShutdown); */

  CCTK_RegisterBanner("Driver provided by MyDriver");
  return 0;
}
```

Only one thorn may successfully overload each symbol. If two drivers are
*active* in the parameter file, startup fails or behaves unpredictably;
activate exactly one.

### 4.3 The GH extension

Store **everything** grid-related here: pointers for each variable and
time level, local/global shapes, ghost widths, MPI neighbours, AMR level
lists, etc.

```c
struct MyExtension {
  void ***data;          /* [var][timelevel] -> memory */
  int *activetimelevels;
  int *maxtimelevels;
  /* domain decomposition, comm buffers, ... */
};
```

**SetupGH** outline:

1. Read parameters (global size, ghosts, periodicity, …).
2. Compute processor topology and local bounds.
3. For each Cactus group (`CCTK_NumGroups`, `CCTK_GroupData`), create
   driver-side descriptors (but do not necessarily allocate GF memory
   until storage is enabled).
4. Ensure **grid scalars** have storage (flesh expectation).
5. Return the extension pointer for `GH->extensions[handle]`.

### 4.4 ScheduleTraverseGH

Before calling into user code:

1. Set `GH->cctk_dim`, `cctk_lsh`, `cctk_gsh`, `cctk_lbnd`, `cctk_ubnd`,
   `cctk_ash`, `cctk_nghostzones`, `cctk_bbox`, `cctk_levfac`,
   `cctk_time`, `cctk_delta_time`, level/component indices, …
2. For every variable/timelevel with storage, set
   `GH->data[var][tl]` to the contiguous local buffer.
3. Call `CCTK_ScheduleTraverse(where, GH, call_function)`  
   - `call_function == NULL` uses the flesh default caller (fine for
     unigrid).  
   - A custom caller is the natural place for **looping over AMR
     components** or CarpetX tiles/boxes.

Return whether synchronisation was already performed for the routine’s
`SYNC` list (nonzero ⇒ flesh will not sync again).

### 4.5 Storage

Scheduler `STORAGE: group[tl]` clauses call into the driver. Preferred
implementation:

- **`GroupStorageIncrease`**: if inactive levels < requested, allocate
  and poison/initialise as needed; write old counts into `status[]`;
  return aggregate previous state.
- **`GroupStorageDecrease`**: free levels carefully (other schedule
  entries may still need them); restore prior counts.
- **`QueryMaxTimeLevels`**: report allocation capacity per group.

Memory layout must match what application thorns and Fortran bindings
expect: Fortran array order, ghost padding (`ash` vs `lsh`), and
alignment constraints advertised via `cGroupDynamicData`.

### 4.6 Synchronisation

`SyncGroupsByDirI` must:

1. For each group with communication enabled and storage active,
2. Exchange ghost zones with neighbouring subdomains (and periodic
   wraps if `driver::periodic*` is set),
3. Optionally fill symmetry/physical boundaries when the driver owns
   that pipeline (Carpet PreSync path),
4. Respect multi-level rules (sync on the current level only; prolongate
   separately).

PUGH implements classic MPI domain-decomposition halo exchange
(`PUGH/src/Comm.c` and send/receive helpers). Carpet and CarpetX also
handle inter-level and inter-box communication.

### 4.7 Evolution loop (AMR sketch)

Carpet/CarpetX-style responsibilities inside an overloaded Evolve:

1. While not done (iteration / time / runtime termination parameters):
2. **Cycle time levels** (rotate pointers; invalidate new “current”).
3. For each refinement level (coarse to fine or as required by the
   algorithm):  
   - Select level mode / enter component loops.  
   - `CCTK_Traverse` evolution bins (`EVOL`, `POSTSTEP`, …).  
   - Synchronise; apply BCs.  
   - Prolongate fine boundaries from coarse; restrict fine→coarse.
4. Periodic regridding / load balancing.
5. Analysis and `CCTK_OutputGH` (or overloaded OutputGH).
6. Checkpoint as scheduled.

Unigrid default evolve (`CactusDefaultEvolve`) simply steps a single GH
and calls output — enough when there is only one level.

---

## 5. Comparing the three drivers

### 5.1 PUGH (`CactusPUGH/PUGH`)

- **Model**: single regular grid, domain-decomposed across MPI ranks.
- **Startup**: registers GH extension Setup/Init/ScheduleTraverse;
  overloads storage, sync, barrier, ranks, exit; optionally Evolve.
- **Parameters**: `PUGH::global_n*`, `local_n*`, `ghost_size*`,
  `partition*`, and restricted `driver::periodic*`.
- **Strengths**: simple, robust, good for tests and problems that do not
  need AMR.
- **Companion thorns**: `PUGHReduce`, `PUGHInterp`, `PUGHSlab`,
  `CactusPUGHIO/*`.

### 5.2 Carpet (`Carpet/Carpet`)

- **Model**: Berger–Oliger AMR with multiple levels and components;
  full overloads of Initialise/Evolve/Shutdown/OutputGH.
- **Startup**: `CarpetStartup` as `Driver_Startup`; multi-model MPI
  split can run `BEFORE Driver_Startup`.
- **Extras**: PreSync, poisoning, checksums, schedule wrappers,
  regridding hooks, time refinement.
- **Companion thorns**: `CarpetLib`, `CarpetRegrid*`, `CarpetIO*`,
  `CarpetReduce`, `CarpetInterp*`, …

### 5.3 CarpetX (`CarpetX/CarpetX`)

- **Model**: AMReX-backed block-structured AMR; GPU-aware loops via
  companion loop headers.
- **Startup**: same GH-extension + overload pattern as Carpet, plus
  AMReX initialisation inside SetupGH, local interpolator registration,
  and `InterpGridArrays` overload.
- **Interface**: richer `PROVIDES FUNCTION` surface (domain
  specification, loop boxes, Poisson solve, `DriverInterpolate`, …).
- **Companion thorns**: `Loop`, `AMReX` external, `ODESolvers`,
  `CoordinatesX`, various `*X` physics thorns.

### 5.4 Feature matrix (approximate)

| Capability | PUGH | Carpet | CarpetX |
|------------|:----:|:------:|:-------:|
| Unigrid MPI | yes | yes (1 level) | yes (1 level) |
| AMR | no | yes | yes (AMReX) |
| Overloads main loop | Evolve optional | yes | yes |
| PreSync / valid regions | limited | yes | yes |
| GPU / AMReX boxes | no | no | yes |
| Implementation name | `Driver` | `Driver` | `Driver` |

---

## 6. Checklist: implementing a new driver

Use this as a working checklist when writing a fourth driver or a
teaching minimal driver.

### CCL and packaging

- [ ] `interface.ccl`: `implements: Driver`
- [ ] `param.ccl`: restricted periodicity (if applicable) + private
      grid/topology parameters; `shares:` any flesh parameters you need
      (`cactus::cctk_itlast`, …)
- [ ] `schedule.ccl`: `… as Driver_Startup` at `STARTUP`; terminate
      cleanly
- [ ] `configuration.ccl`: MPI / external library requirements
- [ ] Ensure thorn list activates **only one** Driver implementation

### Startup registration

- [ ] `CCTK_RegisterGHExtension` + Setup (+ Init) + ScheduleTraverse
- [ ] Overload storage increase/decrease + max timelevels
- [ ] Overload sync-by-direction, barrier, MyProc, nProcs, Exit, Abort
- [ ] Overload ArrayGroupSizeB, QueryGroupStorageB, GroupDynamicData
- [ ] Overload Enable/DisableGroupComm (and storage enable/disable if
      required for compatibility)
- [ ] Overload Initialise/Evolve/Shutdown if not using flesh defaults
- [ ] Register a banner string

### Correctness responsibilities

- [ ] Scalars always have usable storage
- [ ] `GH->data[var][tl]` is non-NULL iff that time level is active
- [ ] Geometry arrays on `cGH` match the memory layout you expose
- [ ] Ghost exchange is consistent with `nghostzones` and symmetries
- [ ] Time level cycling matches MoL / multi-step methods users expect
- [ ] Collective operations run on all ranks (no deadlocks on error paths)
- [ ] Recovery/checkpoint compatible with your layout (if you support it)

### Testing

- [ ] `CactusTest` / wave-toy style unigrid evolution with your driver
- [ ] Multi-process ghost exchange (norms match single-process)
- [ ] Storage on/off via schedule clauses
- [ ] If AMR: convergence under refinement, restrict/prolongate tests
- [ ] Build with another driver **inactive** to ensure no symbol clashes

---

## 7. Minimal mental model

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

## 8. Primary references in this tree

| Topic | Location |
|-------|----------|
| Driver concept (Users Guide) | `repos/flesh/doc/UsersGuide/InfrastructureThorns.tex` (§ Drivers) |
| Parallelisation for app writers | `repos/flesh/doc/UsersGuide/ApplicationThorns.tex` (§ Parallelisation) |
| Glossary entry | `repos/flesh/doc/UsersGuide/Appendices.tex` (`driver`) |
| `Driver_*` API reference | `repos/flesh/doc/ReferenceManual/DriverReference.tex` |
| Comm overload list | `repos/flesh/src/include/CommOverloadables.h` |
| Main overload list | `repos/flesh/src/include/MainOverloadables.h` |
| Dummy errors without a driver | `repos/flesh/src/main/Dummies.c` |
| PUGH startup / storage / comm | `arrangements/CactusPUGH/PUGH/src/` |
| Carpet startup / evolve | `arrangements/Carpet/Carpet/src/CarpetStartup.cc`, `Evolve.cc` |
| CarpetX startup | `arrangements/CarpetX/CarpetX/src/driver.cxx` |

---

## 9. Practical notes

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
