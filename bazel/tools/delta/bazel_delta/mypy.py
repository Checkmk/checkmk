# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""`bazel run //:mypy.check -- --delta`: type-checks what the changed files can affect."""

import json
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from bazel_delta.files import (
    delta_files,
    existing_files,
    FileStatus,
    find_base_branch,
    is_file_in,
    run_captured_in,
    run_on_terminal_in,
    RunCaptured,
    RunOnTerminal,
)
from bazel_delta.summary import echo, note, print_summary
from bazel_delta.targets import file_labels, owning_targets, OwningTargets, Query, query_in

# The files that affect every type check: mypy's settings, how it runs and the
# versions of mypy and the stubs. No target lists them, so the queries cannot
# tell which type checks they reach.
_GLOBAL_INPUTS = (
    "pyproject.toml",
    "mypy-gpl.toml",
    "bazel/tools/aspects.bzl",
    "bazel/tools/BUILD",
    "bazel/patches/rules_mypy*.patch",
    "bazel/rc/mypy.rc",
    "bazel/tools/mypy_wrapper.sh",
    "tests/typeshed/*",
    "MODULE.bazel",
    "MODULE.bazel.lock",
    "bazel/module/py.MODULE.bazel",
    "requirements.txt",
)


def global_inputs(files: Sequence[str]) -> list[str]:
    return [file for file in files if any(fnmatchcase(file, p) for p in _GLOBAL_INPUTS)]


def global_inputs_warning(files: Sequence[str]) -> str:
    return (
        f"{', '.join(files)} changed, which affects every type check, so this run cannot"
        " tell. Run 'bazel build --config=mypy //...'."
    )


def python_files(files: Sequence[str]) -> list[str]:
    return [file for file in files if file.endswith((".py", ".pyi"))]


def build_files(files: Sequence[str]) -> list[str]:
    """The BUILD files, whose deps decide what mypy sees of the other modules."""
    return [file for file in files if PurePosixPath(file).name in ("BUILD", "BUILD.bazel")]


def bzl_files(files: Sequence[str]) -> list[str]:
    """The .bzl files, whose macros can change the targets of the BUILD files that use them."""
    return [file for file in files if file.endswith(".bzl")]


def packages_loading(query: Query, bzl: Sequence[str]) -> list[str]:
    """The packages whose BUILD files load any of the .bzl files, also through
    other .bzl files. Needs a query with --universe_scope."""
    # rbuildfiles takes its files separated by commas, unlike set()
    file_list = ", ".join(json.dumps(file, ensure_ascii=False) for file in bzl)
    # //<package>:BUILD is the BUILD file of <package>
    return [
        label.removeprefix("//").rsplit(":", 1)[0]
        for label in query(f"rbuildfiles({file_list})", "label").splitlines()
    ]


def type_checked_files(owning: OwningTargets, checked: Sequence[str]) -> set[str]:
    """The files that at least one type-checked target lists: one that is built
    and not tagged no-mypy, the suppression tag of bazel/tools/aspects.bzl."""
    built = set(checked)
    return {
        file
        for file, rules in owning.rules.items()
        if any(rule.label in built and "no-mypy" not in rule.tags for rule in rules)
    }


def summary_rows(
    files: Sequence[str],
    python: Sequence[str],
    deleted: Sequence[str],
    build: Sequence[str],
    bzl: Sequence[str],
    global_changed: Sequence[str],
    owning: OwningTargets,
    type_checked: set[str],
) -> list[tuple[str, int]]:
    """How many of the Python files mypy checks, how many were deleted, how many
    BUILD and .bzl files changed, how many global inputs changed, how many Python
    files no type-checked target lists and how many files are skipped. The global
    inputs count in their own row only."""
    global_set = set(global_changed)
    build = [file for file in build if file not in global_set]
    bzl = [file for file in bzl if file not in global_set]
    rows = []
    if type_checked:
        rows.append(("Python (mypy):", len(type_checked)))
    if deleted:
        rows.append(("Deleted Python (users checked):", len(deleted)))
    if build:
        rows.append(("BUILD files (Python targets checked):", len(build)))
    if bzl:
        rows.append((".bzl files (Python targets of their users checked):", len(bzl)))
    if global_changed:
        rows.append(("Affect every type check:", len(global_changed)))
    if not_checked := len(owning.rules) - len(type_checked):
        rows.append(("Not checked (manual or no-mypy):", not_checked))
    # mypy runs through the targets, so it cannot see the files that none lists
    if no_target := len([f for f in python if f not in owning.rules and f not in global_set]):
        rows.append(("Not checked (no Bazel target):", no_target))
    if other := len(set(files) - set(python) - set(deleted) - set(build) - set(bzl) - global_set):
        rows.append(("Other files (users checked):", other))
    return rows


def package_of(file: str, is_file: Callable[[str], bool]) -> str:
    """The Bazel package a file belongs to, or belonged to before it was deleted:
    the closest directory above it with a BUILD file."""
    for directory in PurePosixPath(file).parents:
        package = "" if directory == PurePosixPath(".") else str(directory)
        if any(is_file(str(PurePosixPath(package, name))) for name in ("BUILD", "BUILD.bazel")):
            return package
    return ""


def python_targets_of_packages(query: Query, packages: Sequence[str]) -> list[str]:
    """All Python targets of the packages: those of a deleted file, as the ones
    that listed it are among them, and those of a changed or affected BUILD file."""
    package_set = " ".join(
        json.dumps(f"//{package}:all", ensure_ascii=False) for package in packages
    )
    return query(f'kind("^py_", set({package_set}))', "label").splitlines()


