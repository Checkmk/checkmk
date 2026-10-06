#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""groovy-format leaves the content of string literals alone and formats the code around them.

Each case in groovy/ is an input <case>.groovy with the expected result <case>.formatted.groovy.
Every input contains something to fix in the code, so a formatter doing nothing fails, too.
"""

import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

CASES_DIR = Path(__file__).parent / "groovy"


@dataclass(frozen=True)
class Formatted:
    source: str
    remaining_findings: list[str]


def _expected(case: str, remaining_findings: list[str]) -> Formatted:
    return Formatted((CASES_DIR / f"{case}.formatted.groovy").read_text(), remaining_findings)


@pytest.fixture(name="formatted", scope="module")
def fixture_formatted(tmp_path_factory: pytest.TempPathFactory) -> Mapping[str, Formatted]:
    # One run for all cases, as each run starts a JVM for CodeNarc
    work_dir = tmp_path_factory.mktemp("groovy")
    sources = []
    for case in CASES_DIR.glob("*.groovy"):
        if not case.name.endswith(".formatted.groovy"):
            sources.append(work_dir / case.name)
            shutil.copyfile(case, sources[-1])
    result = subprocess.run(
        [Path(os.environ["GROOVY_FORMAT"]).absolute(), "--format", "--output", "json", *sources],
        capture_output=True,
        text=True,
        check=False,
    )
    # 1 means that findings are left, which the tests check per case
    if result.returncode not in (0, 1):
        raise RuntimeError(f"groovy-format failed:\n{result.stdout}\n{result.stderr}")
    files = json.loads(result.stdout)["files"]
    return {
        source.stem: Formatted(
            source.read_text(),
            [
                error["rule"]
                for error in files.get(str(source), {"errors": []})["errors"]
                if not error.get("fixed")
            ],
        )
        for source in sources
    }


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("comment_like_lines_in_strings", id="lines starting with // in strings"),
        pytest.param("closing_braces_in_strings", id="closing braces in strings"),
        pytest.param("blank_lines_in_strings", id="consecutive blank lines in strings"),
        pytest.param("blank_lines_in_comments", id="consecutive blank lines in comments"),
        pytest.param("whitespace_in_strings", id="tabs and trailing whitespace in strings"),
        pytest.param("braces_and_slashes_in_code", id="braces in comments and strings, divisions"),
        pytest.param(
            "closing_braces_after_strings_and_comments",
            id="closing braces after multi-line strings and comments",
        ),
        pytest.param("code_in_string_interpolation", id="code in ${} of a multi-line string"),
    ],
)
def test_code_is_formatted_and_strings_are_kept(
    case: str, formatted: Mapping[str, Formatted]
) -> None:
    assert formatted[case] == _expected(case, [])


def test_fix_changing_a_string_is_not_applied(formatted: Mapping[str, Formatted]) -> None:
    assert formatted["fix_changing_a_string"] == _expected(
        "fix_changing_a_string", ["IfStatementBraces"]
    )
