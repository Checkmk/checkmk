# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""`bazel run //:lint -- --delta`: lints the targets of the changed files."""

import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import NotRequired, TypedDict

from bazel_delta.errors import DeltaError
from bazel_delta.files import (
    delta_files,
    existing_files,
    find_base_branch,
    run_captured_in,
    RunCaptured,
)
from bazel_delta.summary import (
    changed_files,
    dirty_file_hashes,
    echo,
    note,
    print_changed_files,
    print_summary,
)

# Runs `bazel query` on an expression with an --output format and returns its stdout.
type Query = Callable[[str, str], str]

# Reads the first line of a workspace file, empty if it cannot be read.
type ReadFirstLine = Callable[[str], str]

# Runs a command in the workspace with its output on the terminal, returns its exit code.
type Call = Callable[[Sequence[str]], int]

# Runs a command in the workspace, returns its exit code and its stdout and stderr together.
type CallCaptured = Callable[[Sequence[str]], tuple[int, str]]

# The summary's languages with their linters: those of `bazel lint` in the order
# of .aspect/cli/config.yaml, then buildifier.
PYTHON = "Python (ruff, bandit, astrein, ...)"
SHELL = "Shell (shellcheck)"
JAVASCRIPT = "JavaScript/TypeScript (eslint)"
CSS = "CSS (stylelint)"
RUST = "Rust (clippy)"
C_CPP = "C/C++ (clang-tidy)"
GROOVY = "Groovy (groovy-lint)"
POWERSHELL = "PowerShell (PSScriptAnalyzer)"
STARLARK = "Starlark (buildifier)"
LANGUAGES = (PYTHON, C_CPP, GROOVY, RUST, JAVASCRIPT, SHELL, CSS, POWERSHELL, STARLARK)

_LANGUAGE_PATTERNS = (
    (PYTHON, ("*.py", "*.pyi")),
    (SHELL, ("*.sh", "*.bash")),
    (JAVASCRIPT, ("*.js", "*.cjs", "*.mjs", "*.jsx", "*.ts", "*.tsx", "*.vue")),
    (CSS, ("*.css", "*.scss")),
    (RUST, ("*.rs",)),
    (C_CPP, ("*.c", "*.cc", "*.cpp", "*.h", "*.hpp")),
    (GROOVY, ("*.groovy", "Jenkinsfile")),
    (POWERSHELL, ("*.ps1", "*.psm1")),
)

# The rule kinds and filegroup tags whose srcs the linters of each language lint,
# and the tags that skip a target besides no-lint, as bazel/tools/aspects.bzl
# sets them or rules_lint and bazel/tools/lint_*.bzl default them. If they drift
# apart, only the summary's counts are off. FILE_CLASSES in
# packages/cmk-repo-checks/cmk/repo_checks/bazel_lint_coverage.py mirrors them too.
_LINTED_RULES = (
    (
        PYTHON,
        ("py_binary", "py_library", "py_test"),
        (
            "python",
            "lint-with-ruff",
            "lint-with-astrein",
            "lint-with-py-import-cycles",
            "lint-with-license-header",
        ),
        (),
    ),
    (C_CPP, ("cc_binary", "cc_library", "_cc_binary_transitioned"), (), ()),
    (GROOVY, (), ("groovy", "lint-with-groovy"), ()),
    (
        RUST,
        ("rust_binary", "rust_library", "rust_shared_library", "rust_test"),
        (),
        ("noclippy",),
    ),
    (JAVASCRIPT, ("js_library", "ts_project", "ts_project_rule", "js_run_binary"), (), ()),
    (SHELL, ("sh_binary", "sh_library", "sh_test"), (), ()),
    (CSS, ("css_library",), ("stylelint",), ()),
    (POWERSHELL, (), ("lint-with-psscriptanalyzer",), ()),
)

# shellcheck takes sh, bash, dash and ksh, also run through env
_SHELL_SHEBANG = re.compile(r"^#!\s*(\S*/)?(env\s+(-\S+\s+)*)?(ba|da|k)?sh(\s|$)")

_NO_TARGET = re.compile(r"^ERROR: Skipping '.*': no such target '")


def query_errors(stderr: str) -> str:
    """The errors of a `bazel query --keep_going` that exited with 3, other than
    the skipped files that are no target, such as a package that fails to load."""
    return "\n".join(
        line
        for line in stderr.splitlines()
        if line.startswith("ERROR: ") and not _NO_TARGET.match(line)
    )


