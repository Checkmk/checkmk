#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Generator, NotRequired, TypedDict

from cmk.agent_based.v2 import Service, SNMPDetectSpecification, SNMPTree
from cmk.agent_based.v2.type_defs import DiscoveryResult

_DiscoveredParameters = Mapping | tuple | str | None


_DiscoveryFunctionLegacy = Callable[..., None | Iterable[tuple[str | None, _DiscoveredParameters]]]
_DiscoveryFunctionV2Compliant = Callable[..., DiscoveryResult]

_OptNumber = None | int | float

_MetricTuple = (
    tuple[str, float]
    | tuple[str, float, _OptNumber, _OptNumber]
    | tuple[str, float, _OptNumber, _OptNumber, _OptNumber, _OptNumber]
)

_SingleResult = tuple[int, str] | tuple[int, str, list[_MetricTuple]]


_CheckFunctionLegacy = Callable[
    ...,
    None | _SingleResult | Iterable[_SingleResult] | Generator[_SingleResult, None, None],
]
_CheckFunctionV2Compliant = Callable[..., Generator[Service, None, None]]


class LegacyCheckDefinition(TypedDict):
    detect: NotRequired[SNMPDetectSpecification]
    fetch: NotRequired[list[SNMPTree] | SNMPTree]
    sections: NotRequired[list[str]]
    check_function: NotRequired[_CheckFunctionV2Compliant | _CheckFunctionLegacy]
    discovery_function: NotRequired[_DiscoveryFunctionV2Compliant | _DiscoveryFunctionLegacy]
    parse_function: NotRequired[Callable[[list], object]]
    check_ruleset_name: NotRequired[str]
    check_default_parameters: NotRequired[Mapping[str, Any]]
    service_name: NotRequired[str]
