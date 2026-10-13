#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check that every tracked source file is in a Bazel rule its linter visits.

The lint aspects in //bazel/tools:aspects.bzl only see files declared in
specific rule kinds. A file outside those rules is never linted, and no
aspect can report it. This check compares `git ls-files` against
`bazel query` and fails on files that are not covered and not listed as
known offenders. It also fails on known offenders that are covered by now,
so the list can only shrink.

Run it from the repository root:
    bazel run //packages/cmk-repo-checks:bazel_lint_coverage
"""

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

KNOWN_OFFENDERS_FILE: Final = Path(
    "packages/cmk-repo-checks/bazel_lint_coverage_known_offenders.txt"
)

# doc/treasures/ holds unmaintained examples.
EXCLUDED_PREFIXES: Final = ("doc/treasures/",)


def _tag_pattern(tag: str) -> str:
    # attr() matches against the string form of the list, e.g. "[foo, no-lint]".
    return f'"[\\[ ]{tag}[,\\]]"'


def _rules_of_kind(*kinds: str) -> str:
    # kind() matches unanchored, so "cc_binary" alone would also match
    # "_cc_binary_transitioned", which no aspect visits.
    return f'kind("^({"|".join(kinds)}) rule$", //...)'


def _linted_sources(targets: str, skip_tags: Sequence[str] = ()) -> str:
    """Source files in srcs or hdrs of the targets, also through a filegroup in srcs.

    Mirrors should_visit() in aspect_rules_lint, which skips "no-lint" targets.
    """
    skipped = " + ".join(
        f"attr(tags, {_tag_pattern(tag)}, //...)" for tag in ("no-lint", *skip_tags)
    )
    return (
        f"let t = {targets} except ({skipped}) in "
        "let s = labels(srcs, $t) + labels(hdrs, $t) in "
        'kind("source file", $s + labels(srcs, kind("^filegroup rule$", $s)))'
    )


@dataclass(frozen=True)
class FileClass:
    name: str
    extensions: tuple[str, ...]
    covering_query: str
    # Shown next to an offender: where the file has to go.
    target_hint: str
    excluded_prefixes: tuple[str, ...] = ()


def _linted_by_rule_kinds(
    name: str,
    extensions: tuple[str, ...],
    kinds: Sequence[str],
    skip_tags: Sequence[str] = (),
    excluded_prefixes: tuple[str, ...] = (),
) -> FileClass:
    return FileClass(
        name=name,
        extensions=extensions,
        covering_query=_linted_sources(_rules_of_kind(*kinds), skip_tags),
        target_hint=f"{', '.join(kinds[:-1])} or {kinds[-1]}",
        excluded_prefixes=excluded_prefixes,
    )


# shellcheck supports sh, bash, dash and ksh, but not zsh.
SHELL_SHEBANG: Final = re.compile(rb"^#!\s*(\S*/)?(env\s+(-\S+\s+)*)?(ba|da|k)?sh(\s|$)")

# Files with a shell shebang belong here, too, unless another class claims
# their extension.
SHELL: Final = _linted_by_rule_kinds("shell", (".sh",), ("sh_binary", "sh_library", "sh_test"))

# The rule kinds and tags mirror the aspects in bazel/tools/aspects.bzl and
# their defaults in aspect_rules_lint.
FILE_CLASSES: Final = (
    SHELL,
    FileClass(
        name="powershell",
        extensions=(".ps1",),
        covering_query=_linted_sources(
            "attr(tags, "
            f"{_tag_pattern('lint-with-psscriptanalyzer')}, "
            'kind("^filegroup rule$", //...))'
        ),
        target_hint="filegroup tagged lint-with-psscriptanalyzer",
    ),
    _linted_by_rule_kinds(
        "rust",
        (".rs",),
        ("rust_binary", "rust_library", "rust_shared_library", "rust_test"),
        skip_tags=("noclippy",),
    ),
    _linted_by_rule_kinds(
        "c/c++",
        (".c", ".cc", ".h"),
        ("cc_binary", "cc_library", "cc_test"),
        # MSBuild builds the Windows agent.
        excluded_prefixes=("agents/wnx/",),
    ),
    FileClass(
        # Most .js files outside an eslint rule kind are vendored bundles, which
        # must not be linted. Being in any target is enough here.
        name="javascript",
        extensions=(".js", ".cjs"),
        covering_query='kind("source file", deps(//..., 1))',
        target_hint="any target",
    ),
)


class QueryError(Exception):
    pass


def needs_first_line(path: str) -> bool:
    return not any(path.endswith(fc.extensions) for fc in FILE_CLASSES)


def classify(path: str, first_line: bytes) -> FileClass | None:
    if path.startswith(EXCLUDED_PREFIXES):
        return None
    file_class = next((fc for fc in FILE_CLASSES if path.endswith(fc.extensions)), None)
    if file_class is None and SHELL_SHEBANG.match(first_line):
        file_class = SHELL
    if file_class is None or path.startswith(file_class.excluded_prefixes):
        return None
    return file_class


def label_to_path(label: str) -> str | None:
    if not label.startswith("//"):
        return None
    package, _, name = label[2:].partition(":")
    return f"{package}/{name}" if package else name


def parse_known_offenders(text: str) -> set[str]:
    return {line for raw in text.splitlines() if (line := raw.split("#", 1)[0].strip())}


@dataclass(frozen=True)
class Result:
    new_offenders: Mapping[str, Sequence[str]]
    stale_known_offenders: Sequence[str]
    offenders: Mapping[str, Sequence[str]]


def evaluate(
    candidates: Mapping[str, FileClass],
    covered: Mapping[str, set[str]],
    known_offenders: set[str],
) -> Result:
    """Compare the candidate files with the covered files of their class.

    `covered` maps a file class name to the repository paths that are in a
    rule kind its linter visits.
    """
    offenders: dict[str, list[str]] = {}
    for path, file_class in sorted(candidates.items()):
        if path not in covered[file_class.name]:
            offenders.setdefault(file_class.name, []).append(path)
    all_offenders = {p for paths in offenders.values() for p in paths}
    new = {
        name: new_paths
        for name, paths in offenders.items()
        if (new_paths := [p for p in paths if p not in known_offenders])
    }
    return Result(
        new_offenders=new,
        stale_known_offenders=sorted(known_offenders - all_offenders),
        offenders=offenders,
    )


def format_report(result: Result) -> str:
    lines = []
    if result.new_offenders:
        count = sum(len(paths) for paths in result.new_offenders.values())
        lines.append(
            f"Found {count} source file(s) outside the Bazel rules their linter visits."
            " Add them to a matching target (see bazel/tools/aspects.bzl):"
        )
        hints = {fc.name: fc.target_hint for fc in FILE_CLASSES}
        lines.extend(
            f" -- {name}: {path} -> {hints[name]}"
            for name, paths in result.new_offenders.items()
            for path in paths
        )
    if result.stale_known_offenders:
        lines.append(
            f"Found {len(result.stale_known_offenders)} known offender(s) that are covered"
            f" or gone now. Remove them from {KNOWN_OFFENDERS_FILE}:"
        )
        lines.extend(f" -- {path}" for path in result.stale_known_offenders)
    if not lines:
        known = sum(len(paths) for paths in result.offenders.values())
        lines.append(f"Bazel lint coverage: no new offenders ({known} known offenders left).")
    return "\n".join(lines)


def _tracked_files(repo_root: Path) -> Iterable[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z", ":(exclude,attr:rules-lint-ignored=true)"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout
    for path in output.decode().split("\0"):
        full_path = repo_root / path
        if path and full_path.is_file() and not full_path.is_symlink():
            yield path


def _first_line(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.readline(256)


def _candidates(repo_root: Path) -> dict[str, FileClass]:
    candidates = {}
    for path in _tracked_files(repo_root):
        first_line = _first_line(repo_root / path) if needs_first_line(path) else b""
        if file_class := classify(path, first_line):
            candidates[path] = file_class
    return candidates


def _query(repo_root: Path, expression: str) -> set[str]:
    process = subprocess.run(
        ["bazel", "query", expression, "--output=label"],
        check=False,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise QueryError(
            f"bazel query failed with exit code {process.returncode}:\n"
            f"{expression}\n{process.stderr}"
        )
    paths = {p for label in process.stdout.splitlines() if (p := label_to_path(label))}
    if not paths:
        raise QueryError(f"bazel query returned no files from the main repository:\n{expression}")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that every tracked source file is in a Bazel rule its linter visits."
    )
    parser.add_argument(
        "--print-offenders",
        action="store_true",
        help="print all current offenders in the known-offenders file format and exit",
    )
    args = parser.parse_args(argv)

    repo_root = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    candidates = _candidates(repo_root)
    try:
        covered = {fc.name: _query(repo_root, fc.covering_query) for fc in FILE_CLASSES}
    except QueryError as e:
        sys.stdout.write(f"Bazel lint coverage: {e}\n")
        return 2
    known_offenders = parse_known_offenders(
        (repo_root / KNOWN_OFFENDERS_FILE).read_text(encoding="utf-8")
    )

    result = evaluate(candidates, covered, known_offenders)

    if args.print_offenders:
        for name, paths in result.offenders.items():
            sys.stdout.write(f"# {name}\n" + "".join(f"{p}\n" for p in paths))
        return 0

    sys.stdout.write(format_report(result) + "\n")
    return 1 if result.new_offenders or result.stale_known_offenders else 0


if __name__ == "__main__":
    sys.exit(main())
