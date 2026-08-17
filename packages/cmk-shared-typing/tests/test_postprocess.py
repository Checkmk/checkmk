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
                    count = "count"
                    foo = "bar"
            """,
            """
                class Foo(str, Enum):
                    count = "count"  # type: ignore[assignment]
                    foo = "bar"
            """,
            id="enum-with-shadowing-member",
        ),
        pytest.param(
            """
                class Foo(StrEnum):
                    count = "count"
                    foo = "bar"
            """,
            """
                class Foo(StrEnum):
                    count = "count"  # type: ignore[assignment]
                    foo = "bar"
            """,
            id="strenum-with-shadowing-member",
        ),
        pytest.param(
            """
                class Foo(str, Enum, metaclass=EnumMeta):
                    count = "count"
            """,
            """
                class Foo(str, Enum, metaclass=EnumMeta):
                    count = "count"  # type: ignore[assignment]
            """,
            id="metaclass-keyword-does-not-hide-str-enum",
        ),
        pytest.param(
            """
                class Foo(Enum):
                    foo = "bar"
            """,
            """
                class Foo(str, Enum):
                    foo = "bar"
            """,
            id="no-shadowing-member",
        ),
        pytest.param(
            """
                class Foo(IntEnum):
                    count = 1
            """,
            """
                class Foo(IntEnum):
                    count = 1
            """,
            id="non-str-enum-untouched",
        ),
    ],
)
def test_postprocess_enums(code: str, expected: str) -> None:
    assert postprocess(dedent(code).lstrip()) == dedent(expected).lstrip()
