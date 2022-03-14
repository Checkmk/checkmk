#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from ast import literal_eval
from dataclasses import asdict, astuple, dataclass
from typing import Any, List, Literal, Mapping, Optional, Sequence, Tuple, Type, TypeVar

from cmk.utils.plugin_registry import Registry
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginNameStr,
    ConfigurationWarnings,
    DiscoveredHostLabelsDict,
)
from cmk.utils.type_defs import DiscoveryResult as SingleHostDiscoveryResult
from cmk.utils.type_defs import (
    Gateways,
    HostName,
    Item,
    Labels,
    LabelSources,
    LegacyCheckParameters,
    MetricTuple,
    NotifyAnalysisInfo,
    NotifyBulks,
    RulesetName,
    ServiceDetails,
    ServiceState,
)
from cmk.utils.type_defs import UpdateDNSCacheResult as UpdateDNSCacheResultRaw


class ResultTypeRegistry(Registry[Type["ABCAutomationResult"]]):
    def plugin_name(self, instance: Type["ABCAutomationResult"]) -> str:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()


class SerializedResult(str):
    ...


_DeserializedType = TypeVar("_DeserializedType", bound="ABCAutomationResult")


@dataclass  # type: ignore[misc]  # https://github.com/python/mypy/issues/5374
class ABCAutomationResult(ABC):
    def serialize(self) -> SerializedResult:
        return SerializedResult(repr(astuple(self)))

    def to_pre_21(self) -> object:
        # Needed to support remote automation calls from an old central site to a new remote site.
        # In such cases, we must send the result in a format understood by the old central site.
        return astuple(self)[0]

    @classmethod
    def deserialize(
        cls: Type[_DeserializedType],
        serialized_result: SerializedResult,
    ) -> _DeserializedType:
        return cls(*literal_eval(serialized_result))

    @staticmethod
    @abstractmethod
    def automation_call() -> str:
        ...


@dataclass
class DiscoveryResult(ABCAutomationResult):
    hosts: Mapping[HostName, SingleHostDiscoveryResult]

    def _to_dict(self) -> Mapping[HostName, Mapping[str, Any]]:
        return {k: asdict(v) for k, v in self.hosts.items()}

    @staticmethod
    def _from_dict(
        serialized: Mapping[HostName, Mapping[str, Any]]
    ) -> Mapping[HostName, SingleHostDiscoveryResult]:
        return {k: SingleHostDiscoveryResult(**v) for k, v in serialized.items()}

    def serialize(self) -> SerializedResult:
        return SerializedResult(repr(self._to_dict()))

    def to_pre_21(self) -> Mapping[Literal["results"], Mapping[HostName, Mapping[str, Any]]]:
        return {"results": self._to_dict()}

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> "DiscoveryResult":
        return cls(cls._from_dict(literal_eval(serialized_result)))

    @staticmethod
    def automation_call() -> str:
        return "inventory"


result_type_registry.register(DiscoveryResult)


@dataclass(frozen=True)
class CheckPreviewEntry:
    check_source: str
    check_plugin_name: str
    ruleset_name: Optional[RulesetName]
    item: Item
    discovered_parameters: LegacyCheckParameters
    effective_parameters: LegacyCheckParameters
    description: str
    state: Optional[int]
    output: str
    metrics: List[MetricTuple]
    labels: dict[str, str]
    found_on_nodes: List[HostName]


@dataclass
class TryDiscoveryResult(ABCAutomationResult):
    output: str
    check_table: Sequence[CheckPreviewEntry]
    host_labels: DiscoveredHostLabelsDict
    new_labels: DiscoveredHostLabelsDict
    vanished_labels: DiscoveredHostLabelsDict
    changed_labels: DiscoveredHostLabelsDict

    def to_pre_21(self) -> Mapping[str, Any]:
        return asdict(self)

    def serialize(self) -> SerializedResult:
        return SerializedResult(repr(astuple(self)))

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> "TryDiscoveryResult":
        raw_output, raw_check_table, *raw_rest = literal_eval(serialized_result)
        return cls(raw_output, [CheckPreviewEntry(*cpe) for cpe in raw_check_table], *raw_rest)

    @staticmethod
    def automation_call() -> str:
        return "try-inventory"


result_type_registry.register(TryDiscoveryResult)


@dataclass
class SetAutochecksResult(ABCAutomationResult):
    def to_pre_21(self) -> None:
        return None

    @staticmethod
    def automation_call() -> str:
        return "set-autochecks"


result_type_registry.register(SetAutochecksResult)


@dataclass
class UpdateHostLabelsResult(ABCAutomationResult):
    def to_pre_21(self) -> None:
        return None

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


@dataclass
class AnalyseServiceResult(ABCAutomationResult):
    service_info: Mapping

    @staticmethod
    def automation_call() -> str:
        return "analyse-service"


result_type_registry.register(AnalyseServiceResult)


@dataclass
class AnalyseHostResult(ABCAutomationResult):
    labels: Labels
    label_sources: LabelSources

    def to_pre_21(self) -> Mapping[str, Any]:
        return asdict(self)

    @staticmethod
    def automation_call() -> str:
        return "analyse-host"


result_type_registry.register(AnalyseHostResult)


@dataclass
class DeleteHostsResult(ABCAutomationResult):
    def to_pre_21(self) -> None:
        return None

    @staticmethod
    def automation_call() -> str:
        return "delete-hosts"


result_type_registry.register(DeleteHostsResult)


@dataclass
class DeleteHostsKnownRemoteResult(ABCAutomationResult):
    def to_pre_21(self) -> None:
        return None

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

    def to_pre_21(self) -> Tuple[int, str]:
        return (
            self.return_code,
            self.response,
        )

    @staticmethod
    def automation_call() -> str:
        return "diag-host"


result_type_registry.register(DiagHostResult)


@dataclass
class ActiveCheckResult(ABCAutomationResult):
    state: Optional[ServiceState]
    output: ServiceDetails

    def to_pre_21(self) -> Optional[Tuple[ServiceState, ServiceDetails]]:
        return (
            None
            if self.state is None
            else (
                self.state,
                self.output,
            )
        )

    @staticmethod
    def automation_call() -> str:
        return "active-check"


result_type_registry.register(ActiveCheckResult)


@dataclass
class UpdateDNSCacheResult(ABCAutomationResult):
    n_updated: int
    failed_hosts: Sequence[HostName]

    def to_pre_21(self) -> UpdateDNSCacheResultRaw:
        return (
            self.n_updated,
            list(self.failed_hosts),
        )

    @staticmethod
    def automation_call() -> str:
        return "update-dns-cache"


result_type_registry.register(UpdateDNSCacheResult)


@dataclass
class GetAgentOutputResult(ABCAutomationResult):
    success: bool
    service_details: ServiceDetails
    raw_agent_data: AgentRawData

    def to_pre_21(self) -> Tuple[bool, ServiceDetails, AgentRawData]:
        return (
            self.success,
            self.service_details,
            self.raw_agent_data,
        )

    @staticmethod
    def automation_call() -> str:
        return "get-agent-output"


result_type_registry.register(GetAgentOutputResult)


@dataclass
class NotificationReplayResult(ABCAutomationResult):
    def to_pre_21(self) -> None:
        return None

    @staticmethod
    def automation_call() -> str:
        return "notification-replay"


result_type_registry.register(NotificationReplayResult)


@dataclass
class NotificationAnalyseResult(ABCAutomationResult):
    result: Optional[NotifyAnalysisInfo]

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

    def to_pre_21(self) -> Mapping[str, Any]:
        return asdict(self)

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
