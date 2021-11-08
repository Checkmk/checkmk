#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional, Sequence, Tuple

from cmk.utils.type_defs import HostKey, ServiceCheckResult


class AggregatedResult(NamedTuple):
    submit: bool
    data_received: bool
    result: ServiceCheckResult
    cache_info: Optional[Tuple[int, int]]


ITEM_NOT_FOUND: ServiceCheckResult = (3, "Item not found in monitoring data", [])

RECEIVED_NO_DATA: ServiceCheckResult = (3, "Check plugin received no monitoring data", [])

CHECK_NOT_IMPLEMENTED: ServiceCheckResult = (3, "Check plugin not implemented", [])


def cluster_received_no_data(node_keys: Sequence[HostKey]) -> ServiceCheckResult:
    node_hint = (
        f"configured nodes: {', '.join(nk.hostname for nk in node_keys)}"
        if node_keys
        else "no nodes configured"
    )
    return (
        3,
        f"Clustered service received no monitoring data ({node_hint})",
        [],
    )
