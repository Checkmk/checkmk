#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.netapp_volumes import parse_netapp_volumes

STRING_TABLE_FILER_NETAPP_8_1_1 = [
    ["vol0", "23465813", "1", "online", "raid_dp, 64-bit, rlw_on"],
    ["lun_29Aug2012_162910_vol", "1885979353", "1", "offline", "raid_dp, 64-bit, rlw_on"],
    ["a2_esx_zit_g7_00", "1597710601", "1", "online", ""],
    ["a2_lika_vol0", "102390877", "1", "online", "raid_dp, 64-bit, rlw_on"],
    ["a2_nfs_lika_ans", "614473649", "1", "online", "raid_dp, 64-bit, rlw_on"],
    ["a2_nfs_lika_backup", "786320752", "1", "online", "raid_dp, 64-bit, rlw_on"],
]


@pytest.fixture(name="netapp_volumes_plugin")
def fixture_netapp_volumes_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("netapp_volumes")]


def test_inventory(
    netapp_volumes_plugin: CheckPlugin,
) -> None:
    assert (
        list(
            netapp_volumes_plugin.discovery_function(
                section=parse_netapp_volumes(STRING_TABLE_FILER_NETAPP_8_1_1),
            )
        )
    ) == [
        Service(item="vol0"),
        Service(item="lun_29Aug2012_162910_vol"),
        Service(item="a2_esx_zit_g7_00"),
        Service(item="a2_lika_vol0"),
        Service(item="a2_nfs_lika_ans"),
        Service(item="a2_nfs_lika_backup"),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "vol0",
            [
                Result(
                    state=State.OK,
                    summary="FSID: 23465813, Owner: local, State: online, Status: raid_dp, 64-bit, rlw_on",
                ),
            ],
            id="everything ok",
        ),
        pytest.param(
            "lun_29Aug2012_162910_vol",
            [
                Result(
                    state=State.WARN,
                    summary="FSID: 1885979353, Owner: local, State: offline(!), Status: raid_dp, 64-bit, rlw_on",
                ),
            ],
            id="state offline - warn",
        ),
        pytest.param(
            "a2_esx_zit_g7_00",
            [
                Result(
                    state=State.CRIT,
                    summary="FSID: 1597710601, Owner: local, State: online, Status: (!!)",
                ),
            ],
            id="status empty - crit",
        ),
        pytest.param(
            "I_am_not_a_real_volume",
            [],
            id="unknown volume",
        ),
    ],
)
def test_check(
    netapp_volumes_plugin: CheckPlugin,
    item: str,
    expected_result: Sequence[Result],
) -> None:
    assert (
        list(
            netapp_volumes_plugin.check_function(
                item=item,
                params={},
                section=parse_netapp_volumes(STRING_TABLE_FILER_NETAPP_8_1_1),
            )
        )
        == expected_result
    )
