# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest
from bazel_delta.files import FileStatus, RunCaptured
from bazel_delta.mypy import (
    build_files,
    bzl_files,
    checked_targets,
    global_inputs,
    global_inputs_warning,
    mypy_build_command,
    mypy_delta,
    MypyWorkspace,
    package_of,
    packages_loading,
    python_files,
    python_targets_of_packages,
    summary_rows,
    targets_to_check,
    type_checked_files,
)
from bazel_delta.targets import OwningRule, OwningTargets, Query


def test_python_files_include_stubs() -> None:
    assert python_files(["a.py", "b.pyi", "c.sh", "BUILD"]) == ["a.py", "b.pyi"]


def test_build_files_are_found_by_name() -> None:
    assert build_files(["BUILD", "cmk/BUILD.bazel", "cmk/a.py", "omd/foo.BUILD"]) == [
        "BUILD",
        "cmk/BUILD.bazel",
    ]


def test_bzl_files_are_found_by_extension() -> None:
    assert bzl_files(["bazel/rules/x.bzl", "BUILD", "a.py"]) == ["bazel/rules/x.bzl"]


def test_packages_loading_a_bzl_file() -> None:
    queries: list[tuple[str, str]] = []

    def query(expression: str, output: str) -> str:
        queries.append((expression, output))
        return "//cmk/gui:BUILD\n//:BUILD\n"

    assert packages_loading(query, ["bazel/rules/x.bzl", "bazel/rules/y.bzl"]) == ["cmk/gui", ""]
    assert queries == [('rbuildfiles("bazel/rules/x.bzl", "bazel/rules/y.bzl")', "label")]


def test_summary_counts_every_kind_of_changed_file() -> None:
    files = [
        "cmk/a.py",
        "cmk/b.pyi",
        "cmk/test_c.py",
        "cmk/old.py",
        "loose.py",
        "cmk/BUILD",
        "bazel/rules/x.bzl",
        "run.sh",
        "x.md",
        "pyproject.toml",
        "bazel/tools/aspects.bzl",
        "bazel/tools/BUILD",
    ]
    library = [OwningRule("//cmk:lib", "py_library", frozenset())]
    test = [OwningRule("//cmk:test", "py_test", frozenset({"no-mypy"}))]
    owning = OwningTargets(
        ["//cmk:lib", "//cmk:test"],
        {"cmk/a.py": library, "cmk/b.pyi": library, "cmk/test_c.py": test},
    )
    python = ["cmk/a.py", "cmk/b.pyi", "cmk/test_c.py", "loose.py"]
    rows = summary_rows(
        files,
        python,
        ["cmk/old.py"],
        ["cmk/BUILD", "bazel/tools/BUILD"],
        ["bazel/rules/x.bzl", "bazel/tools/aspects.bzl"],
        ["pyproject.toml", "bazel/tools/aspects.bzl", "bazel/tools/BUILD"],
        owning,
        {"cmk/a.py", "cmk/b.pyi"},
    )
    assert rows == [
        ("Python (mypy):", 2),
        ("Deleted Python (users checked):", 1),
        ("BUILD files (Python targets checked):", 1),
        (".bzl files (Python targets of their users checked):", 1),
        ("Affect every type check:", 3),
        ("Not checked (manual or no-mypy):", 1),
        ("Not checked (no Bazel target):", 1),
        ("Other files (users checked):", 2),
    ]


def _owned_by(label: str, tags: frozenset[str] = frozenset()) -> OwningTargets:
    return OwningTargets([label], {"cmk/a.py": [OwningRule(label, "py_library", tags)]})


def test_files_of_built_targets_are_type_checked() -> None:
    assert type_checked_files(_owned_by("//cmk:lib"), ["//cmk:lib"]) == {"cmk/a.py"}


def test_files_of_manual_targets_are_not_type_checked() -> None:
    # checked_targets leaves the targets tagged manual out of the build
    assert type_checked_files(_owned_by("//cmk:lib"), ["//cmk:other"]) == set()