def checked_targets(query: Query, targets: Sequence[str]) -> list[str]:
    """The targets and all that depend on them, as a change can break the type
    checks of its users. Like CI's `bazel build ...`, it leaves out the targets
    tagged manual: building those, e.g. the .venv targets of py_test, beside their
    own target conflicts. Only rules, not the files they generate."""
    target_set = " ".join(json.dumps(target, ensure_ascii=False) for target in targets)
    return query(
        f"let r = kind(rule, rdeps(//..., set({target_set}))) in "
        f'$r except attr(tags, "\\bmanual\\b", $r)',
        "label",
    ).splitlines()


def nothing_to_check(targets_found: bool) -> str:
    """Why no target is left to type-check."""
    if not targets_found:
        return "No Bazel target holds or uses the changed files, nothing to type-check."
    return "Only targets tagged manual hold or use the changes, nothing to type-check."


def outcome(clean: bool) -> str:
    return "No type errors." if clean else "Type errors or build failures above."


def mypy_build_command(target_file: str, bazel_flags: Sequence[str]) -> list[str]:
    """As with `bazel build //...`, the targets that the edition or platform rules
    out are skipped, not failed on."""
    return [
        "bazel",
        "build",
        "--keep_going",
        "--config=mypy",
        "--skip_incompatible_explicit_targets",
        *bazel_flags,
        f"--target_pattern_file={target_file}",
    ]


@dataclass(frozen=True)
class MypyWorkspace:
    """How mypy_delta reaches the workspace: its git, bazel and files. The
    universe query has --universe_scope, which rbuildfiles needs."""

    run: RunCaptured
    query: Query
    universe_query: Query
    run_on_terminal: RunOnTerminal
    is_file: Callable[[str], bool]


def mypy_workspace_in(path: Path) -> MypyWorkspace:
    return MypyWorkspace(
        run=run_captured_in(path),
        query=query_in(path),
        universe_query=query_in(path, "--universe_scope=//...", "--order_output=no"),
        run_on_terminal=run_on_terminal_in(path),
        is_file=is_file_in(path),
    )


def _build_with_mypy(
    workspace: MypyWorkspace, targets: Sequence[str], bazel_flags: Sequence[str]
) -> bool:
    """Runs mypy through `bazel build --config=mypy`, returns whether it found no type errors."""
    # A target pattern file, as the targets can be thousands
    with tempfile.NamedTemporaryFile("w", suffix=".targets") as target_file:
        target_file.write("".join(f"{target}\n" for target in targets))
        target_file.flush()
        return workspace.run_on_terminal(mypy_build_command(target_file.name, bazel_flags)) == 0


def targets_to_check(
    files: Mapping[str, FileStatus],
    query: Query,
    universe_query: Query,
    is_file: Callable[[str], bool],
) -> list[str]:
    """The targets whose users mypy checks: the changed files that are targets,
    so that also the users of non-Python files are checked, e.g. of the sources of
    generated code, and the Python targets of the packages whose files were
    deleted, whose BUILD file changed or that load a changed .bzl file. The
    universe query has --universe_scope, which rbuildfiles needs."""
    existing = existing_files(files)
    deleted = [file for file, status in files.items() if status is FileStatus.DELETED]
    bzl = bzl_files(existing)
    packages = {package_of(file, is_file) for file in [*deleted, *build_files(list(files))]}
    if bzl:
        packages |= set(packages_loading(universe_query, bzl))
    return sorted(
        file_labels(query, existing)
        | set(python_targets_of_packages(query, sorted(packages)) if packages else [])
    )


def mypy_delta(workspace: MypyWorkspace, bazel_flags: Sequence[str]) -> int:
    """Type-checks the targets of the changed Python files and all that depend on
    them, prints a summary and returns the exit code. The Bazel flags go to
    `bazel build`."""
    run = workspace.run

    # 1. Which files changed
    base_branch = find_base_branch(run)
    files = delta_files(run, base_branch)
    if not files:
        echo(f"No files changed compared to {base_branch}.")
        return 0

    # 2. Which targets the changes reach: the changed files themselves and the
    # Python targets of the packages that deletions, BUILD and .bzl files change
    query = workspace.query
    targets = targets_to_check(files, query, workspace.universe_query, workspace.is_file)
    python = python_files(existing_files(files))
    deleted = python_files([file for file, status in files.items() if status is FileStatus.DELETED])
    build = build_files(list(files))
    bzl = bzl_files(existing_files(files))
    owning = owning_targets(query, python)
    title = f"Type-checking: {len(files)} file(s) changed compared to {base_branch}"
    global_changed = global_inputs(list(files))

    # 3. Type-check them and all targets that depend on them
    checked = checked_targets(query, targets) if targets else []
    rows = summary_rows(
        list(files),
        python,
        deleted,
        build,
        bzl,
        global_changed,
        owning,
        type_checked_files(owning, checked),
    )
    if not checked:
        print_summary(title, rows)
        note(nothing_to_check(bool(targets)))
        if global_changed:
            note(global_inputs_warning(global_changed))
            return 1
        return 0
    clean = _build_with_mypy(workspace, checked, bazel_flags)

    # 4. Summary
    print_summary(title, rows)
    note(
        f"Built {len(checked)} target(s) with the mypy aspect: those holding the changes"
        " and all that depend on them."
    )
    note(outcome(clean))
    if global_changed:
        note(global_inputs_warning(global_changed))
        return 1
    return 0 if clean else 1
