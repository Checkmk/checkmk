#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from textwrap import dedent

from datamodel_code_generator.format import CodeFormatter, PythonVersion


def test_custom_formatter_hook_applies_postprocessing(tmp_path: Path) -> None:
    formatter = CodeFormatter(
        PythonVersion.PY_314,
        settings_path=tmp_path,
        custom_formatters=["utils.format"],
        formatters=[],
    )
    code = dedent("""
        class Foo(Enum):
            foo = 'bar'
    """).lstrip()
    expected = dedent("""
        class Foo(str, Enum):
            foo = "bar"
    """).lstrip()
    assert formatter.format_code(code) == expected
