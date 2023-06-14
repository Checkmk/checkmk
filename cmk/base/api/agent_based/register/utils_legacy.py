#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping
from typing import Any, NotRequired, TypedDict

from cmk.base.api.agent_based.checking_classes import Service
from cmk.base.api.agent_based.section_classes import SNMPTree

from ..section_classes import SNMPDetectSpecification

_DiscoveredParameters = Mapping | tuple | str | None


class LegacyCheckDefinition(TypedDict):
    detect: NotRequired[SNMPDetectSpecification]
    fetch: NotRequired[list[SNMPTree] | SNMPTree]
    check_function: NotRequired[Callable]
    discovery_function: NotRequired[
        Callable[..., None | Iterable[tuple[str | None, _DiscoveredParameters]] | Iterable[Service]]
    ]
    parse_function: NotRequired[Callable[[list], object]]
    check_ruleset_name: NotRequired[str]
    check_default_parameters: NotRequired[Mapping[str, Any]]
    service_name: NotRequired[str]
