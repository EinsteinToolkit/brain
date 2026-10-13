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

## Three different things all called a machine's files

| Thing | Where | Created by | Scope |
|---|---|---|---|
| Machine **template** | `mdb/machines/<name>.ini` + the optionlist/submitscript/runscript it names | You, by hand | The machine; shared by every configuration on it |
| Per-**configuration** copies | `configs/<cfg>/{OptionList,SubmitScript,RunScript}` (capitalized, no extension) | `sim build`, on every build | What SimFactory reads at run/submit time for *this* configuration |
| Per-**simulation** copies | `<simdir>/SIMFACTORY/run/{SubmitScript,RunScript}` | `sim create*`, recording the path as `Properties.submitscript` (`lib/simrestart.py`) | What `submit()` actually reads for *this* simulation, including later restarts. Still holds its `@TOKENS@`; they are substituted into `<restartdir>/SIMFACTORY/` at submit time |

A change to `mdb/` therefore has to walk three levels before it takes effect, and **nothing
warns you at any of them**:

```
mdb/<name>.sub  --sim build-->  configs/<cfg>/SubmitScript  --sim create*-->  <simdir>/SIMFACTORY/run/SubmitScript  --sim submit-->  <restartdir>/SIMFACTORY/SubmitScript
```

Edit the MDB and resubmit an existing simulation and you get the old behaviour silently.
Rebuild (or `cp` the file into `configs/<cfg>/`) to fix the *configuration*; an
already-created simulation keeps its own copy, so that one needs a new simulation or an
edit to the copy in `<simdir>/SIMFACTORY/run/`. Diff the levels whenever an MDB change
appears to have been ignored.

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

## Heterogeneous clusters — one machine entry per partition

On many clusters each partition is a different machine: different CPU, core count and
memory. A single entry can be stretched with `--queue`, `--ppn`, `--num-threads` and the
generic `--mdbkey KEY VALUE` on every submit, but it cannot vary the **optionlist**,
which is baked into the configuration at build time. Give each partition its own entry
and its own optionlist.

An optionlist carrying the build host's ISA (`-mavx512f` and friends) will SIGILL on a
partition with older or AMD CPUs, so that partition needs a separate build as well as a
separate entry.

**Measure the hardware on the partition you will run on, not on the head node.**
`sim setup`/`setup-silent` shell out to `lscpu` on whatever host you run them from and
write `ppn`, `max-num-threads` and `num-threads` from `Socket(s) × Core(s) per socket`
(`lib/simdt.py`). Run from the login node, those describe the login node. `lscpu` reports
no memory at all, so `memory` is never auto-generated — take it from `free -m`,
`/proc/meminfo`, or the scheduler (`scontrol show node <n>` on Slurm).

### Does `aliaspattern` matter inside a job?

Usually not, and it is worth knowing why before debugging the wrong thing. 34 of the 37
shipped submit templates end by calling

```
@SIMFACTORY@ run @SIMULATION_NAME@ ... --machine=@MACHINE@ ...
```

`@MACHINE@` is substituted at `create` time from the machine resolved **on the submitting
host**, and `GetMachineName()` returns a `--machine` option immediately without ever
consulting `hostname` or `aliaspattern` (`lib/simlib.py`). So a job launched from one of
those templates does not re-resolve the machine, and a pattern that matches only the head
node will not break it. (`db.sub`, `db-sing-nv.sub` and `qbd.sub` omit the flag; on those
it does re-resolve.)

`aliaspattern` *is* consulted every time you run `sim` by hand on a compute node — an
interactive `srun`/`salloc` shell, or building inside a job — where it fails like this:

```
head node:         Current machine: rostam
inside the queue:  Warning: Unknown machine name medusa00.example.edu
                   Current machine: None
```

Make the pattern cover the compute nodes anyway, keeping entries distinguishable (by
disjoint patterns, or by the `sourcebasedir` tiebreak described under *Machine
resolution* above). On Slurm, check it where it has to work:

```bash
srun -p <partition> -N1 -n1 --pty ./simfactory/bin/sim whoami
```

---

## `allocation` is required, and a placeholder can be a silent no-op

`allocation` is one of three keys `GetLocalEnvironment()` requires, alongside `user` and
`sourcebasedir`; a missing one is `fatal: machine <name> is missing a required key`
(`lib/simlib.py`). You cannot remove it — only change where it comes from.

`sim setup-silent` writes `allocation = NO_ALLOCATION` into the **`[default]` section** of
`etc/defs.local.ini` (`lib/dt/defaults-silent.ini`), and `[default]` keys propagate into
every machine entry that lacks them. That is why deleting `allocation` from an `.ini`
appears to work. Many shipped entries hardcode the same placeholder.

Where the entry's submit script also has `#SBATCH --account=@ALLOCATION@`, the placeholder
reaches Slurm. On a cluster where accounting is configured but not enforced, Slurm
**ignores the unknown account and charges the user's default association** — the job runs
and the entry looks correct. Per the Slurm documentation the identical line is a submit
failure (`Invalid account or account/partition combination specified`) wherever
`AccountingStorageEnforce=associations` is set, so a directive that does nothing at one
site breaks the entry at another.

Check what the job charged rather than that it ran:

```bash
sacct -j <jobid> -o JobID,Account,State,ExitCode
```

On a cluster with no accounting, remove the `--account` line from the machine's submit
script; leave the key alone. Sites that do need an account set `allocation` in
`etc/defs.local.ini` or pass `--allocation`, which requires the line to be present.

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
> for `Illegal instruction` / `Caught signal`, check that expected output files were
> actually produced, and check `sacct -j <jobid>` if the entry names an allocation.
> On a cluster whose partitions differ, see
> [Heterogeneous clusters](#heterogeneous-clusters--one-machine-entry-per-partition).
