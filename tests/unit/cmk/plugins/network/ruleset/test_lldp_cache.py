#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.plugins.network.rulesets.lldp_cache import (
    _migrate_lldp_cache,
)

REMOVE_COLUMNS = [
    "port_description",
    "system_description",
    "capabilities_map_supported",
    "capabilities",
]


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "remove_columns": [],
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
        ),
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "removecolumns": REMOVE_COLUMNS,
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "remove_columns": REMOVE_COLUMNS,
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
        ),
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "remove_columns": None,
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "remove_columns": [],
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
        ),
        (
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "removecolumns": REMOVE_COLUMNS,
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
            {
                "remove_domain": True,
                "domain_name": "example.com",
                "remove_columns": REMOVE_COLUMNS,
                "use_short_if_name": True,
                "one_neighbor_per_port": True,
            },
        ),
    ],
    ids=[
        "no removecolumns key is migrated to empty array",
        "remove_columns with proper value is not removed",
        "remove_columns with empty value is migrated to empty array",
        "removecolumns is migrated to remove_columns",
    ],
)
def test_migrate_cdp_cache(data: object, expected: Mapping[str, object]) -> None:
    migrated = _migrate_lldp_cache(data)
    assert migrated == expected
