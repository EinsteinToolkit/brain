# Build system

Requires **GNU make** (`gmake`, or `make` if it is GNU). The top-level `Makefile`
re-invokes itself via `$(MAKE)`, so plain `make` works.

---

## Two file formats both called "thornlist" — never confuse them

| Format | Looks like | Consumed by |
|---|---|---|
| **CRL / GetComponents** | `!CRL_VERSION`, `!DEFINE`, `!TARGET`, `!TYPE`, `!URL`, `!REPO_BRANCH`, `!REPO_PATH`, `!NAME`, `!CHECKOUT` directives, then `Arrangement/Thorn` lines | **Checkout only** (`bin/GetComponents`) |
| **CST / compile ThornList** | plain `Arrangement/Thorn` lines, `#comment`, `#DISABLED Arr/Thorn` | **Configure + compile** (`configs/<cfg>/ThornList`) |

The flesh's ThornList parser ignores `#`- and `!`-prefixed lines, so a CRL file often
*happens* to work as a ThornList — but only if every enabled component is also a
buildable thorn. Strip it deliberately rather than relying on that.

CRL gotchas:

- `!CHECKOUT` sparse-checkout paths are **not** "enabled for compile".
- A component may appear in `!CHECKOUT` **and** as `#DISABLED` (downloaded, not built).
  Listing it a third time as an enabled body line gives GetComponents
  `Duplicate checkouts`.
- Never enable both `ExternalLibraries/BLAS` and `ExternalLibraries/OpenBLAS`.

Refresh a checkout:
`bin/GetComponents --update --root=. thornlists/<list>.th`

---

## The pipeline

### 1. Configure

```bash
gmake <cfg>-config THORNLIST=/abs/path/compile.th options=/abs/path/optionlist.cfg PROMPT=no
```

1. `lib/make/setup_configuration.pl` creates `configs/<cfg>/{build,lib,scratch,config-data}`.
2. Runs the autoconf-generated `lib/make/configure`, driven by **`configure.ac`**
   (`AC_CONFIG_HEADERS([cctk_Config.h])`) — *not* `configure.in`/`config.h`, whatever
   `Makesystem.tex` says. `lib/make/known-architectures/<host_os>` is sourced twice,
   gated by `$CCTK_CONFIG_STAGE` = `preferred-compilers` then `misc`. Helper functions
   live in `CCTK_Functions.sh` (capital F).
3. Writes `config-data/{cctk_Config.h, make.config.defn, make.config.rules, make.config.deps}`.
4. Records `config-info`.

**Configuration names must not end in a reserved suffix** (`-build`, `-clean`, `-config`,
`-delete`, …).

`gmake <newcfg> options=... THORNLIST=... PROMPT=no` does configure *and* build in one
command: the `%::` catch-all in the top-level `Makefile` creates the configuration, then
builds it **only if `PROMPT=no`**. With the default `PROMPT=yes` it configures and stops,
printing `Use gmake <newcfg> to build the configuration` — which looks like a silent
failure if you expected an executable.

### 2. CST

`make.configuration:214` runs:

```
$(PERL) $(CCTK_HOME)/lib/sbin/CST -config_dir=$(CONFIG) -cctk_home=$(CCTK_HOME) -top=$(TOP) <ThornList>
```

`make.thornlist`'s dependency list (`make.configuration:211`) includes **every thorn's
four CCL files** (plus any `cakernel.ccl`, for Kranc/CaKernel thorns) and
`lib/make/force-rebuild`, so touching any CCL file — or that sentinel — retriggers the CST.

Three stages inside `lib/sbin/CST`:

1. **Parse** — `CreateThornList`, then `CreateConfigurationDatabase`,
   `create_interface_database`, `create_parameter_database`, `create_schedule_database`
   populate four Perl hashes. All four parsers are **PEG-based** on the shared
   `lib/sbin/Piraha.pm` with grammars in `src/piraha/pegs/`; parse results are cached in
   `$TOP/piraha` (cleared by the `cleandeps` target).
