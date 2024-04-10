#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.agent_based.v2 import DiscoveryResult, Service

_ItemData = dict
Section = Mapping[str, _ItemData]


def discover_key(key: str) -> Callable[[Section], DiscoveryResult]:
    def _discover_bound_key(section: Section) -> DiscoveryResult:
        yield from (Service(item=item) for item, data in section.items() if key in data)

    return _discover_bound_key
