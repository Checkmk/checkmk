#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.rulesets.custom_files import migrate


@pytest.mark.parametrize(
    "value, expected",
    [
        (["pkg_1", "pkg_2"], {"folders": ["pkg_1", "pkg_2"]}),
        ([], {"folders": []}),
        ({"folders": ["pkg_1"]}, {"folders": ["pkg_1"]}),
        ({"folders": []}, {"folders": []}),
    ],
)
def test_migrate(value: object, expected: object) -> None:
    assert migrate(value) == expected


def test_migrate_invalid() -> None:
    with pytest.raises(ValueError):
        migrate("invalid")
