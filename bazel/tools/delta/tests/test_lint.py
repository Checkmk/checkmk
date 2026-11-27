# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
from bazel_delta.__main__ import _parse_args
from bazel_delta.lint import (
    bazel_lint_command,
    Buildifier,
    C_CPP,
    GROOVY,
    JAVASCRIPT,
    language_by_name,
    lint_delta,
    lint_findings,
    linted_language,
    outcome,
    owning_targets,
    OwningRule,
    OwningTargets,
    PYTHON,
    Query,
    query_errors,
    RUST,
    SHELL,
    STARLARK,
    summary_rows,
    Workspace,
)


def _rule(
    name: str,
    srcs: list[str],
    hdrs: list[str] | None = None,
    kind: str = "py_library",
    tags: list[str] | None = None,
) -> str:
    attribute = [{"name": "srcs", "type": "LABEL_LIST", "stringListValue": srcs}]
    if hdrs is not None:
        attribute.append({"name": "hdrs", "type": "LABEL_LIST", "stringListValue": hdrs})
    if tags is not None:
        attribute.append({"name": "tags", "type": "STRING_LIST", "stringListValue": tags})
    return json.dumps(
        {"type": "RULE", "rule": {"name": name, "ruleClass": kind, "attribute": attribute}}
    )


def _fake_query(outputs: Mapping[tuple[str, str], str]) -> Query:
    """Returns the output given for an expression and output format, nothing otherwise."""

    def query(expression: str, output: str) -> str:
        return outputs.get((expression, output), "")

    return query


def test_targets_listing_a_file_in_their_srcs_own_it() -> None:
    query = _fake_query(
        {
            ('set("cmk/a.py" "cmk/b.py")', "label"): "//cmk:a.py\n//cmk:b.py\n",
            (
                'same_pkg_direct_rdeps(set("//cmk:a.py" "//cmk:b.py"))',
                "streamed_jsonproto",
            ): "\n".join(
                [
                    _rule("//cmk:lib", ["//cmk:a.py", "//cmk:other.py"]),
                    _rule("//cmk:data_only", []),
                    _rule("//cmk:test", ["//cmk:b.py"], kind="py_test", tags=["slow"]),
                ]
            ),
        }
    )
    owning = owning_targets(query, ["cmk/a.py", "cmk/b.py"])
    assert owning.targets == ["//cmk:lib", "//cmk:test"]
    assert owning.rules == {
        "cmk/a.py": [OwningRule("py_library", frozenset())],
        "cmk/b.py": [OwningRule("py_test", frozenset({"slow"}))],
    }


def test_files_in_a_filegroup_are_owned_by_its_users_in_the_package() -> None:
    query = _fake_query(
        {
            ('set("tests/testlib/out.py")', "label"): "//tests/testlib:out.py\n",
            (
                'same_pkg_direct_rdeps(set("//tests/testlib:out.py"))',
                "streamed_jsonproto",
            ): _rule("//tests/testlib:srcs", ["//tests/testlib:out.py"], kind="filegroup"),
            (
                'same_pkg_direct_rdeps(set("//tests/testlib:srcs"))',
                "streamed_jsonproto",
            ): "\n".join(
                [
                    _rule("//tests/testlib:testlib", ["//tests/testlib:srcs"]),
                    _rule("//tests/testlib:data", [], kind="filegroup"),
                ]
            ),
        }
    )
    owning = owning_targets(query, ["tests/testlib/out.py"])
    assert owning.targets == ["//tests/testlib:srcs", "//tests/testlib:testlib"]
    assert owning.rules == {
        "tests/testlib/out.py": [
            OwningRule("filegroup", frozenset()),
            OwningRule("py_library", frozenset()),
        ]
    }


