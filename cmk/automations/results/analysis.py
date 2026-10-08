#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Host/service introspection and rule-matching results.

Groups all "tell me about this host, service, or rule" query automations
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import override, TypedDict

from cmk.automations.internal import AutomationID, AutomationResult
from cmk.checkengine.specs.checkresults import ServiceState
from cmk.checkengine.specs.parameters import TimespecificParametersPreview
from cmk.checkengine.submitters import ServiceDetails
from cmk.ruleset_matcher.labels import Labels, LabelSources
from cmk.ruleset_matcher.matcher import RulesetName
from cmk.utils.servicename import Item, ServiceName


class ServiceInfo(TypedDict, total=False):
    origin: str
    checkgroup: RulesetName
    checktype: str
    item: Item
    inv_parameters: Mapping[str, object]
    factory_settings: Mapping[str, object] | None
    parameters: TimespecificParametersPreview | Mapping[str, object]
    command_line: str


@dataclass
class AnalyseServiceResult(AutomationResult):
    service_info: ServiceInfo
    labels: Labels
    label_sources: LabelSources

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("analyse-service")


@dataclass
class GetServicesLabelsResult(AutomationResult):
    labels: Mapping[ServiceName, Labels]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-services-labels")


@dataclass
class GetServiceNameResult(AutomationResult):
    service_name: str

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-service-name")


@dataclass
class AnalyseHostResult(AutomationResult):
    labels: Labels
    label_sources: LabelSources

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("analyse-host")


@dataclass
class AnalyzeHostRuleMatchesResult(AutomationResult):
    results: dict[str, list[object]]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("analyze-host-rule-matches")


@dataclass
class AnalyzeServiceRuleMatchesResult(AutomationResult):
    results: dict[str, list[object]]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("analyze-service-rule-matches")


@dataclass
class AnalyzeHostRuleEffectivenessResult(AutomationResult):
    results: dict[str, bool]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("analyze-host-rule-effectiveness")


@dataclass
class ActiveCheckResult(AutomationResult):
    state: ServiceState | None
    output: ServiceDetails

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("active-check")


@dataclass
class UnknownCheckParameterRuleSetsResult(AutomationResult):
    result: Sequence[str]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("find-unknown-check-parameter-rule-sets")
