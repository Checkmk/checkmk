#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.network.rulesets.cdp_cache import (
    _migrate_inv_cdp_cache,
    _migrate_remove_columns,
)

REMOVE_COLUMNS = [
    "platform_details",
    "duplex",
    "vtp_mgmt_domain",
    "native_vlan",
    "power_consumption",
    "platform",
]


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            REMOVE_COLUMNS,
            REMOVE_COLUMNS,
        ),
        (
            REMOVE_COLUMNS + ["last_change"],
            REMOVE_COLUMNS,
        ),
    ],
    ids=["nothing to remove", "last_change is removed"],
)
def test_migrate_remove_columns(data: object, expected: Sequence[str]) -> None:
    reduced_list = _migrate_remove_columns(data)
    assert reduced_list == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "use_short_if_name": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "use_short_if_name": True,
            },
        ),
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "removecolumns": REMOVE_COLUMNS,
                "use_short_if_name": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "removecolumns": REMOVE_COLUMNS,
                "use_short_if_name": True,
            },
        ),
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "removecolumns": None,
                "use_short_if_name": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "use_short_if_name": True,
            },
        ),
    ],
    ids=[
        "no removecolumns key",
        "removecolumns with proper value is not removed",
        "removecolumns with empty value is removed",
    ],
)
def test_migrate_inv_cdp_cache(data: object, expected: Mapping[str, object]) -> None:
    migrated = _migrate_inv_cdp_cache(data)
    assert migrated == expected
