# SimFactory 2

`simfactory/` → `repos/simfactory2`. Entry point `./simfactory/bin/sim` (a bash wrapper
that execs `sim.py` under python3). It is Einstein-Toolkit tooling, **not** part of the
flesh, and is not covered by the flesh UsersGuide.

SimFactory ultimately just invokes the flesh Makefile. Once `configs/<cfg>/` exists,
debugging a failed `sim build` is identical to debugging `gmake <cfg>` —
see [build-system.md](build-system.md).

---

## Common commands

```bash
./simfactory/bin/sim setup-silent                      # create etc/defs.local.ini
./simfactory/bin/sim whoami [--machine=<name>]         # which machine did it resolve to
./simfactory/bin/sim print-mdb-entry <name>            # dump all resolved fields
./simfactory/bin/sim build -jN --configuration <cfg> --thornlist <CST.th> --optionlist <file.cfg>
./simfactory/bin/sim create-run <simname> --parfile=<par> --procs=N
./simfactory/bin/sim create-submit <simname> --parfile=<par> --procs=N
./simfactory/bin/sim create-run <simname> --testsuite --select-tests <Arrangement>
```

`--thornlist` takes a **CST** list, never a CRL file.

`--select-tests` accepts `all`, an `Arrangement`, an `Arrangement/Thorn`, or a specific
`<test>.par` name (matching rules in `copyTestsuiteData`, `simfactory/lib/simrestart.py`).

---

## The MDB

| Path | Role |
|---|---|
| `simfactory/mdb/machines/<nick>.ini` | hostname/aliaspattern, which optionlist/submitscript/runscript, job limits |
| `simfactory/mdb/optionlists/*.cfg` | Cactus optionlists |
| `simfactory/mdb/submitscripts/*.sub` | Batch or local submit templates |
| `simfactory/mdb/runscripts/*.run` | How the binary is launched |
| `simfactory/etc/defs.local.ini` | Local defaults — **must** come from `sim setup-silent` |

`generic.sub` / `generic.run` implement the no-scheduler pattern and can usually be
reused unchanged.

**Never delete anything under `mdb/` to fix a problem — only add files.** If
`generic.sub does not exist`, restore it; do not wipe the MDB.

In `defs.local.ini` the key `machine = ...` is only valid under `[default]`. Putting it
under a config section gives `Error: found invalid keys machine in section <name>`. The
fix is to delete the file and re-run `sim setup-silent`, not to hand-edit it.

---

## Two different things both called a machine's files

| Thing | Where | Created by | Scope |
|---|---|---|---|
| Machine **template** | `mdb/machines/<name>.ini` + the optionlist/submitscript/runscript it names | You, by hand | The machine; shared by every configuration on it |
| Per-**configuration** copies | `configs/<cfg>/{OptionList,SubmitScript,RunScript}` (capitalized, no extension) | `sim build`, on every build | What SimFactory reads at run/submit time for *this* configuration |

### If you configured with `gmake` instead of `sim build`

The per-configuration copies never get created, and `sim create-run`/`run`/`submit` fail
one missing piece at a time. Populate them by hand:

```bash
cp simfactory/mdb/runscripts/<name>.run    configs/<cfg>/RunScript && chmod +x configs/<cfg>/RunScript
cp simfactory/mdb/submitscripts/<name>.sub configs/<cfg>/SubmitScript      # needed for submit
cp simfactory/mdb/optionlists/<name>.cfg   configs/<cfg>/OptionList
gmake <cfg>-utils PROMPT=no                                                # creates exe/<cfg>/
```

These are **raw, unsubstituted copies** — `@PLACEHOLDER@` tokens are filled in later,
per restart (`sim build`'s own logic is just `shutil.copy`, in
`simfactory/lib/sim-build.py`).

`exe/<cfg>/` holds thorn **utility programs** (`UTIL_DIR = $(EXEDIR)/$(CONFIG_NAME)`).
A normal `gmake <cfg>` does not build it; `copyTestsuiteData` does a `copytree` on it and
raises `FileNotFoundError` if it is absent. It may end up nearly empty — it just has to
exist. A bare `gmake <cfg>-testsuite` does not need it.

> **Do not "fix" this by running a plain `sim build`** on a hand-configured tree.
> With no `configs/<cfg>/OptionList`, `hasStoredOptions` is false, so `hasOutdatedConfig`
> is unconditionally true *and* `removeConfig` becomes true — which runs
> `<cfg>-realclean` and throws away every object file.

---

## Machine resolution — `GetMachineName()` in `simfactory/lib/simlib.py`

1. `--machine=<name>` on the command line wins outright. Use it to sanity-check a new
   `.ini` before fighting hostname detection.
2. `~/.hostname`, if it exists — its **contents** (not the real `hostname` output) become
   the string to match.
