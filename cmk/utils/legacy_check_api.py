#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Generator, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    DiscoveryResult,
    IgnoreResults,
    Metric,
    Result,
    SNMPDetectSpecification,
    SNMPTree,
)

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
_CheckFunctionV2Compliant = Callable[..., Generator[Result | Metric | IgnoreResults, None, None]]


@dataclass(frozen=True, kw_only=True)
class LegacyCheckDefinition:
    detect: SNMPDetectSpecification | None = None
    fetch: list[SNMPTree] | SNMPTree | None = None
    sections: list[str] | None = None
    check_function: _CheckFunctionV2Compliant | _CheckFunctionLegacy | None = None
    discovery_function: _DiscoveryFunctionV2Compliant | _DiscoveryFunctionLegacy | None = None
    parse_function: Callable[[list], object] | None = None
    check_ruleset_name: str | None = None
    check_default_parameters: Mapping[str, Any] | None = None
    service_name: str | None = None
