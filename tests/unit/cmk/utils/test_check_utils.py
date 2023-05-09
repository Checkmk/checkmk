#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import HostName

from cmk.checkers.checkresults import ServiceCheckResult


def test_cluster_received_no_data_no_nodes() -> None:
    assert ServiceCheckResult.cluster_received_no_data([]) == ServiceCheckResult(
        3,
        "Clustered service received no monitoring data (no nodes configured)",
    )


def test_cluster_received_no_data() -> None:
    assert ServiceCheckResult.cluster_received_no_data(
        [HostName("node1"), HostName("node2")]
    ) == ServiceCheckResult(
        3,
        "Clustered service received no monitoring data (configured nodes: node1, node2)",
    )