def test_files_of_the_root_package_are_repo_paths() -> None:
    query = _fake_query(
        {
            ('set("setup.py")', "label"): "//:setup.py\n",
            ('same_pkg_direct_rdeps(set("//:setup.py"))', "streamed_jsonproto"): _rule(
                "//:setup", ["//:setup.py"]
            ),
        }
    )
    assert set(owning_targets(query, ["setup.py"]).rules) == {"setup.py"}


def test_rules_py_helpers_listing_the_srcs_of_a_test_own_nothing() -> None:
    query = _fake_query(
        {
            ('set("cmk/test_a.py")', "label"): "//cmk:test_a.py\n",
            (
                'same_pkg_direct_rdeps(set("//cmk:test_a.py"))',
                "streamed_jsonproto",
            ): "\n".join(
                [
                    _rule("//cmk:test", ["//cmk:test_a.py"], kind="py_test"),
                    _rule("//cmk:test.pytest_paths", ["//cmk:test_a.py"], kind="pytest_paths"),
                    _rule(
                        "//cmk:test.venv",
                        ["//cmk:test_a.py"],
                        kind="_py_venv_binary",
                        tags=["manual"],
                    ),
                ]
            ),
        }
    )

    owning = owning_targets(query, ["cmk/test_a.py"])

    assert owning.targets == ["//cmk:test"]
    assert owning.rules == {"cmk/test_a.py": [OwningRule("py_test", frozenset())]}


def test_files_in_no_package_have_no_targets() -> None:
    owning = owning_targets(_fake_query({}), ["notes.txt"])
    assert owning.targets == []
    assert owning.rules == {}


_BUILDIFIER = Buildifier(
    Path("/bin/buildifier"),
    Path("/cfg.json"),
    excluded=["*/build/*", "bazel/thirdparty/*"],
    names=["*.bzl", "BUILD", "BUILD.bazel", "*.BUILD"],
)


@pytest.mark.parametrize(
    "file",
    ["BUILD", "cmk/BUILD.bazel", "bazel/rules/x.bzl", "omd/foo.BUILD"],
)
def test_buildifier_covers_files_by_name(file: str) -> None:
    assert _BUILDIFIER.covers(file)


@pytest.mark.parametrize(
    "file",
    ["cmk/a.py", "bazel/thirdparty/x.bzl", "omd/build/BUILD"],
)
def test_buildifier_skips_other_and_excluded_files(file: str) -> None:
    assert not _BUILDIFIER.covers(file)


@pytest.mark.parametrize(
    ("file", "language"),
    [
        ("cmk/a.py", PYTHON),
        ("cmk/a.pyi", PYTHON),
        ("scripts/run.sh", SHELL),
        ("web/App.jsx", JAVASCRIPT),
        ("src/x.hpp", C_CPP),
        ("buildscripts/Jenkinsfile", GROOVY),
        ("README.md", None),
    ],
)
def test_language_by_name(file: str, language: str | None) -> None:
    assert language_by_name(file, lambda _file: "") == language


@pytest.mark.parametrize(
    ("first_line", "language"),
    [
        ("#!/bin/bash", SHELL),
        ("#!/usr/bin/env sh", SHELL),
        ("#!/bin/dash", SHELL),
        ("#!/usr/bin/env -S ksh -e", SHELL),
        ("#!/bin/zsh", None),
        ("#!/usr/bin/env python3", None),
    ],
)
def test_files_without_extension_by_shebang(first_line: str, language: str | None) -> None:
    assert language_by_name("bin/tool", lambda _file: first_line) == language


@pytest.mark.parametrize(
    ("rules", "language"),
    [
        ([OwningRule("sh_library", frozenset())], SHELL),
        ([OwningRule("filegroup", frozenset({"python"}))], PYTHON),
        ([OwningRule("filegroup", frozenset())], None),
        ([OwningRule("genrule", frozenset())], None),
        ([OwningRule("py_library", frozenset({"no-lint"}))], None),
        ([OwningRule("rust_library", frozenset({"noclippy"}))], None),
        ([OwningRule("rust_library", frozenset())], RUST),
        ([OwningRule("pkg_files", frozenset()), OwningRule("cc_library", frozenset())], C_CPP),
    ],
)
def test_language_by_the_kinds_of_the_owning_rules(
    rules: list[OwningRule], language: str | None
) -> None:
    assert linted_language(rules) == language


