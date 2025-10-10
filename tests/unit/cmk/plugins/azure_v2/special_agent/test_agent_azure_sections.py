#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence

import pytest

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import Section


@pytest.mark.parametrize(
    "piggytarget, expected_piggytarget_header",
    [
        (["one"], "<<<<one>>>>"),
        (["piggy-back"], "<<<<piggy-back>>>>"),
    ],
)
def test_piggytarget_header(
    piggytarget: Sequence[str],
    expected_piggytarget_header: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = Section("testsection", piggytarget, 1, ["myopts"])
    section.add(["section data"])
    section.write()
    section_stdout = capsys.readouterr().out.split("\n")
    assert section_stdout[0] == expected_piggytarget_header


@pytest.mark.parametrize(
    "section_name, expected_section_header",
    [
        ("testsection", "<<<testsection:sep(1):myopts>>>"),
        ("test-section", "<<<test_section:sep(1):myopts>>>"),
    ],
)
def test_section_header(
    section_name: str,
    expected_section_header: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = Section(section_name, [""], 1, ["myopts"])
    section.add(["section data"])
    section.write()
    section_stdout = capsys.readouterr().out.split("\n")
    assert section_stdout[1] == expected_section_header


@pytest.mark.parametrize(
    "section_name, section_data, separator, expected_section",
    [
        ("testsection", (("section data",)), 0, ["section data"]),
        (
            "test-section",
            (("first line",), ("second line",)),
            124,
            ["first line", "second line"],
        ),
        (
            "test-section",
            (("first line a", "first line b"), ("second line",)),
            124,
            ["first line a|first line b", "second line"],
        ),
    ],
)
def test_section(
    section_name: str,
    section_data: Sequence[str],
    separator: int,
    expected_section: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = Section(section_name, [""], separator, ["myopts"])
    section.add(section_data)
    section.write()
    section_stdout = capsys.readouterr().out.split("\n")
    assert section_stdout[2:-2] == expected_section
