#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Service discovery and autochecks results.

Groups all types that revolve around discovering services/host-labels and
managing autochecks, including the shared DiscoveryReport serialization helpers.
"""

from __future__ import annotations

import json
from ast import literal_eval
from collections.abc import Container, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Self

from cmk.automations.results._base import (
    ABCAutomationResult,
    DiscoveredHostLabelsDict,
    result_type_registry,
    SerializedResult,
)
from cmk.ccc import version as cmk_version
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import CheckPreviewEntry, DiscoveryReport, TransitionCounter
from cmk.checkengine.plugins import AutocheckEntry
from cmk.utils.labels import HostLabel
from cmk.utils.servicename import ServiceName

from ..types import AutomationID


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
    def automation_call() -> AutomationID:
        return AutomationID("service-discovery")


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
    config_warnings: Sequence[str]

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        if for_cmk_version < cmk_version.Version.from_str("2.5.0b1"):
            return self._serialize_as_dict(skip_keys={"config_warnings"})
        return self._serialize_as_dict(skip_keys=())

    def _serialize_as_dict(self, skip_keys: Container[str]) -> SerializedResult:
        raw = asdict(self)
        return SerializedResult(
            repr(
                {
                    **{k: v for k, v in raw.items() if k not in skip_keys},
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
            config_warnings=raw["config_warnings"],
        )

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("service-discovery-preview")


result_type_registry.register(ServiceDiscoveryPreviewResult)


class SpecialAgentDiscoveryPreviewResult(ServiceDiscoveryPreviewResult):
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("special-agent-discovery-preview")


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
    def automation_call() -> AutomationID:
        return AutomationID("autodiscovery")


result_type_registry.register(AutodiscoveryResult)


@dataclass
class SetAutochecksV2Result(ABCAutomationResult):
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("set-autochecks-v2")


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
    def automation_call() -> AutomationID:
        return AutomationID("update-host-labels")


result_type_registry.register(UpdateHostLabelsResult)
