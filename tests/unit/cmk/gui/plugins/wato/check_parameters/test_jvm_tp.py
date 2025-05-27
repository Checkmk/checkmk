#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.jvm_tp import _migrate


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            (80, 90),
            ("percentage", (80, 90)),
            id="old tuple -> new tuple",
        ),
        pytest.param(
            ("percentage", (80, 90)),
            ("percentage", (80, 90)),
            id="new percentage tuple -> new tuple",
        ),
        pytest.param(
            ("absolute", (80, 90)),
            ("absolute", (80, 90)),
            id="new absolute tuple -> new tuple",
        ),
    ],
)
def test_migrate(
    entry: tuple[int, int] | tuple[str, tuple[int, int]],
    result: tuple[str, tuple[int, int]],
) -> None:
    assert _migrate(entry) == result