2. **Cross-check** — `ProcessConfiguration` (runs `configuration.ccl` scripts),
   `check_schedule_database`, `CheckImpParamConsistency`, `CheckCrossConsistency`
   (thorns sharing an implementation must agree on restricted-parameter defaults).
   Also `TestName` (thorn name rules) and `TopoSort`, which computes `THORN_LINKLIST`
   from inheritance + `PROVIDES`/`REQUIRES` capabilities + `REQUIRES THORNS`/`USES THORNS`.
3. **Generate** — `CreateImplementationBindings` → `CreateParameterBindings` →
   `CreateVariableBindings` → `CreateScheduleBindings` → `CreateFunctionBindings` →
   `GenerateArguments`, then `CreateConfigurationBindings`, `CreateThornsHeaders`
   (`bindings/include/{thornlist.h, cctk_DefineThorn.h}`, per-thorn `definethisthorn.h`),
   `BuildHeaders`, `CreateLogFile`, and finally `CreateMakeThornlist` →
   `config-data/make.thornlist` (variables `THORNS`, per-thorn `USESTHORNS_*`, link order).

`MaintGuide/CST.tex` is an empty stub; the above is reconstructed from the script.

**Force a CST rerun** after changing any CCL file or ThornList membership:

```bash
gmake <cfg>-rebuild                       # or
rm configs/<cfg>/config-data/make.thornlist && gmake <cfg>
```

### 3. Compile and link

Per thorn (`make.configuration` → `make.thornlib`):

1. `Checking status of thorn <Name>`
2. Use `src/Makefile` if present, else `lib/make/make.thornlib`.
3. Read `src/make.code.defn` (`SRCS`, `SUBDIRS`); subdirs recurse via `make.subdir`,
   with `make.pre` resetting `SRCS:=` and `make.post` prefixing the subdir name onto
   `CCTK_SRCS`.
4. Compile with flags from `config-data/make.config.defn` plus include dirs: thorn `src/`,
   `config-data`, flesh `src/include`, `bindings/include`, and the include/lib lines of
   every `USESTHORNS_<thorn>` dependency (via a generated
   `bindings/Configuration/Thorns/make.<Thorn>.defn`).
5. Archive to `configs/<cfg>/lib/libthorn_<Thorn>.a`.

Final link: flesh `datestamp.c` + all `libthorn_*.a` in CST link order + `GENERAL_LIBRARIES`
from configure. Executable is `exe/cactus_<cfg>` (or per `EXE`/`EXEDIR`).

A thorn rebuild is skipped when `make.checked` is up to date.

---

## Makefile targets

| Target | Meaning |
|---|---|
| `gmake help` | List configurations and options |
| `gmake <cfg>` | Configure if needed, then build |
| `gmake <cfg>-config` | Configure / reconfigure (`THORNLIST=`, `options=`) |
| `gmake <cfg>-reconfig` | Reconfigure with the **previous** options |
| `gmake <cfg>-rebuild` | Force CST + rebuild |
| `gmake <cfg>-build BUILDLIST="A B"` | Build only those thorns, no link |
| `gmake <cfg>-clean` | Delete objects and deps |
| `gmake <cfg>-realclean` | Almost-new; keeps `config-data` + `ThornList` |
| `gmake <cfg>-cleandeps` | Drop dependency + piraha caches (fixes stale/renamed includes) |
| `gmake <cfg>-delete` | Delete the whole `configs/<cfg>/` |
| `gmake distclean` | Delete all configurations |
| `gmake <cfg>-configinfo` | Print recorded options |
| `gmake <cfg>-thornlist` / `-editthorns` | Regenerate/edit `ThornList` (dangerous if you manage it by hand) |
| `gmake <cfg>-testsuite` | Run the test suite |
| `gmake <cfg>-utils` | Build thorn utility programs into `exe/<cfg>/` — **not** built by a normal `gmake <cfg>`, and required by SimFactory testsuite runs |
| `gmake <cfg>-ThornGuide`, `gmake ThornDoc`, `gmake ArrangementDoc`, `gmake UsersGuide` | Documentation |
| `gmake newthorn` | Skeleton thorn |

