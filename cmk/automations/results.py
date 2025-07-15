#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import socket
from abc import ABC, abstractmethod
from ast import literal_eval
from collections.abc import Mapping, Sequence
from dataclasses import asdict, astuple, dataclass, field
from enum import StrEnum
from typing import Any, Literal, Self, TypedDict, TypeVar

from cmk.ccc import version as cmk_version
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.plugin_registry import Registry

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import HostLabel, HostLabelValueDict, Labels, LabelSources
from cmk.utils.notify_types import NotifyAnalysisInfo, NotifyBulks
from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.servicename import Item, ServiceName

from cmk.checkengine.discovery import CheckPreviewEntry, DiscoveryReport, TransitionCounter
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.plugins import AutocheckEntry
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


def _serialize_discovery_report(
    report: DiscoveryReport, for_cmk_version: cmk_version.Version
) -> Mapping[str, object]:
    if for_cmk_version >= cmk_version.Version.from_str("2.5.0b1"):
        return asdict(report)

    return {
        "self_new": report.services.new,
        "self_changed": report.services.changed,
        "self_removed": report.services.removed,
        "self_kept": report.services.kept,
        "self_new_host_labels": report.host_labels.new,
        "self_total_host_labels": report.host_labels.total,
        "clustered_new": report.clustered_new,
        "clustered_old": report.clustered_old,
        "clustered_vanished": report.clustered_vanished,
        "clustered_ignored": report.clustered_ignored,
        "error_text": report.error_text,
        "diff_text": report.diff_text,
    }


def _deserialize_discovery_report(
    serialized: Mapping[str, Any],
) -> DiscoveryReport:
    return DiscoveryReport(
        services=TransitionCounter(**serialized["services"]),
        host_labels=TransitionCounter(**serialized["host_labels"]),
        clustered_new=serialized["clustered_new"],
        clustered_old=serialized["clustered_old"],
        clustered_vanished=serialized["clustered_vanished"],
        clustered_ignored=serialized["clustered_ignored"],
        error_text=serialized["error_text"],
        diff_text=serialized["diff_text"],
    )


@dataclass
class ServiceDiscoveryResult(ABCAutomationResult):
    hosts: Mapping[HostName, DiscoveryReport]

    def _to_dict(
        self, for_cmk_version: cmk_version.Version
    ) -> Mapping[HostName, Mapping[str, Any]]:
        return {k: _serialize_discovery_report(v, for_cmk_version) for k, v in self.hosts.items()}

    @staticmethod
    def _from_dict(
        serialized: Mapping[HostName, Mapping[str, Any]],
    ) -> Mapping[HostName, DiscoveryReport]:
        return {k: _deserialize_discovery_report(v) for k, v in serialized.items()}

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return SerializedResult(repr(self._to_dict(for_cmk_version)))

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> ServiceDiscoveryResult:
        return cls(cls._from_dict(literal_eval(serialized_result)))

    @staticmethod
    def automation_call() -> str:
        return "service-discovery"


result_type_registry.register(ServiceDiscoveryResult)


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


class SpecialAgentDiscoveryPreviewResult(ServiceDiscoveryPreviewResult):
    @staticmethod
    def automation_call() -> str:
        return "special-agent-discovery-preview"


result_type_registry.register(SpecialAgentDiscoveryPreviewResult)


@dataclass
class AutodiscoveryResult(ABCAutomationResult):
    hosts: Mapping[HostName, DiscoveryReport]
    changes_activated: bool

    def _hosts_to_dict(
        self, for_cmk_version: cmk_version.Version
    ) -> Mapping[HostName, Mapping[str, Any]]:
        return {k: _serialize_discovery_report(v, for_cmk_version) for k, v in self.hosts.items()}

    @staticmethod
    def _hosts_from_dict(
        serialized: Mapping[HostName, Mapping[str, Any]],
    ) -> Mapping[HostName, DiscoveryReport]:
        return {k: _deserialize_discovery_report(v) for k, v in serialized.items()}

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return SerializedResult(
            repr((self._hosts_to_dict(for_cmk_version), self.changes_activated))
        )

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> Self:
        hosts, changes_activated = literal_eval(serialized_result)
        return cls(cls._hosts_from_dict(hosts), changes_activated)

    @staticmethod
    def automation_call() -> str:
        return "autodiscovery"


result_type_registry.register(AutodiscoveryResult)


@dataclass
class SetAutochecksV2Result(ABCAutomationResult):
    @staticmethod
    def automation_call() -> str:
        return "set-autochecks-v2"


result_type_registry.register(SetAutochecksV2Result)


