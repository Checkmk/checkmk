#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from get_distros import main

EDITIONS_YAML = """
common: &common
    - "debian-12"
    - "ubuntu-24.04"
internal_distros: &internal_distros
    - "sles-16.0"
internal_editions:
    - "cloud"
editions:
    pro:
        release: [*common, "cma-4"]
        daily: ["ubuntu-24.04"]
    cloud:
        release: ["ubuntu-22.04"]
        daily: ["ubuntu-22.04"]
distro_to_codename: {}
"""


@pytest.fixture(name="editions_file")
def fixture_editions_file(tmp_path: Path) -> Path:
    editions_file = tmp_path / "editions.yml"
    editions_file.write_text(EDITIONS_YAML)
    return editions_file


def _run(
    editions_file: Path,
    argv: Sequence[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> str:
    monkeypatch.setattr(
        sys, "argv", ["get_distros.py", "--editions_file", str(editions_file), *argv]
    )
    main()
    return capsys.readouterr().out.strip()


def test_all_lists_every_distro_of_every_edition(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(editions_file, ["all"], monkeypatch, capsys) == (
        "cma-4 debian-12 ubuntu-22.04 ubuntu-24.04"
    )


def test_all_can_be_narrowed_to_one_use_case(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(editions_file, ["all", "--use_case", "daily"], monkeypatch, capsys) == (
        "ubuntu-22.04 ubuntu-24.04"
    )


def test_use_cases_lists_distros_of_one_edition_and_use_case(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _run(
        editions_file,
        ["use_cases", "--edition", "pro", "--use_case", "release"],
        monkeypatch,
        capsys,
    )

    assert out == "cma-4 debian-12 ubuntu-24.04"


def test_editions_lists_all_editions_sorted(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(editions_file, ["editions"], monkeypatch, capsys) == "cloud pro"


def test_internal_build_artifacts_lists_internal_distros_and_editions(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(editions_file, ["internal_build_artifacts"], monkeypatch, capsys) == (
        "cloud sles-16.0"
    )


def test_internal_build_artifacts_as_rsync_pattern_is_a_brace_expansion(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _run(
        editions_file,
        ["internal_build_artifacts", "--as-rsync-exclude-pattern"],
        monkeypatch,
        capsys,
    )

    assert out == "{'*sles-16.0*','*cloud*','*omd*','*bazel*'}"
