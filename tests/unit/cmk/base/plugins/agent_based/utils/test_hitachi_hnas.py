#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.utils.hitachi_hnas import (
    parse_physical_volumes,
    parse_virtual_volumes,
)


@pytest.mark.parametrize(
    "volume_data,expected",
    [
        (
            [["1024", "mount_id1", "2", "", "", "1"]],
            ({"1024": "mount_id1"}, {"1024 mount_id1": ("mounted", None, None, "1")}),
        )
    ],
)
def test_parse_physical_volumes(volume_data, expected) -> None:
    assert parse_physical_volumes(volume_data) == expected


@pytest.mark.parametrize(
    "volume_data,expected",
    [
        (
            (
                {"1071": "mount_id2"},
                [["17417895.101.110.100.111.45.104.111.109.101", "1071", "mount_id3"]],
                [],
            ),
            ({"mount_id3 on mount_id2": (None, None)}),
        )
    ],
)
def test_parse_virtual_volumes(volume_data, expected) -> None:
    assert parse_virtual_volumes(*volume_data) == expected
