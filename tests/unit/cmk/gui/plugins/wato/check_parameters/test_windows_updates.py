#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.windows_updates import _transform


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            (1, 2, 3, 4, 5, 6, True),
            {
                "levels_important": (1, 2),
                "levels_optional": (3, 4),
                "levels_lower_forced_reboot": (5, 6),
            },
            id="tuple conversion",
        ),
        pytest.param(
            (0, 0, 0, 0, 5, 6, True),
            {
                "levels_important": None,
                "levels_optional": None,
                "levels_lower_forced_reboot": (5, 6),
            },
            id="zero to None conversion",
        ),
        pytest.param(
            {},
            {},
            id="transform dict is noop",
        ),
        pytest.param(
            (0, 1, 0, 1, 2, 2, True),
            {
                "levels_important": (1, 1),
                "levels_optional": (1, 1),
                "levels_lower_forced_reboot": (2, 2),
            },
            id="handle only crit level set",
        ),
        pytest.param(
            (2, 0, 2, 0, 2, 2, True),
            {
                "levels_important": (2, 2000),
                "levels_optional": (2, 2000),
                "levels_lower_forced_reboot": (2, 2),
            },
            id="handle only warn level set, and set crit to double of warn",
        ),
    ],
)
def test_transform(entry, result):
    assert _transform(entry) == result