def query_in(workspace: Path) -> Query:
    def query(expression: str, output: str) -> str:
        # A query file, as the expression lists every changed file. With
        # --keep_going, exit code 3 means it left out the files that are no target,
        # or the packages that fail to load.
        with tempfile.NamedTemporaryFile("w", suffix=".query") as query_file:
            query_file.write(expression)
            query_file.flush()
            result = subprocess.run(
                [
                    "bazel",
                    "query",
                    "--keep_going",
                    f"--output={output}",
                    f"--query_file={query_file.name}",
                ],
                check=False,
                cwd=workspace,
                capture_output=True,
                text=True,
            )
        if result.returncode not in (0, 3):
            raise DeltaError(f"bazel query failed:\n{result.stderr}")
        if result.returncode == 3 and (errors := query_errors(result.stderr)):
            raise DeltaError(f"bazel query failed:\n{errors}")
        return result.stdout

    return query


@dataclass(frozen=True)
class OwningRule:
    kind: str
    tags: frozenset[str]


@dataclass(frozen=True)
class OwningTargets:
    targets: list[str]
    """The targets that list any of the files in their srcs or hdrs, sorted."""
    rules: dict[str, list[OwningRule]]
    """The files those targets list, each with the kinds and tags of the targets listing it."""


def _label_path(label: str) -> str:
    package, name = label.removeprefix("//").split(":", 1)
    return f"{package}/{name}" if package else name


# The parts of a rule in `bazel query --output=streamed_jsonproto` that are read here
class _Attribute(TypedDict):
    name: str
    stringListValue: NotRequired[list[str]]


class _Rule(TypedDict):
    name: str
    ruleClass: str
    attribute: NotRequired[list[_Attribute]]


def _string_lists(rule: _Rule, *names: str) -> list[str]:
    return [
        value
        for attribute in rule.get("attribute", [])
        if attribute["name"] in names
        for value in attribute.get("stringListValue", [])
    ]


def _listed_files(rule: _Rule) -> list[str]:
    """The srcs and hdrs of the rule. clang-tidy reports findings in the hdrs of
    the target it lints."""
    return _string_lists(rule, "srcs", "hdrs")


def _rules(streamed_jsonproto: str) -> list[_Rule]:
    """The rules of a `bazel query --output=streamed_jsonproto`."""
    return [
        rule
        for line in streamed_jsonproto.splitlines()
        if (rule := json.loads(line).get("rule")) is not None
    ]


# rules_py's py_binary and py_test add <name>.venv and <name>.pytest_paths next to
# themselves, which also list their srcs. Linting the py_binary or py_test covers those.
_RULES_PY_HELPERS = frozenset({"_py_venv_binary", "pytest_paths"})


def owning_targets(query: Query, files: Sequence[str]) -> OwningTargets:
    """The targets in the files' packages that list them in their srcs or hdrs,
    also through a filegroup in srcs, as rules_lint lints the files of those
    too. Files in no package are left out, and so are rules_py's helper targets."""
    if not files:
        return OwningTargets([], {})
    # Without escapes for non-ASCII characters, which bazel query does not decode
    file_set = " ".join(json.dumps(file, ensure_ascii=False) for file in files)
    labels = set(query(f"set({file_set})", "label").splitlines())
    if not labels:
        return OwningTargets([], {})
    owners: dict[str, OwningRule] = {}
    owner_names: dict[str, set[str]] = {}

    def own(rule: _Rule, owned: set[str]) -> None:
        if rule["ruleClass"] in _RULES_PY_HELPERS:
            return
        owners[rule["name"]] = OwningRule(rule["ruleClass"], frozenset(_string_lists(rule, "tags")))
        for label in owned:
            owner_names.setdefault(label, set()).add(rule["name"])

    label_set = " ".join(json.dumps(label, ensure_ascii=False) for label in sorted(labels))
    filegroups: dict[str, set[str]] = {}
    for rule in _rules(query(f"same_pkg_direct_rdeps(set({label_set}))", "streamed_jsonproto")):
        if owned := labels.intersection(_listed_files(rule)):
            own(rule, owned)
            if rule["ruleClass"] == "filegroup":
                filegroups[rule["name"]] = owned
    if filegroups:
        filegroup_set = " ".join(
            json.dumps(label, ensure_ascii=False) for label in sorted(filegroups)
        )
        for rule in _rules(
            query(f"same_pkg_direct_rdeps(set({filegroup_set}))", "streamed_jsonproto")
        ):
            for filegroup in filegroups.keys() & set(_string_lists(rule, "srcs")):
                own(rule, filegroups[filegroup])
    return OwningTargets(
        sorted(owners),
        {
            _label_path(label): [owners[name] for name in sorted(names)]
            for label, names in owner_names.items()
        },
    )


