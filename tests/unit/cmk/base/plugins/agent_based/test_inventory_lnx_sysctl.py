#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_lnx_sysctl import inventory_lnx_sysctl, parse_lnx_sysctl

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "info, params, inventory_data",
    [
        (
            [],
            {},
            [],
        ),
        (
            [
                ["abi.vsyscall32", "=", "1"],
            ],
            {},
            [],
        ),
        (
            [],
            {
                "include_patterns": [".*"],
            },
            [],
        ),
        (
            [
                ["abi.vsyscall32", "=", "1"],
                [
                    "dev.cdrom.info",
                    "=",
                    "CD-ROM",
                    "information,",
                    "Id:",
                    "cdrom.c",
                    "3.20",
                    "2003/12/17",
                ],
                ["dev.cdrom.info", "="],
                ["dev.cdrom.info", "=", "drive", "name:"],
                ["dev.cdrom.info", "=", "drive", "speed:"],
                ["dev.cdrom.info", "=", "drive", "#", "of", "slots:"],
                ["dev.cdrom.info", "="],
                ["dev.cdrom.info", "="],
                ["dev.hpet.max-user-freq", "=", "64"],
                ["kernel.hotplug", "="],
                ["kernel.hung_task_check_count", "=", "4194304"],
            ],
            {
                "include_patterns": [".*"],
                "exclude_patterns": ["kernel.hotplug"],
            },
            [
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "abi.vsyscall32",
                        "value": "1",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "dev.cdrom.info",
                        "value": "",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "dev.cdrom.info",
                        "value": "CD-ROM information, Id: cdrom.c 3.20 2003/12/17",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "dev.cdrom.info",
                        "value": "drive # of slots:",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "dev.cdrom.info",
                        "value": "drive name:",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "dev.cdrom.info",
                        "value": "drive speed:",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "dev.hpet.max-user-freq",
                        "value": "64",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": "kernel.hung_task_check_count",
                        "value": "4194304",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
            ],
        ),
        (
            [
                ["abi.vsyscall32", "=", "1"],
                [
                    "dev.cdrom.info",
                    "=",
                    "CD-ROM",
                    "information,",
                    "Id:",
                    "cdrom.c",
                    "3.20",
                    "2003/12/17",
                ],
                ["dev.cdrom.info", "="],
                ["dev.cdrom.info", "=", "drive", "name:"],
                ["dev.cdrom.info", "=", "drive", "speed:"],
                ["dev.cdrom.info", "=", "drive", "#", "of", "slots:"],
                ["dev.cdrom.info", "="],
                ["dev.cdrom.info", "="],
                ["dev.hpet.max-user-freq", "=", "64"],
                ["kernel.hotplug", "="],
                ["kernel.hung_task_check_count", "=", "4194304"],
            ],
            {
                "include_patterns": [".*"],
                "exclude_patterns": [".*"],
            },
            [],
        ),
    ],
)
def test_inv_oracle_systemparameter(info, params, inventory_data) -> None:
    assert sort_inventory_result(
        inventory_lnx_sysctl(params, parse_lnx_sysctl(info))
    ) == sort_inventory_result(inventory_data)