def test_summary_counts_linted_untargeted_and_skipped_files() -> None:
    library = [OwningRule("py_library", frozenset())]
    owning = OwningTargets(
        ["//cmk:lib", "//cmk:data"],
        {
            "cmk/a.py": library,
            "cmk/b.py": library,
            "cmk/data.json": [OwningRule("filegroup", frozenset())],
            "omd/skel/profile.sh": [OwningRule("pkg_files", frozenset())],
        },
    )
    files = [
        "cmk/a.py",
        "cmk/b.py",
        "cmk/data.json",
        "omd/skel/profile.sh",
        "BUILD",
        "loose.py",
        "notes.md",
    ]
    assert summary_rows(files, owning, ["BUILD"], lambda _file: "") == [
        (f"{PYTHON}:", 2),
        (f"{STARLARK}:", 1),
        ("Not linted (no Bazel target):", 1),
        ("Not linted (no linted target lists it):", 1),
        ("Skipped (no linter):", 2),
    ]


@pytest.mark.parametrize(
    ("fix", "fix_args"),
    [(False, ["--fixes=false"]), (True, ["--fix"])],
)
def test_bazel_lint_fixes_only_in_fix_mode(fix: bool, fix_args: list[str]) -> None:
    assert bazel_lint_command(["//a:b"], fix=fix, bazel_flags=[]) == [
        "bazelisk",
        "lint",
        "--skip_incompatible_explicit_targets",
        *fix_args,
        "//a:b",
    ]


def test_bazel_flags_reach_bazel_lint() -> None:
    command = bazel_lint_command(["//a:b"], fix=False, bazel_flags=["--cmk_edition=pro"])
    assert command[-2:] == ["--cmk_edition=pro", "//a:b"]


@pytest.mark.parametrize(
    "bazel_flags",
    [["--config", "ci"], ["-c", "opt"], ["--build"], ["--cmk_edition=pro"]],
)
def test_bazel_flags_pass_the_parser(bazel_flags: list[str]) -> None:
    args = _parse_args(
        ["lint", "--buildifier=/bin/buildifier", "--buildifier_config=/cfg.json", "--delta"]
        + bazel_flags
    )
    assert args.bazel_flags == bazel_flags


def test_buildifier_checks_lint_without_touching_the_layout() -> None:
    assert _BUILDIFIER.command(["BUILD"], fix=False) == [
        "/bin/buildifier",
        "-lint=warn",
        "-mode=check",
        "-config=/cfg.json",
        "BUILD",
    ]


@pytest.mark.parametrize(
    ("returncode", "output", "findings"),
    [
        (4, "BUILD # reformat\nx.bzl:3: unused-variable: ...\n", "x.bzl:3: unused-variable: ..."),
        (4, "BUILD # reformat\n", ""),
        (0, "", ""),
    ],
)
def test_layout_findings_are_no_lint_findings(returncode: int, output: str, findings: str) -> None:
    assert lint_findings(returncode, output) == findings


@pytest.mark.parametrize(
    ("returncode", "output", "findings"),
    [
        (1, "BUILD:3: syntax error\n", "BUILD:3: syntax error"),
        (3, "", "buildifier failed with exit code 3"),
    ],
)
def test_buildifier_failures_are_findings_even_without_output(
    returncode: int, output: str, findings: str
) -> None:
    assert lint_findings(returncode, output) == findings


@pytest.mark.parametrize(
    ("fix", "clean", "message"),
    [
        (False, True, "No lint findings."),
        (False, False, "Lint findings above."),
        (True, True, None),
        (True, False, "Lint findings above, which could not be fixed automatically."),
    ],
)
def test_summary_ends_with_the_lint_outcome(fix: bool, clean: bool, message: str | None) -> None:
    assert outcome(fix, clean) == message


