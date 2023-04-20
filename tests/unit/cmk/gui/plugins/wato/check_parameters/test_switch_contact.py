#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.switch_contact import _migrate


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {},
            {},
            id="transform dict is noop",
        ),
        pytest.param(
            "closed",
            {"state": "closed"},
            id="transform dict is noop",
        ),
    ],
)
def test_transform(entry, result) -> None:  # type:ignore[no-untyped-def]
    assert _migrate(entry) == result
