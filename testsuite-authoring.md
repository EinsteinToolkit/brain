# Writing a test case

How to *author* a Cactus testsuite test. For *running* one —
`sim create-run --testsuite`, `gmake <cfg>-testsuite`, `--select-tests` — see
[simfactory.md](simfactory.md) and [build-system.md](build-system.md).

A test case is a review gate: a new component is not accepted into the Einstein Toolkit
without one ([tickets-and-review.md](tickets-and-review.md)), and the project's own
review guidance argues that a new *feature* should be blocked until its tests exist.

Authority: `repos/flesh/lib/sbin/RunTestUtils.pl` (parsing, comparison, tolerances) and
`RunTest.pl`. Everything about tolerances and `test.ccl` below was read out of that file.

---

## What a Cactus test is

A **regression** test, and nothing more: a parameter file plus the output it produced
when it was known-good. The harness reruns the parfile and compares numbers in the ASCII
output against the stored copy. It is explicitly *not* a convergence test or a physics
correctness check — those matter, but a regression test is a bad way to do them.

The corollary is liberating: **the output does not have to be physically meaningful.**
A coarser grid, fewer timesteps, a smaller domain, lower order, no mesh refinement — all
fine, as long as the same code paths execute and nothing produces a NaN.

## Layout

```
arrangements/<Arr>/<Thorn>/test/
    mytest.par            # the parameter file
    mytest/               # expected output — SAME NAME as the parfile, minus .par
        mytest::phi.norms.asc
        ...
    test.ccl              # optional per-thorn / per-test settings
```

`RunTestUtils.pl` finds tests by globbing `*.par` inside `test/` and then requiring the
stem to resolve: either a directory of that name, or an archive of it —
`<stem>.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz`, `.tar.xz`, `.txz`, unpacked on the
fly. A `.par` with neither prints *"Parameter file ... but no output directory"* and is
skipped, so a committed parfile whose expected output never got added is silently not a
test. The stem match is load-bearing either way.

A `config` file in `test/` is the **dead** predecessor of `test.ccl`: the harness only
prints a deprecation notice when it sees one and then parses `test.ccl` regardless. A
thorn carrying only a `config` file gets no settings at all — silently default
tolerances and default `NPROCS`.

Make the parfile write into exactly that directory:

```
IO::out_dir       = $parfile
IO::out_fileinfo  = "axis labels"
IO::parfile_write = "no"
```

`$parfile` expands to the parfile's basename with `.par` stripped —
`get_parfilename()` in `repos/flesh/src/piraha/Call.cc` — which is exactly what makes
the output directory name line up with what the harness looks for.

## Which files are compared

`FindFiles` walks both the stored expected-output directory and the directory the run
just produced, splitting what it finds in two:

- **Recognised** — the extension appears in the accumulated `EXTENSIONS` list. These are
  compared numerically.
- **Unrecognised** — everything else. Not compared, and reported in the summary as
  clutter.

Only `*.par`, `CVS`, `.svn`, emacs lock files (`.#*`) and editor backups (`*~`) are
skipped outright. A generic dotfile is **not** — it lands in the unrecognised list and
is reported as clutter.

`EXTENSIONS` is **global, not per-thorn**: every `test.ccl` in the build contributes to
one shared list. In practice the I/O thorns register the common ones — `CarpetIOASCII`
and `IOASCII` register `asc`, `CarpetX` registers `tsv`, others add `gp`, `xg`, `xl`,
`tl`. So `.asc` output just works. If your thorn invents an extension, you must declare
it yourself or the file is silently never compared:

```
EXTENSIONS myext
```

## Tolerances

Defaults are `ABSTOL = 1e-12` and `RELTOL = 1e-12`. Override them per thorn, per test,
or per file-name pattern:

```
# thorn-wide
RELTOL 1e-10

# per test, which is the usual form
TEST FLRW_fileread_exact_test
{
  RELTOL 1e-3
}

TEST kasner
{
  NPROCS 2
}
```

`ABSTOL`/`RELTOL`/`POSTPROC` take an optional second argument: a regex matched
case-insensitively against the *file name*, defaulting to `.*`. Keep those patterns
disjoint — if a data file matches more than one non-default pattern, `RunTestUtils.pl`
does not pick one, it **dies**. That check fires at four places independently
(thorn-wide `ABSTOL`, thorn-wide `RELTOL`, per-test `ABSTOL`, per-test `RELTOL`), plus a
fifth for `POSTPROC`. Per-test patterns are every bit as fatal as thorn-wide ones.

Say why in a comment. A loosened tolerance without a stated reason is indistinguishable
from a silently broken test, and reviewers will ask.

Loosening is normal, not exceptional: of the 104 `test.ccl` files in a full checkout, 70
set a tolerance and 53 set `NPROCS`. If your test needs `RELTOL 1e-10` because it
compares finite differences, you are in the majority, not making an excuse.

