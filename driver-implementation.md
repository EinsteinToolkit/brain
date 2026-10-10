# Implementing a driver

The driver **contract** — what the flesh expects, what each overload means,
and how PUGH, Carpet and CarpetX differ — is [driver.md](driver.md). Read
that first. This file is the other half: the concrete shape of a driver
thorn, and a checklist for writing one.

This is a rare task. If you are debugging an existing driver or just need to
know what a driver guarantees, you want [driver.md](driver.md) instead.

---

## Anatomy of an implementation

The flesh guide’s recommended structure matches all three real drivers.

### Thorn skeleton

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

### Startup (register everything)

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

### The GH extension

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

### ScheduleTraverseGH

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

### Storage

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

### Synchronisation

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

### Evolution loop (AMR sketch)

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

## Checklist: implementing a new driver

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
      (ThornList vs CRL: [build-system.md](build-system.md))

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
