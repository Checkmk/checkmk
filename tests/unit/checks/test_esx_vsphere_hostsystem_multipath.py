#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from cmk.base.plugins.agent_based.utils.esx_vsphere import Section

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "section, item, check_results",
    [
        (
            Section(
                [
                    (
                        "config.storageDevice.multipathInfo",
                        [
                            "73854743",
                            "bla1:A0:B7:C0",
                            "active",
                            "8390487493837394957202736469161739476594",
                            "bla3:A0:B0:C0",
                            "active",
                            "bla3:A0:B2:C0",
                            "active",
                            "52436384763283284389549439394844",
                            "bla2:A0:B2:C21",
                            "active",
                            "52436384763283284389549439394844",
                            "bla4:A0:B0:C21",
                            "active",
                            "52436384763283284389549439394844",
                            "bla4:A0:B1:C21",
                            "active",
                            "52436384763283284389549439394844",
                            "bla2:A0:B0:C21",
                            "active",
                        ],
                    ),
                ]
            ),
            "bla2:A0:B2:C21",
            [
                0,
                "0 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nactive",
            ],
        ),
        (
            Section(
                [
                    (
                        "config.storageDevice.multipathInfo",
                        [],
                    ),
                ]
            ),
            "52436384763283284389549439394844",
            [],
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_multipath(section, item, check_results):
    check = Check("esx_vsphere_hostsystem.multipath")
    assert list(check.run_check(item, {}, section) or ()) == check_results