## Process count

With MPI present, tests run on **2 processes** by default (1 without MPI); the
environment variable `CCTK_TESTSUITE_RUN_PROCESSORS` overrides globally, and `NPROCS` in
`test.ccl` overrides per thorn or per test.

A test is only portable across process counts if its output is. Carpet's ASCII output
carries the domain decomposition, including blank-line placement, so output produced on
two processes will not match a one-process run. Either pin `NPROCS`, or make the output
decomposition-independent:

```
CarpetIOASCII::compact_format      = yes
CarpetIOASCII::output_ghost_points = no
```

## Designing the thing

Rules of thumb from the project's `Adding a test case` guidance. The two wiki pages give
*different* numbers — `Adding a test case` says under one to two minutes and a few
hundred MB, while `How to Review a new component` says under 10 s. The reviewer's page
is the one you will be held to, so the limits below are its numbers.

- **Few thorns, few variables, few files.** Over-outputting is the standard beginner
  mistake. Extra variables do not catch more regressions — they only help localise one
  after the fact, which is not a test case's job — and they bloat every clone of the
  thorn forever.
- **Norms plus 1-D ASCII.** Norms miss single-point changes; 1-D ASCII misses off-axis
  changes. The combination catches both.
- **Avoid round-off-dominated reductions.** `sum` over N points carries N times the
  round-off and will fail spuriously. Use `count`, `minimum`, `maximum`, `average`,
  `norm1`, `norm2`, `norm_inf`. Avoid `product`, `sum`, `sum_abs`, `sum_squared`,
  `sum_abs_squared`.
- **Nothing run-dependent.** No dates, no timing, no host names, no echo of the parfile.
  Screen/info output is ignored by the comparison, so leave a little of it on for
  debugging.
- **Avoid checkpoints, binary I/O and file-reading** where you can. They are testable —
  `CarpetIOHDF5/test/` does it — but they are an advanced case.
- **Under 10 s per test, under 2 min for the whole component, under 1 GB of memory**
  ("preferably much less"). Note that the 1 GB is *memory*, not file size. There are
  hundreds of tests in a full run and they go on every release-critical machine.
- **Data files small.** Under 1 MB if a test genuinely needs input data. For scale: the
  largest data file in the whole toolkit is ~11 MB and that is considered a problem. A
  reader thorn's test input does not have to be a solution to anything — a single
  low-resolution domain with a few non-zero, spatially varying modes is enough.

If a test needs an input file, reference it by a path relative to the **test run
directory**, which is `TEST/<config>/<Thorn>/` under the Cactus root (`TESTS_DIR`
defaults to `$CCTK_HOME/TEST`; `RunTestUtils.pl` chdirs there before launching). That is
three levels down, which is exactly why the canonical example begins with `../../../`:

```
IO::filereader_ID_dir = "../../../arrangements/Carpet/CarpetIOHDF5/test/input_initial_data"
```

Such a parfile will **not** work if you `cd` into `test/` and run it by hand, and it
will not work from the Cactus root either. That is expected, not a bug — count the
levels from `TEST/<config>/<Thorn>/`, not from anywhere else.

## Procedure

1. Start from a working parfile that exercises the feature.
2. Strip thorns, variables and output until only the feature remains. Shrink the domain,
   coarsen the grid, cut the timesteps, drop refinement and multi-block, lower the order.
3. Set the three `IO::` parameters above; switch reductions to the safe list.
4. Comment the parfile — say what is being tested.
5. Run it at the process count you intend to pin. Then inspect the output directory:
   no `.par` file, no binary files, no large files, not many files.
6. Move the parfile and the output directory into `test/`, add `test.ccl` if you need a
   non-default `NPROCS` or tolerance, and run the test through the harness. It must pass.
7. Run it at another process count too. If it fails, either pin `NPROCS` or make the
   output decomposition-independent.
8. Commit the expected output along with the code. A patch without its test data is not
   reviewable.

## When a test fails

Test failure is the normal signal that something regressed, so take it literally before
loosening anything.

- **Widening a tolerance to silence a failure is different from setting one when you
  write the test.** Choosing `RELTOL 1e-10` up front because the test compares finite
  differences is routine. Raising it afterwards because the numbers moved hides
  exactly the regression the test existed to catch. Do the second only once you know
  *why* the numbers moved and have decided the move is legitimate.
- Bisect against older checkouts to find the commit that changed the numbers, keeping
  several built executables around — you will rerun many times.
- A test case deliberately outputs too little to debug with. Add output to a *scratch
  copy* of the parfile, not to the committed test.
- A failure on one machine only is usually a compiler or external-library problem rather
  than a code change; [troubleshooting.md](troubleshooting.md) covers those.
- Changing the expected output is sometimes correct — when the change in behaviour is
  intended. Say so explicitly in the ticket and the commit, because regenerating
  expected data is exactly how a real regression gets laundered into the baseline.
