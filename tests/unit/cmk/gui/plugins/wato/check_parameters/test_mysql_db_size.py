#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.mysql_db_size import _migrate


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {},
            {
                "levels": None,
            },
            id="empty dict",
        ),
        pytest.param(
            (1, 2),
            {
                "levels": (1, 2),
            },
            id="tuple",
        ),
        pytest.param(
            {
                "levels": (1, 2),
            },
            {
                "levels": (1, 2),
            },
            id="keep dict",
        ),
    ],
)
def test_migrate(
    entry: dict[str, object] | tuple[float, float], result: dict[str, tuple[float, float]]
) -> None:
    assert _migrate(entry) == result
