#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.repo_checks.bazel_lint_coverage import (
    classify,
    evaluate,
    FILE_CLASSES,
    FileClass,
    format_report,
    label_to_path,
    parse_known_offenders,
    SHELL,
)

_BY_NAME = {fc.name: fc for fc in FILE_CLASSES}
POWERSHELL = _BY_NAME["powershell"]
RUST = _BY_NAME["rust"]
C_CPP = _BY_NAME["c/c++"]
JAVASCRIPT = _BY_NAME["javascript"]


@pytest.mark.parametrize(
    "path, first_line, expected",
    [
        pytest.param("a/run.sh", b"", SHELL, id="sh extension"),
        pytest.param("a/run", b"#!/bin/bash\n", SHELL, id="bash shebang"),
        pytest.param("a/run", b"#!/bin/sh -e\n", SHELL, id="sh shebang with option"),
        pytest.param("a/run", b"#!/usr/bin/env bash\n", SHELL, id="env bash"),
        pytest.param("a/run", b"#!/usr/bin/ksh", SHELL, id="ksh without newline"),
        pytest.param("a/.do-it", b"#!/bin/bash\n", SHELL, id="dotfile with shebang"),
        pytest.param("a/agent.linux", b"#!/bin/bash\n", SHELL, id="shebang behind other extension"),
        pytest.param("agents/wnx/x.ps1", b"", POWERSHELL, id="powershell in msbuild tree"),
        pytest.param("a/script.ps1", b"", POWERSHELL, id="powershell"),
        pytest.param("a/main.rs", b"", RUST, id="rust"),
        pytest.param("a/x.h", b"", C_CPP, id="c header"),
        pytest.param("a/x.cjs", b"", JAVASCRIPT, id="commonjs"),
    ],
)
def test_source_file_gets_its_class(path: str, first_line: bytes, expected: FileClass) -> None:
    assert classify(path, first_line) is expected


@pytest.mark.parametrize(
    "path, first_line",
    [
        pytest.param("a/run", b"#!/bin/zsh\n", id="zsh unsupported by shellcheck"),
        pytest.param("a/run", b"#!/usr/bin/fish\n", id="interpreter ending in sh"),
        pytest.param("a/run", b"#!/usr/bin/env python3\n", id="python shebang"),
        pytest.param("a/run", b"echo no shebang\n", id="no shebang"),
        pytest.param("a/run.pl", b"#!/usr/bin/perl\n", id="perl shebang"),
        pytest.param("doc/treasures/x.sh", b"", id="excluded tree"),
        pytest.param("agents/wnx/x.cc", b"", id="c++ in msbuild tree"),
    ],
)
def test_other_files_are_ignored(path: str, first_line: bytes) -> None:
    assert classify(path, first_line) is None


@pytest.mark.parametrize(
    "label, expected",
    [
        pytest.param("//pkg/sub:dir/x.sh", "pkg/sub/dir/x.sh", id="nested package"),
        pytest.param("//:x.sh", "x.sh", id="root package"),
        pytest.param("@rules_foo//pkg:x.sh", None, id="external repository"),
    ],
)
def test_label_maps_to_repository_path(label: str, expected: str | None) -> None:
    assert label_to_path(label) == expected


def test_comments_and_blank_lines_are_not_known_offenders() -> None:
    text = "# CMK-1 component\na/x.sh\n\nb/y.rs  # trailing comment\n"

    assert parse_known_offenders(text) == {"a/x.sh", "b/y.rs"}


def test_uncovered_unknown_file_is_a_new_offender() -> None:
    result = evaluate({"a/x.sh": SHELL}, {"shell": set()}, known_offenders=set())

    assert result.new_offenders == {"shell": ["a/x.sh"]}


def test_uncovered_known_file_passes() -> None:
    result = evaluate({"a/x.sh": SHELL}, {"shell": set()}, known_offenders={"a/x.sh"})

    assert (result.new_offenders, result.stale_known_offenders) == ({}, [])


def test_file_covered_by_another_class_is_still_an_offender() -> None:
    result = evaluate(
        {"a/x.sh": SHELL}, {"shell": set(), "javascript": {"a/x.sh"}}, known_offenders=set()
    )

    assert result.new_offenders == {"shell": ["a/x.sh"]}


def test_covered_known_offender_is_stale() -> None:
    result = evaluate({"a/x.sh": SHELL}, {"shell": {"a/x.sh"}}, known_offenders={"a/x.sh"})

    assert result.stale_known_offenders == ["a/x.sh"]


def test_deleted_known_offender_is_stale() -> None:
    result = evaluate({}, {}, known_offenders={"a/gone.sh"})

    assert result.stale_known_offenders == ["a/gone.sh"]


def test_report_names_new_offender_with_its_target_kinds() -> None:
    result = evaluate({"a/new.rs": RUST}, {"rust": set()}, known_offenders=set())

    assert (
        " -- rust: a/new.rs -> rust_binary, rust_library, rust_shared_library or rust_test"
        in format_report(result).splitlines()
    )


def test_report_names_stale_known_offender() -> None:
    result = evaluate({"a/fixed.sh": SHELL}, {"shell": {"a/fixed.sh"}}, {"a/fixed.sh"})

    assert " -- a/fixed.sh" in format_report(result).splitlines()
