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
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.labels import HostLabel, HostLabelValueDict, Labels, LabelSources
from cmk.utils.notify_types import NotifyAnalysisInfo, NotifyBulks
from cmk.utils.plugin_registry import Registry
from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.servicename import Item, ServiceName

from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.checkengine.discovery import DiscoveryResult as SingleHostDiscoveryResult
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.submitters import ServiceDetails, ServiceState

DiscoveredHostLabelsDict = dict[str, HostLabelValueDict]


class ResultTypeRegistry(Registry[type["ABCAutomationResult"]]):
    def plugin_name(self, instance: type[ABCAutomationResult]) -> str:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()


class SerializedResult(str): ...


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
    def automation_call() -> str: ...

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


@dataclass
class ServiceDiscoveryPreviewResult(ABCAutomationResult):
    output: str
    check_table: Sequence[CheckPreviewEntry]
    nodes_check_table: Mapping[HostName, Sequence[CheckPreviewEntry]]
    host_labels: DiscoveredHostLabelsDict
    new_labels: DiscoveredHostLabelsDict
    vanished_labels: DiscoveredHostLabelsDict
    changed_labels: DiscoveredHostLabelsDict
    labels_by_host: Mapping[HostName, Sequence[HostLabel]]
    source_results: Mapping[str, tuple[int, str]]

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        if for_cmk_version < cmk_version.Version.from_str("2.4.0b1"):
            raw = asdict(self)
            raw.pop("nodes_check_table")
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
            nodes_check_table={
                HostName(h): [CheckPreviewEntry(**cpe) for cpe in entries]
                for h, entries in raw["nodes_check_table"].items()
            },
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
    tuple[str, Item], tuple[ServiceName, Mapping[str, object], Labels, list[HostName]]
]


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
    plugin_infos: Mapping[str, Mapping[str, Any]]

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


@dataclass(frozen=True)
class Gateway:
    existing_gw_host_name: HostName | None
    ip: HostAddress
    dns_name: HostName | None


@dataclass(frozen=True)
class GatewayResult:
    gateway: Gateway | None
    state: str
    ping_fails: int
    message: str


@dataclass
class ScanParentsResult(ABCAutomationResult):
    results: Sequence[GatewayResult]

    @staticmethod
    def automation_call() -> str:
        return "scan-parents"

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> ScanParentsResult:
        (serialized_results,) = literal_eval(serialized_result)
        results = [
            GatewayResult(
                gateway=Gateway(*gw) if gw else None,
                state=state,
                ping_fails=ping_fails,
                message=message,
            )
            for gw, state, ping_fails, message in serialized_results
        ]
        return cls(results=results)


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
class UpdatePasswordsMergedFileResult(ABCAutomationResult):

    @staticmethod
    def automation_call() -> str:
        return "update-passwords-merged-file"


result_type_registry.register(UpdatePasswordsMergedFileResult)


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
class NotificationTestResult(ABCAutomationResult):
    result: NotifyAnalysisInfo | None

    @staticmethod
    def automation_call() -> str:
        return "notification-test"


result_type_registry.register(NotificationTestResult)


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
    output: str | None

    @staticmethod
    def automation_call() -> str:
        return "bake-agents"


result_type_registry.register(BakeAgentsResult)
