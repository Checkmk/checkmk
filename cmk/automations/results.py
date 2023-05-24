#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from ast import literal_eval
from collections.abc import Mapping, Sequence
from dataclasses import asdict, astuple, dataclass
from typing import Any, TypedDict, TypeVar

from cmk.utils import version as cmk_version
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.labels import HostLabel, HostLabelValueDict, Labels
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.plugin_registry import Registry
from cmk.utils.rulesets.ruleset_matcher import LabelSources, RulesetName
from cmk.utils.type_defs import AgentRawData, CheckPluginNameStr
from cmk.utils.type_defs import DiscoveryResult as SingleHostDiscoveryResult
from cmk.utils.type_defs import (
    Gateways,
    HostName,
    Item,
    LegacyCheckParameters,
    MetricTuple,
    NotifyAnalysisInfo,
    NotifyBulks,
    ParametersTypeAlias,
    ServiceDetails,
    ServiceName,
    ServiceState,
)

DiscoveredHostLabelsDict = dict[str, HostLabelValueDict]


class ResultTypeRegistry(Registry[type["ABCAutomationResult"]]):
    def plugin_name(self, instance: type[ABCAutomationResult]) -> str:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()


class SerializedResult(str):
    ...


_DeserializedType = TypeVar("_DeserializedType", bound="ABCAutomationResult")


@dataclass
class ABCAutomationResult(ABC):
    def serialize(
        self,
        for_cmk_version: cmk_version.Version,  # used to stay compatible with older central sites
    ) -> SerializedResult:
        return self._default_serialize()

    @classmethod
    def deserialize(
        cls: type[_DeserializedType],
        serialized_result: SerializedResult,
    ) -> _DeserializedType:
        return cls(*literal_eval(serialized_result))

    @staticmethod
    @abstractmethod
    def automation_call() -> str:
        ...

    def _default_serialize(self) -> SerializedResult:
        return SerializedResult(repr(astuple(self)))


@dataclass
class ServiceDiscoveryResult(ABCAutomationResult):
    hosts: Mapping[HostName, SingleHostDiscoveryResult]

    def _to_dict(self) -> Mapping[HostName, Mapping[str, Any]]:
        return {k: asdict(v) for k, v in self.hosts.items()}

    @staticmethod
    def _from_dict(
        serialized: Mapping[HostName, Mapping[str, Any]]
    ) -> Mapping[HostName, SingleHostDiscoveryResult]:
        return {k: SingleHostDiscoveryResult(**v) for k, v in serialized.items()}

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return SerializedResult(repr(self._to_dict()))

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> ServiceDiscoveryResult:
        return cls(cls._from_dict(literal_eval(serialized_result)))

    @staticmethod
    def automation_call() -> str:
        return "service-discovery"


result_type_registry.register(ServiceDiscoveryResult)


# Should be droped in 2.3
class DiscoveryPre22NameResult(ServiceDiscoveryResult):
    @staticmethod
    def automation_call() -> str:
        return "inventory"


result_type_registry.register(DiscoveryPre22NameResult)


@dataclass(frozen=True)
class CheckPreviewEntry:
    check_source: str
    check_plugin_name: str
    ruleset_name: RulesetName | None
    item: Item
    discovered_parameters: LegacyCheckParameters
    effective_parameters: LegacyCheckParameters
    description: str
    state: int | None
    output: str
    # Service discovery never uses the perfdata in the check table. That entry
    # is constantly discarded, yet passed around(back and forth) as part of the
    # discovery result in the request elements. Some perfdata VALUES are not parsable
    # by ast.literal_eval such as "inf" it lead to ValueErrors. Thus keep perfdata empty
    metrics: list[MetricTuple]
    labels: dict[str, str]
    found_on_nodes: list[HostName]