def linted_language(rules: Sequence[OwningRule]) -> str | None:
    """The language whose linters lint a file listed by the rules, None if no
    linter does. As in rules_lint, rules tagged no-lint are left out and the
    tags count for filegroups only."""
    for language, kinds, filegroup_tags, skip_tags in _LINTED_RULES:
        for rule in rules:
            if "no-lint" in rule.tags or rule.tags & set(skip_tags):
                continue
            if rule.kind in kinds or (rule.kind == "filegroup" and rule.tags & set(filegroup_tags)):
                return language
    return None


def language_by_name(file: str, read_first_line: ReadFirstLine) -> str | None:
    """The language a linter would take a file in no target for, None if none.
    Files without an extension count as shell scripts by their shebang."""
    name = Path(file).name
    for language, patterns in _LANGUAGE_PATTERNS:
        if any(fnmatchcase(name, pattern) for pattern in patterns):
            return language
    if "." not in name and _SHELL_SHEBANG.match(read_first_line(file)):
        return SHELL
    return None


def summary_rows(
    files: Sequence[str],
    owning: OwningTargets,
    starlark_files: Sequence[str],
    read_first_line: ReadFirstLine,
) -> list[tuple[str, int]]:
    """How many of the files each linter takes, how many of their languages no
    target lists, how many of their languages only targets list that no linter
    visits and how many no linter takes."""
    counts = Counter(
        language for rules in owning.rules.values() if (language := linted_language(rules))
    )
    if starlark_files:
        counts[STARLARK] = len(starlark_files)
    rows = [(f"{language}:", counts[language]) for language in LANGUAGES if counts[language]]
    # `bazel lint` sees files through the targets only, so it misses the files of
    # its languages that no target lists
    no_target = sum(
        1
        for file in files
        if file not in owning.rules
        and file not in starlark_files
        and language_by_name(file, read_first_line)
    )
    if no_target:
        rows.append(("Not linted (no Bazel target):", no_target))
    # Such targets can still reach a linter through a target of another package,
    # which only a query of the whole repo would find
    not_visited = sum(
        1
        for file, rules in owning.rules.items()
        if not linted_language(rules)
        and file not in starlark_files
        and language_by_name(file, read_first_line)
    )
    if not_visited:
        rows.append(("Not linted (no linted target lists it):", not_visited))
    if skipped := len(files) - counts.total() - no_target - not_visited:
        rows.append(("Skipped (no linter):", skipped))
    return rows


def bazel_lint_command(targets: Sequence[str], fix: bool, bazel_flags: Sequence[str]) -> list[str]:
    """Within `bazel run`, `bazel` is the plain Bazel that bazelisk puts first on
    PATH, which lacks the lint command of the Aspect CLI. bazelisk starts the
    Aspect CLI as configured in .bazeliskrc. As with `bazel lint //...`, the
    targets that the edition or platform rules out are skipped, not failed on.
    Like CI, the check mode asks for no fixes, which would hide findings."""
    return [
        "bazelisk",
        "lint",
        "--skip_incompatible_explicit_targets",
        "--fix" if fix else "--fixes=false",
        *bazel_flags,
        *targets,
    ]


@dataclass(frozen=True)
class Buildifier:
    """buildifier with the options and files of //:buildifier(.check), see
    bazel/tools/starlark_files.bzl."""

    binary: Path
    config: Path
    excluded: Sequence[str]
    names: Sequence[str]

    def covers(self, file: str) -> bool:
        if any(fnmatchcase(file, pattern) for pattern in self.excluded):
            return False
        return any(fnmatchcase(Path(file).name, pattern) for pattern in self.names)

    def command(self, files: Sequence[str], fix: bool) -> list[str]:
        """buildifier's lint checks with the options of //:buildifier(.check).
        Fixing lint findings implies fixing the layout, buildifier refuses
        -lint=fix otherwise."""
        modes = ["-lint=fix", "-mode=fix"] if fix else ["-lint=warn", "-mode=check"]
        return [str(self.binary), *modes, f"-config={self.config}", *files]


def lint_findings(returncode: int, buildifier_output: str) -> str:
    """buildifier's check output without the layout findings, which are the
    concern of //:format.check. buildifier exits with 4 for both; any other
    failure counts as a finding, even without output."""
    if returncode not in (0, 4):
        return buildifier_output.strip() or f"buildifier failed with exit code {returncode}"
    return "\n".join(
        line for line in buildifier_output.splitlines() if not line.endswith(" # reformat")
    )


@dataclass(frozen=True)
class Workspace:
    """How lint_delta reaches the workspace: its git, bazel, linters and files."""

    run: RunCaptured
    query: Query
    call: Call
    call_captured: CallCaptured
    which: Callable[[str], str | None]
    is_file: Callable[[str], bool]
    read_first_line: ReadFirstLine


