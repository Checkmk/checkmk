#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.graphing._html_render import _render_title_elements_plain


@pytest.mark.parametrize(
    "elements, result",
    [
        (
            ["first", "second"],
            "first / second",
        ),
        (
            ["", "second"],
            "second",
        ),
    ],
)
def test_render_title_elements_plain(elements: Sequence[str], result: str) -> None:
    assert _render_title_elements_plain(elements) == result
