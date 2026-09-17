# Layout — where everything lives

Root of the tree = `$CCTK_HOME` = the directory containing the top-level `Makefile`.

```
Cactus/                          # CCTK_HOME
  Makefile  src/  lib/  doc/     # all SYMLINKS into repos/flesh
  bin/GetComponents              # → repos/CRL/GetComponents (Perl)
  manifest  → repos/manifest     # ET's canonical CRL thornlists
  simfactory → repos/simfactory2
  par → repos/einsteinexamples/par

  repos/<name>/                  # REAL git checkouts, one per source repo, lowercase names
  arrangements/<Arrangement>/<Thorn>   # SYMLINKS into repos/*, canonical CamelCase names
  thornlists/*.th                # local copies of thornlists
  configs/<cfg>/                 # one build
  exe/cactus_<cfg>               # linked executables
  utils/Scripts/MakeThornList    # parfile → minimal ThornList
```

## The symlink layer (important)

`arrangements/CactusBase/Boundary` is a symlink to `../../repos/cactusbase/Boundary`.
The flesh build system only knows about `arrangements/`; GetComponents creates the
symlinks. Consequences:

- Editing under `arrangements/` edits the real git repo under `repos/`.
- Case differs: `repos/*` is lowercase, `arrangements/*` is CamelCase.
- Use `find -L arrangements ...` — plain `find` will not descend the symlinks.

## Inside `repos/flesh`

| Path | What |
|---|---|
| `src/main/`, `src/comm/`, `src/util/` | Flesh C sources (`ScheduleInterface.c`, `GroupsOnGH.c`, `RDWR.cc`, `CactusTimers.c`, …) |
| `src/include/cctk*.h` | The public CCTK API headers — the real signatures |
| `src/param.ccl` | The flesh's own parameters (`presync_mode`, `cctk_itlast`, `terminate`, …) |
| `src/piraha/pegs/*.peg` | **The CCL grammars.** Authoritative for what parses |
| `lib/sbin/CST` | The CST driver script (847 lines) |
| `lib/sbin/{interface,parameter}_parser.pl`, `ScheduleParser.pl`, `ConfigurationParser.pl` | CCL parsers (all Piraha/PEG based) |
| `lib/sbin/Create*Bindings.pl`, `rdwr.pl` | Binding generators |
| `lib/sbin/Piraha.pm` | The PEG engine |
| `lib/make/` | `make.configuration`, `make.thornlib`, `setup_configuration.pl`, `configure`, `configure.ac`, `known-architectures/` |
| `doc/` | UsersGuide, ReferenceManual, MaintGuide, FAQ, ReleaseNotes — see [doc-traps.md](doc-traps.md) |

## Inside `configs/<cfg>/`

| Path | What |
|---|---|
| `ThornList` | The compile list actually used (plain `Arrangement/Thorn` lines) |
| `config-info` | Recorded options + timestamps; `gmake <cfg>-configinfo` prints it |
| `config-data/` | autoconf output: `cctk_Config.h`, `make.config.defn`, `make.config.rules`, `make.thornlist` |
| `bindings/` | **All CST-generated code.** Subdirs `Functions Implementations Parameters Variables Schedule`, plus `bindings/include/` |
| `build/<Thorn>/` | Object files |
| `lib/libthorn_<Thorn>.a` | Per-thorn static libraries |
| `scratch/` | ExternalLibraries build trees, Fortran `.mod` files, `done/` stamps |
| `OptionList`, `SubmitScript`, `RunScript` | SimFactory's per-configuration copies (only created by `sim build`) |

`bindings/` is the single most useful place to look when the *generated* glue is
wrong: aliased-function link errors → `bindings/Functions`; schedule-ordering bugs →
`bindings/Schedule`; `DECLARE_CCTK_ARGUMENTS_CHECKED` surprises →
`bindings/include/<Thorn>/cctk_Arguments_Checked.h`.

## Thorn directory conventions

```
arrangements/<Arr>/<Thorn>/
  interface.ccl  param.ccl  schedule.ccl  [configuration.ccl]
  src/make.code.defn        # SRCS = ...   SUBDIRS = ...
  src/[make.code.deps]      # file-level build ordering; ExternalLibraries hook detect/build here
  src/*.c *.cc *.F90
  par/                      # example parameter files
  test/                     # testsuite parfiles + expected output
  doc/documentation.tex
```

Thorn names: unique case-insensitively, start with a letter, `[A-Za-z0-9_]`,
**≤ 27 characters**, `doc` is reserved. Dirs starting `#` or ending `~`/`.bak` are ignored.

## Environment variables

| Variable | Meaning |
|---|---|
| `CCTK_HOME` | Tree root |
| `CACTUS_CONFIGS_DIR` / `CONFIGS_DIR` | Relocate `configs/` (useful when short on disk) |
| `CACTUS_CONFIG_FILES`, `$HOME/.cactus/config` | User default build options |
| `PROMPT=no` | Required for non-interactive `gmake` — otherwise it stops to ask |
| `VERBOSE=yes` | Print full compiler command lines |