@dataclass
class ServiceDiscoveryPreviewResult(ABCAutomationResult):
    output: str
    check_table: Sequence[CheckPreviewEntry]
    host_labels: DiscoveredHostLabelsDict
    new_labels: DiscoveredHostLabelsDict
    vanished_labels: DiscoveredHostLabelsDict
    changed_labels: DiscoveredHostLabelsDict
    labels_by_host: Mapping[HostName, Sequence[HostLabel]]
    source_results: Mapping[str, tuple[int, str]]

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        if for_cmk_version < cmk_version.Version.from_str(
            "2.1.0p27"
        ):  # no source results, no labels by host
            return SerializedResult(repr(astuple(self)[:6]))

        if for_cmk_version < cmk_version.Version.from_str(
            "2.2.0b1"
        ):  # labels by host, but no source results
            return self._serialize_as_dict()

        if for_cmk_version < cmk_version.Version.from_str(
            "2.2.0b2"
        ):  # no source results, no labels by host
            return SerializedResult(repr(astuple(self)[:6]))

        if for_cmk_version < cmk_version.Version.from_str(
            "2.2.0b6"
        ):  # source_results, no labels by host
            return SerializedResult(repr(astuple(self)[:6] + (self.source_results,)))

        return self._serialize_as_dict()

    def _serialize_as_dict(self) -> SerializedResult:
        raw = asdict(self)
        return SerializedResult(
            repr(
                {
                    **raw,
                    "labels_by_host": {
                        str(host_name): [label.serialize() for label in labels]
                        for host_name, labels in self.labels_by_host.items()
                    },
                }
            )
        )

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> ServiceDiscoveryPreviewResult:
        raw = literal_eval(serialized_result)
        return cls(
            output=raw["output"],
            check_table=[CheckPreviewEntry(**cpe) for cpe in raw["check_table"]],
            host_labels=raw["host_labels"],
            new_labels=raw["new_labels"],
            vanished_labels=raw["vanished_labels"],
            changed_labels=raw["changed_labels"],
            labels_by_host={
                HostName(raw_host_name): [
                    HostLabel.deserialize(raw_label) for raw_label in raw_host_labels
                ]
                for raw_host_name, raw_host_labels in raw["labels_by_host"].items()
            },
            source_results=raw["source_results"],
        )

    @staticmethod
    def automation_call() -> str:
        return "service-discovery-preview"


result_type_registry.register(ServiceDiscoveryPreviewResult)


# Should be droped in 2.3
class DiscoveryPreviewPre22NameResult(ServiceDiscoveryPreviewResult):
    @staticmethod
    def automation_call() -> str:
        return "try-inventory"


result_type_registry.register(DiscoveryPreviewPre22NameResult)


@dataclass
class AutodiscoveryResult(ABCAutomationResult):
    hosts: Mapping[HostName, SingleHostDiscoveryResult]
    changes_activated: bool

    def _hosts_to_dict(self) -> Mapping[HostName, Mapping[str, Any]]:
        return {k: asdict(v) for k, v in self.hosts.items()}

    @staticmethod
    def _hosts_from_dict(
        serialized: Mapping[HostName, Mapping[str, Any]]
    ) -> Mapping[HostName, SingleHostDiscoveryResult]:
        return {k: SingleHostDiscoveryResult(**v) for k, v in serialized.items()}

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return SerializedResult(repr((self._hosts_to_dict(), self.changes_activated)))

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> AutodiscoveryResult:
        hosts, changes_activated = literal_eval(serialized_result)
        return cls(cls._hosts_from_dict(hosts), changes_activated)

    @staticmethod
    def automation_call() -> str:
        return "autodiscovery"


result_type_registry.register(AutodiscoveryResult)


@dataclass
class SetAutochecksResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> str:
        return "set-autochecks"


result_type_registry.register(SetAutochecksResult)


SetAutochecksTable = dict[
    tuple[str, Item], tuple[ServiceName, LegacyCheckParameters, Labels, list[HostName]]
]
SetAutochecksTablePre20 = dict[tuple[str, Item], tuple[dict[str, Any], Labels]]


@dataclass
class UpdateHostLabelsResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> str:
        return "update-host-labels"


result_type_registry.register(UpdateHostLabelsResult)


@dataclass
class RenameHostsResult(ABCAutomationResult):
    action_counts: Mapping[str, int]

    @staticmethod
    def automation_call() -> str:
        return "rename-hosts"


result_type_registry.register(RenameHostsResult)


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
    def automation_call() -> str:
        return "analyse-service"


result_type_registry.register(AnalyseServiceResult)