def test_targets_listing_a_file_in_their_hdrs_own_it() -> None:
    query = _fake_query(
        {
            ('set("src/foo.h")', "label"): "//src:foo.h\n",
            ('same_pkg_direct_rdeps(set("//src:foo.h"))', "streamed_jsonproto"): _rule(
                "//src:foo", ["//src:foo.cc"], hdrs=["//src:foo.h"]
            ),
        }
    )
    owning = owning_targets(query, ["src/foo.h"])
    assert owning.targets == ["//src:foo"]
    assert set(owning.rules) == {"src/foo.h"}


def test_skipped_files_are_no_query_errors() -> None:
    stderr = (
        "ERROR: Skipping 'notes.txt': no such target '//:notes.txt': ...\n"
        "WARNING: --keep_going specified, ignoring errors. Results may be inaccurate\n"
    )
    assert query_errors(stderr) == ""


def test_build_files_that_fail_to_load_are_query_errors() -> None:
    stderr = (
        "ERROR: /repo/pkg/BUILD:2:1: syntax error at 'newline': expected ,\n"
        "ERROR: Skipping 'pkg/a.py': no such target '//pkg:a.py': ...\n"
    )
    assert (
        query_errors(stderr) == "ERROR: /repo/pkg/BUILD:2:1: syntax error at 'newline': expected ,"
    )


def test_skipped_files_of_packages_that_fail_to_load_are_query_errors() -> None:
    stderr = (
        "ERROR: Skipping 'pkg/a.py': error loading package 'pkg': Label '//nope:x.bzl' is invalid\n"
        "ERROR: Skipping 'notes.txt': no such target '//:notes.txt': ...\n"
    )
    assert query_errors(stderr) == (
        "ERROR: Skipping 'pkg/a.py': error loading package 'pkg': Label '//nope:x.bzl' is invalid"
    )


def test_files_with_non_ascii_names_have_their_targets() -> None:
    query = _fake_query(
        {
            ('set("doc/café.py")', "label"): "//doc:café.py\n",
            ('same_pkg_direct_rdeps(set("//doc:café.py"))', "streamed_jsonproto"): _rule(
                "//doc:doc", ["//doc:café.py"]
            ),
        }
    )
    owning = owning_targets(query, ["doc/café.py"])
    assert owning.targets == ["//doc:doc"]
    assert set(owning.rules) == {"doc/café.py"}


class _FakeBranch:
    """A branch whose changed files are all dirty, with git hashes the linters can change."""

    def __init__(self, hashes: dict[str, str]) -> None:
        self.hashes = hashes

    def run(self, command: Sequence[str], stdin: str = "") -> str:
        match list(command[:2]):
            case ["make", _]:
                return ""
            case ["git", "merge-base"]:
                return "base\n"
            case ["git", "diff"]:
                return "".join(f"M\0{file}\0" for file in self.hashes)
            case ["git", "ls-files"] if "--modified" in command:
                return "".join(f"{file}\0" for file in self.hashes)
            case ["git", "ls-files"]:
                return ""
            case ["git", "hash-object"]:
                return "".join(f"{self.hashes[file]}\n" for file in stdin.split())
            case _:
                raise AssertionError(f"unexpected command {command}")


_LIB_QUERY = _fake_query(
    {
        ('set("cmk/a.py" "cmk/b.py")', "label"): "//cmk:a.py\n//cmk:b.py\n",
        (
            'same_pkg_direct_rdeps(set("//cmk:a.py" "//cmk:b.py"))',
            "streamed_jsonproto",
        ): _rule("//cmk:lib", ["//cmk:a.py", "//cmk:b.py"]),
    }
)