Knobs: `TJOBS=N` (parallel across thorns), `FJOBS=N` (parallel files within a thorn),
`VERBOSE=yes`, `PROMPT=no`, `OPTIMISE=no` (faster dev builds), `THORNLIST=`, `options=`.

> `nproc` can under-report on a cgroup-limited session (e.g. `1` on a 144-core box)
> while `/proc/cpuinfo` and `free -h` still show the whole machine. `nproc` is the
> authoritative number for `-j`/`TJOBS`/`FJOBS`. Under a tight budget, trim the
> ThornList instead of parallelizing harder.

---

## Clean vs. delete — do not confuse

| Command | Removes | Keeps |
|---|---|---|
| `<cfg>-clean` | objects, deps | `config-data`, `ThornList` |
| `<cfg>-realclean` | almost everything in the config | `config-data`, `ThornList` |
| `<cfg>-delete` | the entire `configs/<cfg>` | arrangements, flesh |
| `distclean` | all configurations | arrangements, flesh |

Never delete arrangement trees or `simfactory/mdb/*` to clear a compile error.

---

## Optionlists

Plain `KEY = value` text with `#` comments, passed as `options=`. Common keys:

| Key | Role |
|---|---|
| `CC`, `CXX`, `F90`, `LD` | Compilers and linker |
| `CFLAGS`, `CXXFLAGS`, `F90FLAGS`, `LDFLAGS`, `LIBS`, `LIBDIRS`, `SYS_INC_DIRS` | Flags, libs, dirs |
| `CPPFLAGS`, `FPPFLAGS` | Preprocessor flags (e.g. `-DSIMD_DISABLE`) |
| `DEBUG`, `OPTIMISE`, `PROFILE`, `OPENMP`, `WARN` | Build modes — **configure-time only** |
| `VECTORISE`, `VECTORISE_ALIGNED_ARRAYS`, `VECTORISE_INLINE` | Carpet's vectorisation — a different knob from CarpetX's `-DSIMD_DISABLE` |
| `<LIB>_DIR` (`HDF5_DIR`, `AMREX_DIR`, `MPI_DIR`, …) | ExternalLibraries detect roots; `BUILD` forces the bundled build |
| `DISABLE_INT16`, `DISABLE_REAL16` | Often required by CUDA stacks |
| `ac_cv_*` | autoconf cache variables — see below |

### How the build modes compose

`config-data/make.config.defn` ends with one block per mode:

```make
ifeq ($(strip $(CCTK_OPTIMISE_MODE)),yes)
  CPPFLAGS  += $(CPP_OPTIMISE_FLAGS)
  CFLAGS    += $(C_OPTIMISE_FLAGS)
  CXXFLAGS  += $(CXX_OPTIMISE_FLAGS)
  CUCCFLAGS += $(CUCC_OPTIMISE_FLAGS)
  ...
else
  CFLAGS    += $(C_NO_OPTIMISE_FLAGS)
```

The real command line is therefore the base `<LANG>FLAGS` plus one contribution per
enabled mode. Prefixes: `CPP_`, `FPP_`, `C_`, `CXX_`, `CUCC_`, `F77_`, `F90_`, `LD_`;
modes `DEBUG`, `OPTIMISE`/`NO_OPTIMISE`, `PROFILE`, `OPENMP`, `WARN`.

Two consequences:

- **Never put optimisation in the base `CFLAGS`/`CXXFLAGS`/`CUCCFLAGS`.** The DEBUG
  block runs *before* the OPTIMISE block, so a hardcoded `-O2` survives `DEBUG = yes`
  and beats the `-O0` that debug mode appends — the debug build is not a debug build.
  Put `-O2` in `*_OPTIMISE_FLAGS`; keep only language/ABI settings plus `-g` in the base
  flags.
- A `CUCC_` variant exists for every mode, so a CUDA optionlist can keep `CUCCFLAGS`
  free of optimisation too rather than baking it in.

