#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from textwrap import dedent

import pytest
from utils.postprocess import postprocess


@pytest.mark.parametrize(
    ["code", "expected"],
    [
        pytest.param(
            """
                class Foo(Enum):
                    foo = "bar"
            """,
            """
                class Foo(str, Enum):
                    foo = "bar"
            """,
            id="enum-becomes-str-enum",
        ),
        pytest.param(
            """
                class Foo(IntEnum):
                    foo = 1
            """,
            """
                class Foo(IntEnum):
                    foo = 1
            """,
            id="non-str-enum-untouched",
        ),
    ],
)
def test_postprocess_enums(code: str, expected: str) -> None:
    assert postprocess(dedent(code).lstrip()) == dedent(expected).lstrip()
