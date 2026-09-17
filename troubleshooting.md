# Troubleshooting — symptom → cause → fix

Ordered by phase. For the full ExternalLibraries/GPU cases see
[external-libraries.md](external-libraries.md).

---

## Configure / CST

| Symptom | Cause | Fix |
|---|---|---|
| CCL syntax rejected and you believe it is valid | The docs are a lossy summary of the grammar | Read `repos/flesh/src/piraha/pegs/{interface,param,schedule,config}.peg` |
| `STEERABLE=RECOVERY` rejected | Only `NEVER`/`ALWAYS`/`RECOVER` exist; the docs' prose is wrong | Use `RECOVER` |
| Generated bindings stale after a CCL edit | CST did not rerun | `touch` any CCL file or `lib/make/force-rebuild`, or `gmake <cfg>-rebuild` |
| Optionlist change has no effect | The configuration is already configured | `gmake <cfg>-config options=... THORNLIST=...`, or `<cfg>-delete` first |
| `gmake` stops to ask "Setup configuration X (yes)?" | Interactive prompt | Add `PROMPT=no` |
| Configuration name rejected | Ends in a reserved suffix (`-build`, `-clean`, `-config`, `-delete`, …) | Rename |
| `Duplicate checkouts: ...` (GetComponents) | Same `Arr/Thorn` in `!CHECKOUT` and as an enabled body line | Keep only one form |
| Cross-consistency error about restricted parameter defaults | Two thorns share an implementation but disagree on a default | Make the defaults match |

## Compile

| Symptom | Cause | Fix |
|---|---|---|
| `DECLARE_CCTK_PARAMETERS` / `DECLARE_CCTK_ARGUMENTS` undefined | Missing `#include "cctk_Parameters.h"` / `"cctk.h"`+`"cctk_Arguments.h"` | Add them |
| Fortran: "dummy argument CCTK_DIM has not been given a type" | Same missing include | Add them |
| Fortran: parameters have silently wrong values, no error | Missing `DECLARE_CCTK_PARAMETERS` | Add it |
| CST mangles braces around commented-out code | `#if 0 ... #endif` wrapping a `DECLARE_CCTK_*` breaks the CST's automatic closing-brace insertion | Keep commented-out code in matched `{}` |
| Undefined reference / link-order error | Almost always a missing `inherits:` in `interface.ccl` | Add the inherit |
| Aliased-function link error | Binding generation | Inspect `configs/<cfg>/bindings/Functions` |
| Stale or renamed include still being found | Cached dependencies | `gmake <cfg>-cleandeps` |
| Bogus "unresolved text symbol" for a scheduled function | The compiler OOMed and silently produced an empty object file | `touch` the source and rebuild, possibly at `OPTIMISE=no` |
| Build hangs, or odd "checking status of libX.a" | Clock skew between the build host and the filesystem | Check `date` vs file mtimes; rebuild with `VERBOSE=yes` |
| Need to isolate one thorn | | `gmake <cfg>-build BUILDLIST="<Thorn>" VERBOSE=yes` |
| Need a specific thorn built at different optimisation | | Set `C_OPTIMISE_FLAGS`/`CXX_OPTIMISE_FLAGS`/`F77_OPTIMISE_FLAGS`/`F90_OPTIMISE_FLAGS` in that thorn's `make.code.defn` |
| F77/F90 name-mangling mismatches | Different compilers used for F77 and F90 | Use the same compiler for both |
| No C++ available on some nodes | | Configure with `CXX=none` if no thorn needs C++ |
| Out of disk in `configs/` | | Set `CACTUS_CONFIGS_DIR` to relocate it |
| `/usr/bin/ld: cannot find -ludev` | hwloc (and some other stacks) link against libudev | Install `libudev-dev` (provides the `libudev.so` symlink); runtime needs only `libudev1` |

## Runtime

