#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.metrics.html_render import render_title_elements_plain


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
def test_render_title_elements_plain(elements, result) -> None:  # type:ignore[no-untyped-def]
    assert render_title_elements_plain(elements) == result
