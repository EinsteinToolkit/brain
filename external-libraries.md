# ExternalLibraries, MPI, and GPU builds

`ExternalLibraries/*` are ordinary thorns whose job is to **detect an existing install
or build a bundled copy** of a third-party library, before any normal thorn compiles.

---

## Anatomy

| File | Role |
|---|---|
| `configuration.ccl` | `PROVIDES <Cap> { SCRIPT src/detect.sh OPTIONS <CAP>_DIR ... }` |
| `src/detect.sh` | Decide detect-vs-build; emit make variables |
| `src/build.sh` | Build the bundled tarball into `configs/<cfg>/scratch/external/<Thorn>` |
| `src/make.code.deps` | Rule that runs detect/build before the thorn's "done" stamp |
| `dist/*.tar*` | Bundled upstream sources |

`detect.sh` contract:

```
if FOO_DIR = BUILD            → force bundled build
else find_lib FOO ... "$FOO_DIR"
if not found                  → FOO_BUILD=1, FOO_DIR=$SCRATCH_BUILD/external/FOO
emit BEGIN MAKE_DEFINITION ... END for FOO_INC_DIRS, FOO_LIB_DIRS, FOO_LIBS
```

| Situation | Result |
|---|---|
| `FOO_DIR` points at a valid install | detect only; `scratch/done/FOO` stamp |
| `FOO_DIR` unset and nothing found | bundled `build.sh` |
| `FOO_DIR=BUILD` | bundled `build.sh` always |
| Prebuilt with the wrong features (e.g. AMReX without OpenMP while Cactus has it) | compile-time `#error` in CarpetX, or link failures |

**Capability ≠ thorn name.** `configuration.ccl` says `PROVIDES AMReX` / `REQUIRES MPI`;
the directory is `ExternalLibraries/AMReX`. Dependents get include/lib flags via the
generated `make.<Thorn>.defn` and `USESTHORNS`. `OPTIONAL <Cap>` dependencies are only
linked if a providing thorn is actually active.

ExternalLibraries often serialize on shared `scratch/` even with `TJOBS > 1`.

---

## MPI

Strongly prefer a **system-installed MPI**, and always test that it actually runs — a
successful link proves nothing.

- Cactus's `ExternalLibraries/MPI/src/detect.pl` only tries `-compile_info` and
  `--showme` on the wrapper. Intel oneAPI's `mpicxx` supports `-show` instead and,
  unsourced, prints a literal `I_MPI_SUBSTITUTE_INSTALLDIR`. **Do not rely on wrapper
  auto-detection there** — set `MPI_DIR`, `MPI_INC_DIRS`, `MPI_LIB_DIRS`, `MPI_LIBS`
  explicitly in the optionlist, and `source <mpi>/env/vars.sh` before any `mpirun`
  (including build-time conftest links).
- `mpirun` failing with `Unable to create UD QP` / `PSM3 can't open nic unit` means the
  OFI/PSM3 provider is trying the node's RoCE/IB NIC. For single-node runs:
  `export I_MPI_FABRICS=shm` (and `FI_PROVIDER=tcp` as a fallback).
- Old MPICH `ch_p4` binaries must always be launched via `mpirun`; running directly
  changes the CWD used to resolve relative parfile paths.
- `mpirun ... "Unknown option -np"` → put `-i` before it: `mpirun ./cactus_x par -i -np 8`.

---

## CUDA / nvcc

Typical CarpetX CUDA optionlist fragment:

```text
CXX = nvcc -x cu
LD  = nvcc --forward-unknown-to-host-compiler ...
OPENMP = yes
CPPFLAGS = -DSIMD_DISABLE
```

Consequences:

1. **Any ExternalLibraries package that runs CMake with `$CXX` will try to use nvcc as
   its host compiler and usually fail** (`Unknown argument -x`, broken CMake CXX test).
   Affected when `*_DIR=BUILD`: ADIOS2, NSIMD, yaml-cpp, openPMD, Silo. Prebuild those
   with g++/mpicxx and set `*_DIR`, or `#DISABLED` them.
2. **AMReX OpenMP must match Cactus OpenMP.** CarpetX hard-errors on a mismatch.
3. If AMReX was built with HDF5, its public headers may `#include <hdf5.h>` even when
   CarpetX does not list HDF5 in `USESTHORNS` — inject `-I$HDF5_HOME/include` globally.
