#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"


from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Final, NamedTuple

from cmk.agent_based.v2 import IgnoreResults, Metric, Result, Service
from cmk.agent_based.v3_unstable import Metric as MetricV3Unstable
from cmk.agent_based.v3_unstable import ParseFailure
from cmk.discover_plugins import PluginLocation
from cmk.ruleset_matcher.ruleset_name import RuleSetName
from cmk.utils.servicename import Item

from ._common import RuleSetTypeName
from ._sections import ParsedSectionName


@dataclass(frozen=True)
class ReportedParseFailure:
    """A parse failure that the results already account for, and that is only reported

    When a check function yields a ParseFailure, the check engine replaces it by an
    UNKNOWN result followed by this, so that the failure still ends up in the crash
    report.
    """

    failure: ParseFailure


type FinalCheckResult = Iterable[
    IgnoreResults | Metric | Result | MetricV3Unstable | ReportedParseFailure
]
type FinalCheckFunction = Callable[..., FinalCheckResult]
type FinalDiscoveryResult = Iterable[Service]
type FinalDiscoveryFunction = Callable[..., FinalDiscoveryResult]


class CheckPluginName(str):
    MANAGEMENT_PREFIX: Final = "mgmt_"

    def is_management_name(self) -> bool:
        return self.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> CheckPluginName:
        if self.is_management_name():
            return self
        return CheckPluginName(f"{self.MANAGEMENT_PREFIX}{self}")

    def create_basic_name(self) -> CheckPluginName:
        if self.is_management_name():
            return CheckPluginName(self[len(self.MANAGEMENT_PREFIX) :])
        return self


class CheckPlugin(NamedTuple):
    name: CheckPluginName
    sections: list[ParsedSectionName]
    service_name: str
    discovery_function: FinalDiscoveryFunction
    discovery_default_parameters: Mapping[str, object] | None
    discovery_ruleset_name: RuleSetName | None
    discovery_ruleset_type: RuleSetTypeName
    check_function: FinalCheckFunction
    check_default_parameters: Mapping[str, object] | None
    check_ruleset_name: RuleSetName | None
    cluster_check_function: FinalCheckFunction | None
    location: PluginLocation


class ServiceID(NamedTuple):
    name: CheckPluginName
    item: Item