| Symptom | Cause | Fix |
|---|---|---|
| **Segfault immediately after the schedule tree prints** | A `CCTK_STARTUP` routine declared with `CCTK_ARGUMENTS` — no grid exists yet | Signature must be `int fn(void)` |
| `"CCTK_Equals: First string null"` | Mis-detected Fortran name mangling | Full `realclean`, reconfigure, rebuild |
| A grid-function pointer is unexpectedly NULL | Either (a) the group has no storage by default — `ADMBase::shift`/`dtlapse`/`dtshift`, `HydroBase::Bvec`, all gated on an `initial_*` parameter; or (b) `presync_mode = presync-only` and the routine did not declare the variable | Set the gating parameter in the parfile, or add the `READS`/`WRITES` clause. See [schedule-and-presync.md](schedule-and-presync.md) |
| `Grid function "X" is invalid ...; required:` | CarpetX validity tracking: nothing validly wrote it earlier | Fix the ordering, or add the missing `WRITES` |
| `contains ... nans ... expected valid` | A `WRITES: g(everywhere)` clause but only the interior was written | Write the boundary too, or narrow the clause to `(interior)` |
| CarpetX aborts at startup over `presync_mode` | CarpetX accepts only `mixed-error` and `presync-only` | Set one of those |
| A thorn is "missing" at runtime | Not in the compile ThornList, or not in `ActiveThorns` | Align ThornList, `ActiveThorns`, and `arrangements/` |
| `mpirun ... "Unknown option -np"` | | `mpirun ./cactus_x par -i -np 8` |
| `libhdf5.so` load errors | `LD_LIBRARY_PATH` not set, or not propagated to remote ranks by the launcher | Set it in the runscript, or remove the `.so` files to force static linking |
| `Unable to create UD QP` / `PSM3 can't open nic unit` | OFI/PSM3 trying the node's RoCE/IB NIC | `export I_MPI_FABRICS=shm` (+ `FI_PROVIDER=tcp`) |
| SIGILL / `Illegal instruction` only on compute nodes | Binary built for the login node's ISA; the partition has older CPUs | Submit to a CPU-matched partition, or lower the arch flags |
| `IOBasic::outInfo_*` prints nothing useful | No reduction thorn active | Activate one (e.g. `PUGHReduce`) |
| Want to stop at a coordinate time rather than an iteration | | `Cactus::terminate="time"` + `Cactus::cctk_final_time` instead of `cctk_itlast` |
| Two `CCTK_ANALYSIS` routines trigger on the same variable and one never runs | By design — the first scheduled one wins | Give them different triggers |
| Need the exact source a binary was built from | Not recoverable | Activate the `Formaline` thorn next time |

## Performance (not a failure, but usually a surprise)

| Symptom | Cause | Fix |
|---|---|---|
| CarpetX run much slower than the kernel work alone suggests | `CarpetX::poison_undefined_values` defaults to **`yes`**, adding a full-array poison scan per grid function per READS/WRITES clause per scheduled routine, plus host-side checksum passes | Set `CarpetX::poison_undefined_values = no` to measure. See [schedule-and-presync.md](schedule-and-presync.md) for exactly what you give up (value-level checks; presync validity checking stays on) |
| `__curand_matvec_inplace` prominent in a GPU profile | AMReX seeds one XORWOW RNG state per concurrent GPU thread at `amrex::Initialize` — ~885k states on an A100. cuRAND's skipahead is the matvec | Nothing to fix: it is one launch at startup, not per kernel, and AMReX 25.11 has no knob. Confirm with `nsys stats --report cuda_gpu_kern_sum` (Instances = 1). See [external-libraries.md](external-libraries.md) |
| Build parallelism has no effect | `nproc` under-reports under a cgroup CPU quota | Trust `nproc` for `-j`/`TJOBS`/`FJOBS`; trim the ThornList instead |

## Documentation build

| Symptom | Cause |
|---|---|
| Thorns missing from a generated ThornGuide | Bad ThornGuide LaTeX markup in an *earlier* thorn aborted the run |