@dataclass
class SetAutochecksInput:
    discovered_host: HostName  # effective host, the one that is being discovered.
    target_services: Mapping[
        ServiceName, AutocheckEntry
    ]  # the table of services we want to see on the discovered host
    nodes_services: Mapping[
        HostName, Mapping[ServiceName, AutocheckEntry]
    ]  # the discovered services on all the nodes

    @classmethod
    def deserialize(cls, serialized_input: str) -> SetAutochecksInput:
        raw = json.loads(serialized_input)
        return cls(
            discovered_host=HostName(raw["discovered_host"]),
            target_services={
                ServiceName(n): AutocheckEntry.load(literal_eval(s))
                for n, s in raw["target_services"].items()
            },
            nodes_services={
                HostName(k): {
                    ServiceName(n): AutocheckEntry.load(literal_eval(s)) for n, s in v.items()
                }
                for k, v in raw["nodes_services"].items()
            },
        )

    def serialize(self) -> str:
        return json.dumps(
            {
                "discovered_host": str(self.discovered_host),
                "target_services": {n: repr(s.dump()) for n, s in self.target_services.items()},
                "nodes_services": {
                    str(k): {n: repr(s.dump()) for n, s in v.items()}
                    for k, v in self.nodes_services.items()
                },
            }
        )


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
class GetServiceNameResult(ABCAutomationResult):
    service_name: str

    @staticmethod
    def automation_call() -> str:
        return "get-service-name"


result_type_registry.register(GetServiceNameResult)


@dataclass
class AnalyseHostResult(ABCAutomationResult):
    labels: Labels
    label_sources: LabelSources

    @staticmethod
    def automation_call() -> str:
        return "analyse-host"


result_type_registry.register(AnalyseHostResult)


@dataclass
class AnalyzeHostRuleMatchesResult(ABCAutomationResult):
    results: dict[str, list[object]]

    @staticmethod
    def automation_call() -> str:
        return "analyze-host-rule-matches"


result_type_registry.register(AnalyzeHostRuleMatchesResult)


@dataclass
class AnalyzeServiceRuleMatchesResult(ABCAutomationResult):
    results: dict[str, list[object]]

    @staticmethod
    def automation_call() -> str:
        return "analyze-service-rule-matches"


result_type_registry.register(AnalyzeServiceRuleMatchesResult)


@dataclass
class AnalyzeHostRuleEffectivenessResult(ABCAutomationResult):
    results: dict[str, bool]

    @staticmethod
    def automation_call() -> str:
        return "analyze-host-rule-effectiveness"


result_type_registry.register(AnalyzeHostRuleEffectivenessResult)


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
class DiagSpecialAgentHostConfig:
    host_name: HostName
    host_alias: str
    ip_address: HostAddress | None = None
    ip_stack_config: IPStackConfig = IPStackConfig.NO_IP
    host_attrs: Mapping[str, str] = field(default_factory=dict)
    macros: Mapping[str, object] = field(default_factory=dict)
    host_primary_family: Literal[
        socket.AddressFamily.AF_INET,
        socket.AddressFamily.AF_INET6,
    ] = socket.AddressFamily.AF_INET
    host_additional_addresses_ipv4: list[HostAddress] = field(default_factory=list)
    host_additional_addresses_ipv6: list[HostAddress] = field(default_factory=list)

    @classmethod
    def deserialize(cls, serialized_input: str) -> DiagSpecialAgentHostConfig:
        raw = json.loads(serialized_input)
        deserialized = {
            "host_name": HostName(raw["host_name"]),
            "host_alias": raw["host_alias"],
        }
        if "ip_address" in raw:
            deserialized["ip_address"] = (
                HostAddress(raw["ip_address"]) if raw["ip_address"] else None
            )
        if "ip_stack_config" in raw:
            deserialized["ip_stack_config"] = IPStackConfig(raw["ip_stack_config"])
        if "host_attrs" in raw:
            deserialized["host_attrs"] = raw["host_attrs"]
        if "macros" in raw:
            deserialized["macros"] = raw["macros"]
        if "host_primary_family" in raw:
            deserialized["host_primary_family"] = cls.deserialize_host_primary_family(
                raw["host_primary_family"]
            )
        if "host_additional_addresses_ipv4" in raw:
            deserialized["host_additional_addresses_ipv4"] = [
                HostAddress(ip) for ip in raw["host_additional_addresses_ipv4"]
            ]
        if "host_additional_addresses_ipv6" in raw:
            deserialized["host_additional_addresses_ipv6"] = [
                HostAddress(ip) for ip in raw["host_additional_addresses_ipv6"]
            ]
        return cls(**deserialized)

    @staticmethod
    def deserialize_host_primary_family(
        raw: int,
    ) -> Literal[
        socket.AddressFamily.AF_INET,
        socket.AddressFamily.AF_INET6,
    ]:
        address_family = socket.AddressFamily(raw)
        if address_family is socket.AddressFamily.AF_INET:
            return socket.AddressFamily.AF_INET
        if address_family is socket.AddressFamily.AF_INET6:
            return socket.AddressFamily.AF_INET6
        raise ValueError(f"Invalid address family: {address_family}")

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_name": str(self.host_name),
                "host_alias": self.host_alias,
                "ip_address": str(self.ip_address) if self.ip_address else None,
                "ip_stack_config": self.ip_stack_config.value,
                "host_attrs": self.host_attrs,
                "macros": self.macros,
                "host_primary_family": self.host_primary_family.value,
                "host_additional_addresses_ipv4": [
                    str(ip) for ip in self.host_additional_addresses_ipv4
                ],
                "host_additional_addresses_ipv6": [
                    str(ip) for ip in self.host_additional_addresses_ipv6
                ],
            }
        )


