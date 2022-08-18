#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Service
from cmk.base.plugins.agent_based.utils.scaleio import ScaleioSection


@pytest.mark.parametrize(
    "parsed_section, discovered_services",
    [
        pytest.param(
            {
                "4e9a44c700000000": {
                    "ID": ["4e9a44c700000000"],
                    "NAME": ["pool01"],
                }
            },
            [Service(item="4e9a44c700000000")],
            id="A service is created for each storage pool that is present in the parsed section",
        ),
        pytest.param(
            {},
            [],
            id="If no storage pool is present in the parsed section, no services are discovered",
        ),
    ],
)
def test_inventory_scaleio_storage_pool(
    parsed_section: ScaleioSection,
    discovered_services: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool_totalrw")]
    assert list(check.discovery_function(parsed_section)) == discovered_services
