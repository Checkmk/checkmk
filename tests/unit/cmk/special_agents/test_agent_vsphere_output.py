#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.special_agents.agent_vsphere import eval_multipath_info
import pytest


def _build_id(lun_id):
    # Taken from https://kb.vmware.com/s/article/2078730
    assert len(lun_id) == 32 or len(lun_id) == 0
    uuid_type = "02"
    device_type = "00"
    lun_number = "00"
    reserved = "0000"
    unique_hash = "695343534944"

    return f"{uuid_type}{device_type}{lun_number}{reserved}{lun_id}{unique_hash}"


VALID_LUN_ID = "12344a12345b4b0000333a4b00000320"
VALID_PATH = "aaaaa1:AA:AA:AA"
MULTIPATH_PROPSET = ('<id>%s</id>'
                     '<path>'
                     f'<key>key-vim.host.MultipathInfo.Path-{VALID_PATH}</key>'
                     f'<name>{VALID_PATH}</name>'
                     '<pathState>active</pathState>'
                     '<state>active</state>'
                     '<isWorkingPath>true</isWorkingPath>'
                     '<adapter>key-vim.host.BlockHba-vmhba2</adapter>'
                     '<lun>key-vim.host.MultipathInfo.LogicalUnit-123456789</lun>'
                     '<transport xsi:type="HostBlockAdapterTargetTransport"></transport>'
                     '</path>')
PROP_NAME = "foo"


@pytest.mark.parametrize("propset, expected", [
    (
        MULTIPATH_PROPSET % _build_id(VALID_LUN_ID),
        ({
            PROP_NAME: [f'{VALID_LUN_ID} {VALID_PATH} active']
        }, {}),
    ),
    (
        MULTIPATH_PROPSET % _build_id(""),
        ({}, {}),
    ),
])
def test_eval_multipath_info(propset, expected):
    assert eval_multipath_info("", PROP_NAME, propset) == expected