Inspect what a configuration actually resolved to:
`grep -n '_MODE\|_FLAGS' configs/<cfg>/config-data/make.config.defn`, or build one file
with `gmake <cfg> SILENT=no` and read the command.

### The preprocessor passes are separate

Cactus preprocesses Fortran with FPP (`cpp -traditional`) as its own step before the
compiler runs, and `CPPFLAGS` is prepended to **every** compile.

- `-fopenmp` defines `_OPENMP` for the compile proper but **not** for the FPP pass.
  Without `FPP_OPENMP_FLAGS = -D_OPENMP`, every `#ifdef _OPENMP` block in a `.F90` is
  deleted before compilation — silently, with a successful build and working `!$omp`
  directives.
- Conversely, do not put a compiler-only flag in `CPP_OPENMP_FLAGS`. `CPPFLAGS` reaches
  the `$(CUCC)` compiles too, and a bare `-fopenmp` is fatal to nvcc unless `CXX` carries
  `--forward-unknown-to-host-compiler`. Put `-Xcompiler -fopenmp` in `CUCCFLAGS` instead.

### Linking

`configure` defaults `LD_OPENMP_FLAGS` from `CXX_OPENMP_FLAGS` **only when `LD` is
unset** (`lib/make/configure.ac`, search `LD_OPENMP_FLAGS`). An optionlist that sets
`LD` must set `LD_OPENMP_FLAGS` too, or the link fails on
`undefined reference to GOMP_parallel`.

`LIBS` and `LIBDIRS` are folded into `GENERAL_LIBRARIES`, which sits **last** on the link
line — which is why `LIBS` resolves symbols left undefined by the thorn archives. Each
`LIBDIRS` entry is expanded through both `LIBDIR_PREFIX` (`-L`) and `RUNDIR_PREFIX`
(`-Wl,-rpath,`), so listing a directory there also bakes it into the executable's
RUNPATH.

### autoconf cache variables

`setup_configuration.pl`'s `ParseOptionsFile` loads every `KEY = value` straight into
`%ENV`, so any `ac_cv_*` in the optionlist vetoes the corresponding configure probe.
Example: `ac_cv_prog_cc_c23 = no` stops configure selecting `-std=gnu23`, under which
`typedef int bool` in older thorn C no longer compiles.

**Editing the optionlist file does nothing to an existing configuration.** The file is
copied to `configs/<cfg>/OptionList` at configure time and never re-read. To apply a
change: `gmake <cfg>-config options=<file> THORNLIST=<file>`, or `gmake <cfg>-delete`
first.

---

## MakeThornList — parfile → minimal ThornList

```bash
export CCTK_HOME=/path/to/Cactus
$CCTK_HOME/utils/Scripts/MakeThornList -o my.th -m master.th my.par
```

Parses the parfile with `par.peg` → `ActiveThorns`, maps short names to
`Arrangement/Thorn`, then transitively closes over each thorn's `configuration.ccl`
`REQUIRES` / `REQUIRES THORNS` / `OPTIONAL` / `OPTIONAL_IFACTIVE`.

Caveats: it finds thorns present under `arrangements/` even if the master list omits
them, but **hard-errors** if a required thorn appears only as `#DISABLED`; and each
invocation costs ~2 minutes of fixed overhead (it scans every arrangement's
`configuration.ccl`). For one or two lookups it is faster to read the `REQUIRES` lines
by hand.

---

## Running

```bash
./exe/cactus_<cfg> <parfile> [flags]
```

Parfiles start with `ActiveThorns = "..."` then `thorn::parameter = value`. Useful flags:
`-O`/`--describe-all-parameters`, `-S`/`--print-schedule`, `-T`/`--list-thorns`,
`-L`/`-W`/`-E` (log/warn/error levels), `-r`/`-R` (redirect),
`--parameter-level=strict|normal|relaxed`.

In practice use `./simfactory/bin/sim create-run ...` — see [simfactory.md](simfactory.md).