4. `SM Arch ('sm_52') not found` from nvlink means the `-gencode`/`-arch` flag is on the
   compile line but not the **link** line.

Relevant options: `AMREX_ENABLE_CUDA`, `AMREX_CMAKE_CUDA_ARCHITECTURES`, `CUCC`,
`CUCCFLAGS`, `DISABLE_INT16`, `DISABLE_REAL16`.

---

## ROCm / HIP (AMD GPUs)

Differs structurally from the CUDA case:

- `hipcc` is a clang-based **ordinary host+device compiler** — there is no two-compiler
  split. Set `CC = CXX = LD = hipcc --offload-arch=gfxNNN` **globally**, for every thorn.
  No `CUCC`-style conditional override.
- `AMReX/configuration.ccl` already exposes `AMREX_ENABLE_HIP` and `AMREX_AMD_ARCH`, and
  `AMReX/src/build.sh` already branches on them. No thorn-side changes are needed — only
  the optionlist.
- `--offload-arch=gfxNNN` is the current spelling (ROCm ≳ 5.7). Older examples (e.g.
  `simfactory/mdb/optionlists/frontier.cfg`) use `--amdgpu-target=`. Check `hipcc --help`.
- Get the exact arch from `rocminfo | grep -A5 gfx`, not from the card name
  (MI210 = `gfx90a`, MI300 = `gfx942`).

Worked optionlist (single-GPU workstation, no system MPI):

```text
CC  = hipcc --offload-arch=gfx90a
CXX = hipcc --offload-arch=gfx90a
LD  = hipcc --offload-arch=gfx90a
F90 = gfortran

CXXFLAGS = -g -std=c++17 -Wno-unused-command-line-argument -Wno-pass-failed
LDFLAGS  = -fgpu-rdc --hip-link
LIBS     = stdc++fs gfortran hiprand rocrand

SYS_INC_DIRS = /opt/rocm/include
LIBDIRS      = /opt/rocm/lib /usr/lib/gcc/x86_64-linux-gnu/11

OPENMP = no                  # must match how AMReX itself was built

AMREX_DIR        = <install prefix>
AMREX_ENABLE_HIP = yes
AMREX_AMD_ARCH   = gfx90a

MPI_DIR      = /opt/intel/oneapi/mpi/latest
MPI_INC_DIRS = /opt/intel/oneapi/mpi/latest/include
MPI_LIB_DIRS = /opt/intel/oneapi/mpi/latest/lib/release /opt/intel/oneapi/mpi/latest/lib
MPI_LIBS     = mpicxx mpifort mpi rt pthread dl
```

Two link-time traps specific to this path:

- `ld.lld: unable to find library -lgfortran` / unresolved `_gfortran_*` — the final link
  goes through clang, which does not search gcc's private lib dir, and some distros ship
  the unversioned `libgfortran.so` symlink only there. Add `gfortran` to `LIBS` and that
  directory to `LIBDIRS`.
- Unresolved `hiprandCreateGenerator` etc. — AMReX's HIP backend calls hipRAND directly.
  Add `hiprand rocrand` to `LIBS`.

---

## Building AMReX outside Cactus

Legitimate and often easier: point `AMREX_DIR` at an install and `detect.sh`'s `find_lib`
picks it up, skipping `build.sh` entirely.

```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=hipcc \
  -DAMReX_GPU_BACKEND=HIP -DAMReX_CUDA=OFF -DAMReX_AMD_ARCH=gfx90a \
  -DAMReX_MPI=ON -DMPI_HOME=<prefix> -DAMReX_OMP=OFF \
  -DAMReX_PARTICLES=ON -DAMReX_ASSERTIONS=ON -DAMReX_FORTRAN=OFF \
  -DCMAKE_INSTALL_PREFIX=<prefix>
```

CMake's "legacy wrapper `hipcc` ... use amdclang++" warning is non-fatal and matches what
Cactus's own `build.sh` does. Note that with `AMREX_DIR` set, `AMREX_ENABLE_HIP` and
`AMREX_AMD_ARCH` become purely informational — they are only read inside the *bundled*
`build.sh`.

---

## Scoping a ThornList to just the GPU driver

