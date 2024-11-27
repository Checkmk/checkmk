#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.wato._notification_parameter._pushover import _migrate_to_priority


@pytest.mark.parametrize(
    "old_priority, new_priority",
    [
        pytest.param(
            "0",
            ("normal", None),
            id="Normal",
        ),
        pytest.param(
            {
                "priority": "2",
                "retry": 0,
                "expire": 0,
                "receipts": "ergerahtrehrthrthrhrhaergherhtgrsth",
            },
            ("emergency", (0.0, 0.0, "ergerahtrehrthrthrhrhaergherhtgrsth")),
            id="Emergency",
        ),
    ],
)
def test__migrate_to_priority(
    old_priority: tuple[str, None] | dict[str, int | str] | str,
    new_priority: tuple[str, None] | tuple[Literal["emergency"], tuple[float, float, str]],
) -> None:
    assert _migrate_to_priority(old_priority) == new_priority