def workspace_in(path: Path) -> Workspace:
    def call(command: Sequence[str]) -> int:
        return subprocess.run(command, check=False, cwd=path).returncode

    def call_captured(command: Sequence[str]) -> tuple[int, str]:
        result = subprocess.run(
            command,
            check=False,
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return result.returncode, result.stdout

    def is_file(file: str) -> bool:
        return (path / file).is_file()

    def read_first_line(file: str) -> str:
        try:
            with (path / file).open(errors="replace") as f:
                return f.readline()
        except OSError:
            return ""

    return Workspace(
        run=run_captured_in(path),
        query=query_in(path),
        call=call,
        call_captured=call_captured,
        which=shutil.which,
        is_file=is_file,
        read_first_line=read_first_line,
    )


def _bazel_lint(
    workspace: Workspace, targets: Sequence[str], fix: bool, bazel_flags: Sequence[str]
) -> bool:
    """Runs `bazel lint` on the targets, returns whether it found nothing left."""
    if not targets:
        return True
    if not workspace.which("bazelisk"):
        raise DeltaError(
            "bazelisk not found, which runs 'bazel lint' from within 'bazel run'.\n"
            "See buildscripts/infrastructure/build-nodes/scripts/install-bazel.sh."
        )
    return workspace.call(bazel_lint_command(targets, fix, bazel_flags)) == 0


def _lint_starlark(
    workspace: Workspace, buildifier: Buildifier, files: Sequence[str], fix: bool
) -> bool:
    """Runs buildifier on the files, returns whether it found nothing left. The
    fix leaves what it cannot fix unreported, so the check runs after it."""
    if not files:
        return True
    if fix and workspace.call(buildifier.command(files, fix=True)) != 0:
        return False
    returncode, output = workspace.call_captured(buildifier.command(files, fix=False))
    if findings := lint_findings(returncode, output):
        echo(findings)
        return False
    return True


def outcome(fix: bool, clean: bool) -> str | None:
    """The last line of the summary; in fix mode, the fixed files come first."""
    if fix:
        return None if clean else "Lint findings above, which could not be fixed automatically."
    return "No lint findings." if clean else "Lint findings above."


def _print_nothing_to_lint(files: Sequence[str], base_branch: str) -> None:
    echo(f"None of the {len(files)} file(s) changed compared to {base_branch} is linted:")
    echo("no Bazel target lists them in its srcs and none of them is a Starlark file.")


def _run_linters(
    workspace: Workspace,
    buildifier: Buildifier,
    targets: Sequence[str],
    starlark_files: Sequence[str],
    fix: bool,
    bazel_flags: Sequence[str],
) -> bool:
    """Runs `bazel lint` and buildifier, returns whether neither found anything left."""
    return all(
        [
            _bazel_lint(workspace, targets, fix, bazel_flags),
            _lint_starlark(workspace, buildifier, starlark_files, fix),
        ]
    )


def _print_lint_summary(
    base_branch: str,
    files: Sequence[str],
    rows: Sequence[tuple[str, int]],
    fixed: Sequence[str],
    fix: bool,
    clean: bool,
) -> None:
    title = "Linting" if fix else "Linting (check only)"
    print_summary(f"{title}: {len(files)} file(s) changed compared to {base_branch}", rows)
    if fix:
        print_changed_files(
            fixed, "Fixed", "Nothing needed fixing." if clean else "No file changed."
        )
    if message := outcome(fix, clean):
        note(message)


def lint_delta(
    workspace: Workspace, buildifier: Buildifier, fix: bool, bazel_flags: Sequence[str]
) -> int:
    """Lints the targets of the changed files and prints a summary, returns the exit code.
    The Bazel flags go to `bazel lint`."""
    run = workspace.run

    # 1. Which files changed
    base_branch = find_base_branch(run)
    files = existing_files(delta_files(run, base_branch))
    if not files:
        echo(f"No files changed compared to {base_branch}.")
        return 0

    # 2. What lints them: `bazel lint` on their targets, buildifier on the Starlark files
    owning = owning_targets(workspace.query, files)
    starlark_files = [file for file in files if buildifier.covers(file)]
    if not owning.targets and not starlark_files:
        _print_nothing_to_lint(files, base_branch)
        return 0

    # 3. Lint, with the dirty files' hashes before, to tell which files the fix changed
    hashes_before = dirty_file_hashes(run, workspace.is_file) if fix else {}
    clean = _run_linters(workspace, buildifier, owning.targets, starlark_files, fix, bazel_flags)

    # 4. Summary
    rows = summary_rows(files, owning, starlark_files, workspace.read_first_line)
    fixed = changed_files(hashes_before, dirty_file_hashes(run, workspace.is_file)) if fix else []
    _print_lint_summary(base_branch, files, rows, fixed, fix, clean)
    return 0 if clean else 1
