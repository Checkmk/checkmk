#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import HostAddress, HostKey, HostName, SourceType

from cmk.base.agent_based.checking import utils


def test_cluster_received_no_data_no_nodes() -> None:
    assert utils.cluster_received_no_data([]) == (
        3,
        "Clustered service received no monitoring data (no nodes configured)",
        [],
    )


def test_cluster_received_no_data() -> None:
    assert utils.cluster_received_no_data(
        [
            HostKey(HostName("node1"), HostAddress("1.2.3.4"), SourceType.HOST),
            HostKey(HostName("node2"), HostAddress("1.2.3.4"), SourceType.HOST),
        ]
    ) == (
        3,
        "Clustered service received no monitoring data (configured nodes: node1, node2)",
        [],
    )