def _workspace(
    branch: _FakeBranch,
    query: Query,
    calls: list[Sequence[str]],
    call: Callable[[Sequence[str]], int] = lambda _command: 0,
    call_captured: Callable[[Sequence[str]], tuple[int, str]] = lambda _command: (0, ""),
) -> Workspace:
    def recorded_call(command: Sequence[str]) -> int:
        calls.append(command)
        return call(command)

    def recorded_call_captured(command: Sequence[str]) -> tuple[int, str]:
        calls.append(command)
        return call_captured(command)

    return Workspace(
        run=branch.run,
        query=query,
        call=recorded_call,
        call_captured=recorded_call_captured,
        which=lambda name: f"/usr/bin/{name}",
        is_file=lambda _file: True,
        read_first_line=lambda _file: "",
    )


@pytest.mark.parametrize("fix", [False, True])
def test_no_changed_files_run_no_linter(fix: bool) -> None:
    calls: list[Sequence[str]] = []
    workspace = _workspace(_FakeBranch({}), _fake_query({}), calls)
    assert lint_delta(workspace, _BUILDIFIER, fix=fix, bazel_flags=[]) == 0
    assert calls == []


def test_files_no_linter_takes_run_no_linter(capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[Sequence[str]] = []
    workspace = _workspace(_FakeBranch({"notes.md": "h1"}), _fake_query({}), calls)
    assert lint_delta(workspace, _BUILDIFIER, fix=False, bazel_flags=[]) == 0
    assert calls == []
    assert "None of the 1 file(s) changed compared to origin/master is linted" in (
        capsys.readouterr().out
    )


@pytest.mark.parametrize(("returncode", "exit_code"), [(0, 0), (1, 1)])
def test_bazel_lint_findings_make_the_exit_code_1(returncode: int, exit_code: int) -> None:
    calls: list[Sequence[str]] = []
    branch = _FakeBranch({"cmk/a.py": "h1", "cmk/b.py": "h2"})
    workspace = _workspace(branch, _LIB_QUERY, calls, call=lambda _command: returncode)
    assert lint_delta(workspace, _BUILDIFIER, fix=False, bazel_flags=[]) == exit_code
    assert calls == [bazel_lint_command(["//cmk:lib"], fix=False, bazel_flags=[])]


def test_buildifier_findings_make_the_exit_code_1() -> None:
    calls: list[Sequence[str]] = []
    workspace = _workspace(
        _FakeBranch({"BUILD": "h1"}),
        _fake_query({}),
        calls,
        call_captured=lambda _command: (4, "BUILD:1: module-docstring: ..."),
    )
    assert lint_delta(workspace, _BUILDIFIER, fix=False, bazel_flags=[]) == 1
    assert calls == [_BUILDIFIER.command(["BUILD"], fix=False)]


def test_fix_mode_reports_what_buildifier_could_not_fix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[Sequence[str]] = []
    workspace = _workspace(
        _FakeBranch({"BUILD": "h1"}),
        _fake_query({}),
        calls,
        call_captured=lambda _command: (4, "BUILD:1: module-docstring: ..."),
    )
    assert lint_delta(workspace, _BUILDIFIER, fix=True, bazel_flags=[]) == 1
    assert calls == [
        _BUILDIFIER.command(["BUILD"], fix=True),
        _BUILDIFIER.command(["BUILD"], fix=False),
    ]
    assert "BUILD:1: module-docstring: ..." in capsys.readouterr().out


def test_fix_mode_reports_only_the_files_the_linters_changed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    branch = _FakeBranch({"cmk/a.py": "h1", "cmk/b.py": "h2"})

    def fix_a(_command: Sequence[str]) -> int:
        branch.hashes["cmk/a.py"] = "h1-fixed"
        return 0

    workspace = _workspace(branch, _LIB_QUERY, [], call=fix_a)
    assert lint_delta(workspace, _BUILDIFIER, fix=True, bazel_flags=[]) == 0
    _, fixed = capsys.readouterr().out.split("Fixed 1 file(s):")
    assert "cmk/a.py" in fixed
    assert "cmk/b.py" not in fixed