@dataclass
class DiagSpecialAgentInput:
    host_config: DiagSpecialAgentHostConfig
    agent_name: str
    params: Mapping[str, object]
    passwords: Mapping[str, str]
    http_proxies: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    is_cmc: bool = True

    @classmethod
    def deserialize(cls, serialized_input: str) -> DiagSpecialAgentInput:
        raw = json.loads(serialized_input)
        deserialized = {
            "host_config": DiagSpecialAgentHostConfig.deserialize(raw["host_config"]),
            "agent_name": raw["agent_name"],
            # TODO: at the moment there is no validation for params input possible
            #  this could change when being able to use the formspec vue visitor for
            #  (de)serialization in the future.
            "params": literal_eval(raw["params"]),
            "passwords": raw["passwords"],
        }
        if "http_proxies" in raw:
            deserialized["http_proxies"] = raw["http_proxies"]
        if "is_cmc" in raw:
            deserialized["is_cmc"] = raw["is_cmc"]
        return cls(**deserialized)

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_config": self.host_config.serialize(_for_cmk_version),
                "agent_name": self.agent_name,
                "params": repr(self.params),
                "passwords": self.passwords,
                "http_proxies": self.http_proxies,
                "is_cmc": self.is_cmc,
            }
        )


@dataclass
class SpecialAgentResult:
    return_code: int
    response: str


@dataclass
class DiagSpecialAgentResult(ABCAutomationResult):
    results: Sequence[SpecialAgentResult]

    @staticmethod
    def automation_call() -> str:
        return "diag-special-agent"

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return SerializedResult(
            json.dumps(
                {
                    "results": [asdict(r) for r in self.results],
                }
            )
        )

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> DiagSpecialAgentResult:
        raw = json.loads(serialized_result)
        return cls(
            results=[SpecialAgentResult(**r) for r in raw["results"]],
        )


result_type_registry.register(DiagSpecialAgentResult)


@dataclass
class DiagCmkAgentInput:
    host_name: HostName
    ip_address: HostAddress
    address_family: Literal["no-ip", "ip-v4-only", "ip-v6-only", "ip-v4v6"]
    agent_port: int
    timeout: int

    @classmethod
    def deserialize(cls, serialized_input: str) -> DiagCmkAgentInput:
        raw = json.loads(serialized_input)
        deserialized = {
            "host_name": HostName(raw["host_name"]),
            "ip_address": HostAddress(raw["ip_address"]),
            "address_family": raw["address_family"],
            "agent_port": raw["agent_port"],
            "timeout": raw["timeout"],
        }
        return cls(**deserialized)

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_name": self.host_name,
                "ip_address": self.ip_address,
                "address_family": self.address_family,
                "agent_port": self.agent_port,
                "timeout": self.timeout,
            }
        )


@dataclass
class DiagCmkAgentResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> str:
        return "diag-cmk-agent"


result_type_registry.register(DiagCmkAgentResult)


@dataclass
class DiagHostResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> str:
        return "diag-host"


result_type_registry.register(DiagHostResult)


@dataclass
class PingHostResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> str:
        return "ping-host"


result_type_registry.register(PingHostResult)


class PingHostCmd(StrEnum):
    PING = "ping"
    PING6 = "ping6"
    PING4 = "ping4"


@dataclass
class PingHostInput:
    ip_or_dns_name: str
    base_cmd: PingHostCmd = PingHostCmd.PING

    @classmethod
    def deserialize(cls, serialized_input: str) -> PingHostInput:
        raw = json.loads(serialized_input)
        deserialized = {
            "ip_or_dns_name": raw["ip_or_dns_name"],
            "base_cmd": PingHostCmd(raw.get("base_cmd", PingHostCmd.PING)),
        }
        return cls(**deserialized)

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "ip_or_dns_name": self.ip_or_dns_name,
                "base_cmd": self.base_cmd.value,
            }
        )


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


@dataclass
class UnknownCheckParameterRuleSetsResult(ABCAutomationResult):
    result: Sequence[str]

    @staticmethod
    def automation_call() -> str:
        return "find-unknown-check-parameter-rule-sets"


result_type_registry.register(UnknownCheckParameterRuleSetsResult)
