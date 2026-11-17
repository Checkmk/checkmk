#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.systemd_services import (
    _migrate_unit_not_found_key,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            {"else": 1, "cpu_time": (1.0, 2.0)},
            {"unit_not_found": 1, "cpu_time": (1.0, 2.0)},
            id="legacy else key",
        ),
        pytest.param(
            {"unit_not_found": 1, "cpu_time": ("fixed", (1.0, 2.0))},
            {"unit_not_found": 1, "cpu_time": ("fixed", (1.0, 2.0))},
            id="already migrated",
        ),
    ],
)
def test_migrate_unit_not_found_key(value: object, expected: dict[str, object]) -> None:
    assert _migrate_unit_not_found_key(value) == expected