def test_files_of_no_mypy_targets_are_not_type_checked() -> None:
    owning = _owned_by("//cmk:unit", frozenset({"no-mypy"}))
    assert type_checked_files(owning, ["//cmk:unit"]) == set()


def test_one_type_checked_target_is_enough() -> None:
    owning = OwningTargets(
        ["//cmk:lib", "//cmk:unit"],
        {
            "cmk/a.py": [
                OwningRule("//cmk:unit", "py_test", frozenset({"no-mypy"})),
                OwningRule("//cmk:lib", "py_library", frozenset()),
            ]
        },
    )
    assert type_checked_files(owning, ["//cmk:lib", "//cmk:unit"]) == {"cmk/a.py"}


@pytest.mark.parametrize(
    ("file", "package"),
    [
        ("cmk/gui/old.py", "cmk/gui"),
        ("cmk/gui/sub/old.py", "cmk/gui"),
        ("setup.py", ""),
    ],
)
def test_deleted_files_belong_to_the_closest_package(file: str, package: str) -> None:
    existing_build_files = {"BUILD", "cmk/gui/BUILD.bazel"}
    assert package_of(file, existing_build_files.__contains__) == package


def test_python_targets_query_includes_the_root_package() -> None:
    queries: list[tuple[str, str]] = []

    def query(expression: str, output: str) -> str:
        queries.append((expression, output))
        return ""

    python_targets_of_packages(query, ["cmk/gui", ""])
    assert queries == [('kind("^py_", set("//cmk/gui:all" "//:all"))', "label")]


def test_checked_targets_query_excludes_manual_rules() -> None:
    queries: list[tuple[str, str]] = []

    def query(expression: str, output: str) -> str:
        queries.append((expression, output))
        return ""

    checked_targets(query, ["//cmk:lib"])
    assert queries == [
        (
            (
                'let r = kind(rule, rdeps(//..., set("//cmk:lib"))) in '
                '$r except attr(tags, "\\bmanual\\b", $r)'
            ),
            "label",
        )
    ]


def test_global_inputs_are_found_among_the_changed_files() -> None:
    files = ["cmk/a.py", "pyproject.toml", "tests/typeshed/foo/__init__.pyi", "cmk/pyproject.toml"]
    assert global_inputs(files) == ["pyproject.toml", "tests/typeshed/foo/__init__.pyi"]


def test_global_inputs_warning_names_the_files_and_the_full_check() -> None:
    assert global_inputs_warning(["pyproject.toml", "MODULE.bazel"]) == (
        "pyproject.toml, MODULE.bazel changed, which affects every type check, so this run"
        " cannot tell. Run 'bazel build --config=mypy //...'."
    )


def test_bazel_flags_reach_the_mypy_build() -> None:
    assert "--cmk_edition=pro" in mypy_build_command("/tmp/x.targets", ["--cmk_edition=pro"])


def _fake_query(outputs: Mapping[str, str]) -> Query:
    """Returns the labels given for an expression, nothing otherwise."""

    def query(expression: str, output: str) -> str:
        assert output == "label"
        return outputs.get(expression, "")

    return query


_GUI_TARGETS = {'kind("^py_", set("//cmk/gui:all"))': "//cmk/gui:gui\n//cmk/gui:test\n"}
_GUI_BUILD = {"BUILD", "cmk/gui/BUILD"}.__contains__


def test_changed_files_are_checked_through_their_users() -> None:
    # Also a source of generated code, whose users rdeps finds
    query = _fake_query(
        {
            'set("cmk/gui/a.py" "packages/x/changes.json")': "//cmk/gui:a.py\n//packages/x:changes.json\n"
        }
    )
    files = {"cmk/gui/a.py": FileStatus.MODIFIED, "packages/x/changes.json": FileStatus.MODIFIED}
    assert targets_to_check(files, query, _fake_query({}), _GUI_BUILD) == [
        "//cmk/gui:a.py",
        "//packages/x:changes.json",
    ]