@dataclass
class GetServicesLabelsResult(ABCAutomationResult):
    labels: Mapping[ServiceName, Labels]

    @staticmethod
    def automation_call() -> str:
        return "get-services-labels"


result_type_registry.register(GetServicesLabelsResult)


@dataclass
class AnalyseHostResult(ABCAutomationResult):
    labels: Labels
    label_sources: LabelSources

    @staticmethod
    def automation_call() -> str:
        return "analyse-host"


result_type_registry.register(AnalyseHostResult)


@dataclass
class DeleteHostsResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> str:
        return "delete-hosts"


result_type_registry.register(DeleteHostsResult)


@dataclass
class DeleteHostsKnownRemoteResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> str:
        return "delete-hosts-known-remote"


result_type_registry.register(DeleteHostsKnownRemoteResult)


@dataclass
class RestartResult(ABCAutomationResult):
    config_warnings: ConfigurationWarnings

    @staticmethod
    def automation_call() -> str:
        return "restart"


result_type_registry.register(RestartResult)


@dataclass
class ReloadResult(RestartResult):
    @staticmethod
    def automation_call() -> str:
        return "reload"


result_type_registry.register(ReloadResult)


@dataclass
class GetConfigurationResult(ABCAutomationResult):
    result: Mapping[str, Any]

    @staticmethod
    def automation_call() -> str:
        return "get-configuration"


result_type_registry.register(GetConfigurationResult)


@dataclass
class GetCheckInformationResult(ABCAutomationResult):
    plugin_infos: Mapping[CheckPluginNameStr, Mapping[str, Any]]

    @staticmethod
    def automation_call() -> str:
        return "get-check-information"


result_type_registry.register(GetCheckInformationResult)


@dataclass
class GetSectionInformationResult(ABCAutomationResult):
    section_infos: Mapping[str, Mapping[str, str]]

    @staticmethod
    def automation_call() -> str:
        return "get-section-information"


result_type_registry.register(GetSectionInformationResult)


@dataclass
class ScanParentsResult(ABCAutomationResult):
    gateways: Gateways

    @staticmethod
    def automation_call() -> str:
        return "scan-parents"


result_type_registry.register(ScanParentsResult)


@dataclass
class DiagHostResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> str:
        return "diag-host"


result_type_registry.register(DiagHostResult)


@dataclass
class ActiveCheckResult(ABCAutomationResult):
    state: ServiceState | None
    output: ServiceDetails

    @staticmethod
    def automation_call() -> str:
        return "active-check"


result_type_registry.register(ActiveCheckResult)


@dataclass
class UpdateDNSCacheResult(ABCAutomationResult):
    n_updated: int
    failed_hosts: Sequence[HostName]

    @staticmethod
    def automation_call() -> str:
        return "update-dns-cache"


result_type_registry.register(UpdateDNSCacheResult)


@dataclass
class GetAgentOutputResult(ABCAutomationResult):
    success: bool
    service_details: ServiceDetails
    raw_agent_data: AgentRawData

    @staticmethod
    def automation_call() -> str:
        return "get-agent-output"


result_type_registry.register(GetAgentOutputResult)


@dataclass
class NotificationReplayResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> str:
        return "notification-replay"


result_type_registry.register(NotificationReplayResult)


@dataclass
class NotificationAnalyseResult(ABCAutomationResult):
    result: NotifyAnalysisInfo | None

    @staticmethod
    def automation_call() -> str:
        return "notification-analyse"


result_type_registry.register(NotificationAnalyseResult)


@dataclass
class NotificationGetBulksResult(ABCAutomationResult):
    result: NotifyBulks

    @staticmethod
    def automation_call() -> str:
        return "notification-get-bulks"


result_type_registry.register(NotificationGetBulksResult)


@dataclass
class CreateDiagnosticsDumpResult(ABCAutomationResult):
    output: str
    tarfile_path: str
    tarfile_created: bool

    @staticmethod
    def automation_call() -> str:
        return "create-diagnostics-dump"


result_type_registry.register(CreateDiagnosticsDumpResult)


@dataclass
class BakeAgentsResult(ABCAutomationResult):
    warnings_as_json: str

    @staticmethod
    def automation_call() -> str:
        return "bake-agents"


result_type_registry.register(BakeAgentsResult)