3. Otherwise the real `hostname` output.

The resulting string is matched against every machine's `hostname` (exact) or
`aliaspattern` (regex). If several match, SimFactory disambiguates by checking which
candidate's `sourcebasedir` is a path prefix of the Cactus checkout you are running from;
if not exactly one matches, it warns "Could not identify machine" and gives up.

Practical consequences:

- `~/.hostname` lives in `$HOME`. **On a shared/networked home it is the same file on
  every machine that mounts it**, and can silently break resolution everywhere. If
  `sim whoami` resolves to an unexpected machine, check this file first.
- Give every machine a distinct, correct `sourcebasedir` (the directory *containing* that
  machine's Cactus checkout). It is load-bearing, not cosmetic.
- You can exploit this deliberately: give two machines the same alias and let disjoint
  `sourcebasedir`s pick the right one based on which checkout you invoke `sim` from.
- A stale `~/.hostname` pointing at a machine whose `sourcebasedir` no longer exists makes
  resolution fail from a perfectly good checkout. Confirm with the user before deleting
  it — other machines may depend on it.

---

## Minimal `.ini` for a scheduler-less workstation

```ini
[omnia]
nickname        = omnia
name            = omnia
hostname        = omnia
aliaspattern    = ^omnia$
sourcebasedir   = /path/containing/the/Cactus/checkout

envsetup = <<HEREDOC
... machine-specific env: PATH, LD_LIBRARY_PATH, MPI vars.sh, fabric selection ...
HEREDOC

optionlist      = omnia-hip.cfg
submitscript    = generic.sub
runscript       = omnia.run
make            = make -j@MAKEJOBS@
makejobs        = 1

basedir         = /path/to/simulations
ppn             = 1
max-num-threads = 1
num-threads     = 1
nodes           = 1

# No queue: launch directly, track by PID, kill by process group.
submit          = exec nohup @SCRIPTFILE@ < /dev/null > @RUNDIR@/@SIMULATION_NAME@.out 2> @RUNDIR@/@SIMULATION_NAME@.err & echo $!
getstatus       = ps @JOB_ID@
stop            = pkill -g $(ps -o pgid= -p @JOB_ID@)
submitpattern   = (.*)
statuspattern   = "^ *@JOB_ID@ "
queuedpattern   = $^
runningpattern  = ^
holdingpattern  = $^
exechost        = echo localhost
exechostpattern = (.*)
```

(The real `envsetup` block uses `<<EOF` ... `EOF`; it is spelled `HEREDOC` above only so
this file can be pasted into a shell heredoc safely.)

For a Slurm machine, copy an existing cluster entry instead and adjust the partition,
`ppn`, `max-num-threads`, and the submit/status/stop commands.

### `envsetup` vs. a custom runscript — you often need both

`envsetup` is applied **only around commands SimFactory itself executes directly**
(build, configure, the testsuite-data rsync) — `simfactory/lib/simlib.py` wraps them as
`{ envsetup; } && { command; }`.

It is **not** present when a *generated* script runs. The per-restart `RunScript` is
written to `<restartdir>/SIMFACTORY/RunScript` and exec'd later, possibly via `nohup`,
as a plain shell script — outside SimFactory's Python process.

So if your machine needs `PATH`/`LD_LIBRARY_PATH`/fabric selection for the executable to
run at all, copy `generic.run` to `mdb/runscripts/<name>.run`, insert
`source /path/to/env-setup.sh` right after the shebang (before `set -e`), and point the
machine's `runscript` key at it.

This matters most for the test suite: `sim create-run --testsuite` does **not** invoke
`mpirun -np N exe parfile` per test. It sets `CCTK_TESTSUITE_RUN_COMMAND` to a snippet
that ends by invoking the prepared `RunScript`, and Cactus's `lib/sbin/RunTestUtils.pl`
uses that variable in place of its own default. Your runscript therefore runs for
**every single test** — rely on that rather than fighting it.

---

## Verification sequence for a new machine

```bash
./simfactory/bin/sim whoami --machine=<name>     # does the .ini parse?
./simfactory/bin/sim print-mdb-entry <name>      # are the resolved fields sane?
./simfactory/bin/sim whoami                      # does it resolve with no flag?
# populate configs/<cfg>/{OptionList,SubmitScript,RunScript} if built outside sim build
./simfactory/bin/sim create-run <simname> --testsuite --select-tests <Arrangement>
```

> A scheduler reporting success does not mean the run succeeded. Check the job's `.err`
> for `Illegal instruction` / `Caught signal`, and check that expected output files were
> actually produced. On a heterogeneous cluster, a binary compiled with the login node's
> ISA (`-mavx512f`, say) will SIGILL on a partition with older CPUs — pin the submit
> partition to CPUs matching the build host.