def test_a_deleted_file_checks_the_python_targets_of_its_package() -> None:
    files = {"cmk/gui/old.py": FileStatus.DELETED}
    assert targets_to_check(files, _fake_query(_GUI_TARGETS), _fake_query({}), _GUI_BUILD) == [
        "//cmk/gui:gui",
        "//cmk/gui:test",
    ]


def test_a_changed_build_file_checks_the_python_targets_of_its_package() -> None:
    query = _fake_query(_GUI_TARGETS | {'set("cmk/gui/BUILD")': "//cmk/gui:BUILD\n"})
    files = {"cmk/gui/BUILD": FileStatus.MODIFIED}
    assert targets_to_check(files, query, _fake_query({}), _GUI_BUILD) == [
        "//cmk/gui:BUILD",
        "//cmk/gui:gui",
        "//cmk/gui:test",
    ]


def test_a_changed_bzl_file_checks_the_python_targets_of_the_packages_loading_it() -> None:
    universe_query = _fake_query({'rbuildfiles("bazel/rules/x.bzl")': "//cmk/gui:BUILD\n"})
    files = {"bazel/rules/x.bzl": FileStatus.MODIFIED}
    assert targets_to_check(files, _fake_query(_GUI_TARGETS), universe_query, _GUI_BUILD) == [
        "//cmk/gui:gui",
        "//cmk/gui:test",
    ]


def test_files_no_package_declares_reach_no_targets() -> None:
    files = {"notes.md": FileStatus.UNTRACKED}
    assert targets_to_check(files, _fake_query({}), _fake_query({}), _GUI_BUILD) == []


def _branch(files: Sequence[str]) -> RunCaptured:
    """git and make of a branch on origin/master whose changes are the files."""

    def run(command: Sequence[str], stdin: str = "") -> str:
        assert not stdin
        match list(command[:2]):
            case ["make", _]:
                return ""
            case ["git", "merge-base"]:
                return "base\n"
            case ["git", "diff"]:
                return "".join(f"M\0{file}\0" for file in files)
            case ["git", "ls-files"]:
                return ""
            case _:
                raise AssertionError(f"unexpected command {command}")

    return run


def _query(expression: str, output: str) -> str:
    """cmk/a.py is a target, which //cmk:lib uses."""
    if output != "label":
        return ""
    if expression.startswith("set(") and '"cmk/a.py"' in expression:
        return "//cmk:a.py\n"
    if expression.startswith("let r = "):
        return "//cmk:lib\n"
    return ""


def _mypy_workspace(
    files: Sequence[str], builds: list[Sequence[str]], build_exit_code: int = 0
) -> MypyWorkspace:
    def run_on_terminal(command: Sequence[str]) -> int:
        builds.append(command)
        return build_exit_code

    return MypyWorkspace(
        run=_branch(files),
        query=_query,
        universe_query=_query,
        run_on_terminal=run_on_terminal,
        is_file=lambda _file: False,
    )


def test_no_changed_files_build_nothing() -> None:
    builds: list[Sequence[str]] = []
    assert mypy_delta(_mypy_workspace([], builds), []) == 0
    assert builds == []


def test_files_no_target_uses_build_nothing() -> None:
    builds: list[Sequence[str]] = []
    assert mypy_delta(_mypy_workspace(["notes.md"], builds), []) == 0
    assert builds == []


@pytest.mark.parametrize(("build_exit_code", "exit_code"), [(0, 0), (1, 1)])
def test_the_exit_code_is_that_of_the_mypy_build(build_exit_code: int, exit_code: int) -> None:
    builds: list[Sequence[str]] = []
    workspace = _mypy_workspace(["cmk/a.py"], builds, build_exit_code)
    assert mypy_delta(workspace, []) == exit_code
    assert len(builds) == 1


@pytest.mark.parametrize("files", [["pyproject.toml"], ["cmk/a.py", "pyproject.toml"]])
def test_a_changed_global_input_makes_the_exit_code_1(
    files: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert mypy_delta(_mypy_workspace(files, []), []) == 1
    assert "pyproject.toml changed, which affects every type check" in capsys.readouterr().out