When the goal is "get CarpetX/AMReX running on the GPU" rather than a physics stack:

- CarpetX itself only `REQUIRES AMReX IOUtil MPI yaml_cpp zlib`. ADIOS2, openPMD_api,
  Silo and CUDA are all `OPTIONAL`.
- Most CarpetX thorns (`BoxInBox`, `Derivs`, `TestNorms`, …) only `REQUIRES Loop`
  (sometimes `Arith`).
- `CarpetX/Algo` pulls in Boost; `CarpetX/PDESolvers` (and hence `PoissonX`) pulls in
  PETSc. Skip those three unless needed.

Find what the tests need rather than guessing:

```bash
find -L arrangements/CarpetX -path '*/test/*.par' -exec cat {} \; \
  | perl -0777 -ne 'while (/ActiveThorns\s*=\s*"([^"]*)"/gs){print "$1\n"}' \
  | tr -s ' \t\n' '\n' | sort -u
```

---

## AMReX startup: the unconditional per-thread RNG init

Every GPU build pays this once, whether or not anything uses random numbers — CarpetX
never calls `amrex::Random`.

`amrex::Initialize` calls `InitRandom` unconditionally (`Src/Base/AMReX.cpp:683`; skipped
only on the `init_minimal` path, which CarpetX does not take — `CarpetX/src/driver.cxx:1975`
calls the full `Initialize`, exactly once, matched by one `Finalize` at `:2053`). On a GPU
build `InitRandom` calls `ResizeRandomSeed` (`Src/Base/AMReX_Random.cpp:38`), which
allocates one RNG state per concurrent GPU thread slot and launches a single `ParallelFor`
to seed them:

```cpp
const int N = Gpu::Device::maxBlocksPerLaunch() * AMREX_GPU_MAX_THREADS;
gpu_rand_state = static_cast<randState_t*>(The_Arena()->alloc(N*sizeof(randState_t)));
amrex::ParallelFor(N, [=] AMREX_GPU_DEVICE (int idx) noexcept {
    ULong seqstart = static_cast<ULong>(idx) + 10 * static_cast<ULong>(idx);
    AMREX_HIP_OR_CUDA( hiprand_init(gpu_seed, seqstart, 0, &gpu_rand_state_local[idx]);,
                        curand_init(gpu_seed, seqstart, 0, &gpu_rand_state_local[idx]); )
});
```

`AMREX_GPU_MAX_THREADS` cancels between this and `max_blocks_per_launch`
(`AMReX_GpuDevice.cpp:598`), leaving:

```
N = 4 * numSMs * maxThreadsPerSM
```

| GPU | states | `curandState_t` @ 48 B |
|---|---|---|
| V100 (80 SM x 2048) | 655,360 | ~31 MB |
| A100 (108 SM x 2048) | 884,736 | ~42 MB |

`randState_t` is `curandState_t`, i.e. **XORWOW** (`AMReX_RandomEngine.H:49`), and every
thread gets a different subsequence (`11*idx`), so every state pays a skipahead. That is
why a profile shows **`__curand_matvec_inplace`** — cuRAND's GF(2) matrix-vector product,
the inner loop of XORWOW skipahead — and why this can be a visible chunk of startup.
Philox would not produce that symbol.

**It is one launch, not per kernel.** To confirm in your own profile rather than trusting
this note:

```bash
nsys stats --report cuda_gpu_kern_sum <report>.nsys-rep   # Instances should be 1
cuobjdump -sass exe/cactus_<cfg> | grep -c curand_matvec  # how many cubins contain it
```

There is no knob to skip it in AMReX 25.11. This is also why the HIP link needs
`hiprand rocrand` in `LIBS`: `AMReX_Random.cpp` references hipRAND unconditionally, so
the symbols are pulled into every binary regardless of use.

---

## Verifying the GPU is actually used

A clean build and link proves nothing. Check the run's own output — AMReX prints a
memory summary at shutdown:

```
Total GPU global memory (MB) spread across MPI: [65520 ... 65520]
Free  GPU global memory (MB) spread across MPI: [16010 ... 16010]
```

A figure matching the card's real HBM capacity is good evidence the GPU backend
initialized, independent of what `rocm-smi`/`nvidia-smi` busy-% shows for a short run.
