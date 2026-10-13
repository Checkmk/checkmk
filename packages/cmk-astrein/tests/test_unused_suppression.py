#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.astrein.checker_simple_patterns import HTMLDebugChecker
from cmk.astrein.framework import CheckerError, run_checkers


def _run(
    tmp_path: Path, code: str, *, report_unknown_suppressions: bool = False
) -> list[CheckerError]:
    file_path = tmp_path / "module.py"
    file_path.write_text(code)
    return run_checkers(
        file_path,
        tmp_path,
        [HTMLDebugChecker],
        report_unknown_suppressions=report_unknown_suppressions,
    )


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("html.debug()  # astrein: disable=html-debug\n", id="same line"),
        pytest.param("# astrein: disable=html-debug\nhtml.debug()\n", id="preceding line"),
    ],
)
def test_needed_suppression_is_not_reported(tmp_path: Path, code: str) -> None:
    assert _run(tmp_path, code) == []


def test_suppression_on_clean_line_is_reported_as_unused(tmp_path: Path) -> None:
    errors = _run(tmp_path, "html.render()  # astrein: disable=html-debug\n")

    assert [(e.checker_id, e.line, e.column, e.message) for e in errors] == [
        (
            "unused-suppression",
            1,
            17,
            "Unused suppression for html-debug: nothing to suppress",
        )
    ]


def test_suppression_above_clean_line_is_reported_as_unused(tmp_path: Path) -> None:
    errors = _run(tmp_path, "# astrein: disable=html-debug\n\nhtml.debug()\n")

    assert [(e.checker_id, e.line) for e in errors] == [
        ("html-debug", 3),
        ("unused-suppression", 1),
    ]


def test_suppression_for_checker_not_run_is_not_reported(tmp_path: Path) -> None:
    assert _run(tmp_path, "import PIL  # astrein: disable=pillow-import\n") == []


def test_suppression_for_unknown_checker_is_reported_when_all_checkers_ran(
    tmp_path: Path,
) -> None:
    errors = _run(
        tmp_path,
        "x = 1  # astrein: disable=no-such-checker\n",
        report_unknown_suppressions=True,
    )

    assert [e.message for e in errors] == ["Unused suppression for unknown checker no-such-checker"]


def test_suppression_text_inside_string_is_ignored(tmp_path: Path) -> None:
    errors = _run(tmp_path, 'html.debug("# astrein: disable=html-debug")\n')

    assert [e.checker_id for e in errors] == ["html-debug"]
