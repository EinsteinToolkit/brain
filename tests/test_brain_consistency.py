#!/usr/bin/env python3
"""Consistency checks for the brain's own markdown.

The brain is navigated by following links out of index.md, so a broken link or a
topic file missing from the routing table silently costs a reader the file. These
checks guard that wiring.

Run:  python3 -I tests/test_brain_consistency.py
Exits non-zero and prints every failure; it never swallows an error.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Markdown files that are not brain topic files and so need no routing-table entry.
NOT_A_TOPIC = {"index.md", "README.md", "requirements.md", "notes.md"}

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def markdown_files():
    """Every tracked markdown file at the top level of the brain."""
    return sorted(p for p in ROOT.glob("*.md"))


def topic_files():
    return sorted(p for p in markdown_files() if p.name not in NOT_A_TOPIC)


def local_targets(path):
    """Link targets in `path` that point at something on disk, with any #anchor cut."""
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield target.split("#", 1)[0]


def check_links_resolve():
    """Every relative markdown link resolves to a file that exists."""
    failures = []
    for path in markdown_files() + [ROOT / "COPYING"]:
        if not path.exists() or path.suffix != ".md":
            continue
        for target in local_targets(path):
            if not target:
                continue
            if not (path.parent / target).exists():
                failures.append(f"{path.name}: link to missing file {target!r}")
    return failures


def check_every_topic_is_routed():
    """index.md links to every topic file, so no file is unreachable."""
    index = ROOT / "index.md"
    linked = {t for t in local_targets(index)}
    return [
        f"index.md: {p.name} exists but is not linked from the index"
        for p in topic_files()
        if p.name not in linked
    ]


def check_readme_lists_every_topic():
    """README.md's contents table names every topic file."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return [
        f"README.md: contents table does not mention {p.name}"
        for p in topic_files()
        if f"`{p.name}`" not in text
    ]


def check_no_tab_indentation():
    """The ET asks contributors not to commit tabs; hold the brain to it too."""
    failures = []
    for path in markdown_files():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "\t" in line:
                failures.append(f"{path.name}:{n}: contains a tab character")
    return failures


def check_inline_code_spans_balanced():
    """No inline `code` span is wrapped across a line break.

    Markdown does join those, but the rendered span then contains a newline, and the
    brain is read as plain text as often as it is rendered. Caught a real one.
    """
    failures = []
    for path in markdown_files():
        in_fence = False
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # Fences are often indented inside list items, so strip before matching.
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if line.count("`") % 2:
                failures.append(f"{path.name}:{n}: inline code span wraps the line")
    return failures


CHECKS = (
    check_links_resolve,
    check_every_topic_is_routed,
    check_readme_lists_every_topic,
    check_no_tab_indentation,
    check_inline_code_spans_balanced,
)


def main():
    failures = []
    for check in CHECKS:
        found = check()
        status = f"FAIL ({len(found)})" if found else "ok"
        print(f"{check.__name__:35s} {status}", flush=True)
        failures.extend(found)

    if failures:
        print(f"\n{len(failures)} problem(s):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"\nAll {len(CHECKS)} checks passed over {len(markdown_files())} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
