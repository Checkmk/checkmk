#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_checkpoint_vpn_tunnels import (
    inventory_checkpoint_vpn_tunnels,
    parse_checkpoint_vpn_tunnels,
)


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        ([], []),
        (
            [
                ["1.2.3.41", "5.6.7.81", "peer name 1", "tunnel interface 1", "0"],
                ["1.2.3.42", "5.6.7.82", "peer name 2", "tunnel interface 2", "1"],
                ["1.2.3.43", "5.6.7.83", "peer name 3", "tunnel interface 3", "2"],
            ],
            [
                TableRow(
                    path=["networking", "tunnels"],
                    key_columns={
                        "peername": "peer name 1",
                    },
                    inventory_columns={
                        "index": 1,
                        "peerip": "1.2.3.41",
                        "sourceip": "5.6.7.81",
                        "tunnelinterface": "tunnel interface 1",
                        "linkpriority": "Primary",
                    },
                ),
                TableRow(
                    path=["networking", "tunnels"],
                    key_columns={
                        "peername": "peer name 2",
                    },
                    inventory_columns={
                        "index": 2,
                        "peerip": "1.2.3.42",
                        "sourceip": "5.6.7.82",
                        "tunnelinterface": "tunnel interface 2",
                        "linkpriority": "Backup",
                    },
                ),
                TableRow(
                    path=["networking", "tunnels"],
                    key_columns={
                        "peername": "peer name 3",
                    },
                    inventory_columns={
                        "index": 3,
                        "peerip": "1.2.3.43",
                        "sourceip": "5.6.7.83",
                        "tunnelinterface": "tunnel interface 3",
                        "linkpriority": "On-demand",
                    },
                ),
            ],
        ),
    ],
)
def test_inv_aix_baselevel(raw_section, expected_result):
    assert (
        list(inventory_checkpoint_vpn_tunnels(parse_checkpoint_vpn_tunnels(raw_section)))
        == expected_result
    )
