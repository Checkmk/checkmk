#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Host/service introspection and rule-matching results.

Groups all "tell me about this host, service, or rule" query automations
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict

from cmk.automations.results._base import (
    ABCAutomationResult,
    result_type_registry,
    SerializedResult,
)
from cmk.ccc import version as cmk_version
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.submitters import ServiceDetails, ServiceState
from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.labels import Labels, LabelSources
from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.servicename import Item, ServiceName

from ..types import AutomationID


class ServiceInfo(TypedDict, total=False):
    origin: str
    checkgroup: RulesetName
    checktype: str
    item: Item
    inv_parameters: LegacyCheckParameters
    factory_settings: ParametersTypeAlias | None
    parameters: TimespecificParameters | LegacyCheckParameters
    command_line: str


@dataclass
class AnalyseServiceResult(ABCAutomationResult):
    service_info: ServiceInfo
    labels: Labels
    label_sources: LabelSources

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        if for_cmk_version >= cmk_version.Version.from_str("2.2.0i1"):
            return self._default_serialize()
        previous_serialized: Mapping[str, object] = {
            **self.service_info,
            "labels": self.labels,
            "label_sources": self.label_sources,
        }
        return SerializedResult(repr((previous_serialized,)))

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("analyse-service")


result_type_registry.register(AnalyseServiceResult)


@dataclass
class GetServicesLabelsResult(ABCAutomationResult):
    labels: Mapping[ServiceName, Labels]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("get-services-labels")


result_type_registry.register(GetServicesLabelsResult)


@dataclass
class GetServiceNameResult(ABCAutomationResult):
    service_name: str

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("get-service-name")


result_type_registry.register(GetServiceNameResult)


@dataclass
class AnalyseHostResult(ABCAutomationResult):
    labels: Labels
    label_sources: LabelSources

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("analyse-host")


result_type_registry.register(AnalyseHostResult)


@dataclass
class AnalyzeHostRuleMatchesResult(ABCAutomationResult):
    results: dict[str, list[object]]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("analyze-host-rule-matches")


result_type_registry.register(AnalyzeHostRuleMatchesResult)


@dataclass
class AnalyzeServiceRuleMatchesResult(ABCAutomationResult):
    results: dict[str, list[object]]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("analyze-service-rule-matches")


result_type_registry.register(AnalyzeServiceRuleMatchesResult)


@dataclass
class AnalyzeHostRuleEffectivenessResult(ABCAutomationResult):
    results: dict[str, bool]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("analyze-host-rule-effectiveness")


result_type_registry.register(AnalyzeHostRuleEffectivenessResult)


@dataclass
class ActiveCheckResult(ABCAutomationResult):
    state: ServiceState | None
    output: ServiceDetails

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("active-check")


result_type_registry.register(ActiveCheckResult)


@dataclass
class UnknownCheckParameterRuleSetsResult(ABCAutomationResult):
    result: Sequence[str]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("find-unknown-check-parameter-rule-sets")


result_type_registry.register(UnknownCheckParameterRuleSetsResult)
