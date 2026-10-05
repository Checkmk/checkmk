#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Host and configuration management results.

Groups CRUD-like and infrastructure operations.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import override

from cmk.automations.results._base import AutomationResult, result_type_registry
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.helper_interface import AgentRawData
from cmk.checkengine.submitters import ServiceDetails
from cmk.utils.config_warnings import ConfigurationWarnings

from ..types import AutomationID


@dataclass
class RenameHostsResult(AutomationResult):
    action_counts: Mapping[str, int]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("rename-hosts")


result_type_registry.register(RenameHostsResult)


@dataclass
class DeleteHostsResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("delete-hosts")


result_type_registry.register(DeleteHostsResult)


@dataclass
class DeleteHostsKnownRemoteResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("delete-hosts-known-remote")


result_type_registry.register(DeleteHostsKnownRemoteResult)


@dataclass
class RestartResult(AutomationResult):
    config_warnings: ConfigurationWarnings

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("restart")


result_type_registry.register(RestartResult)


@dataclass
class ReloadResult(RestartResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("reload")


result_type_registry.register(ReloadResult)


@dataclass
class GetConfigurationResult(AutomationResult):
    result: Mapping[str, object]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-configuration")


result_type_registry.register(GetConfigurationResult)


@dataclass
class GetCheckInformationResult(AutomationResult):
    plugin_infos: Mapping[str, Mapping[str, object]]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-check-information")


result_type_registry.register(GetCheckInformationResult)


@dataclass
class GetSectionInformationResult(AutomationResult):
    section_infos: Mapping[str, Mapping[str, str]]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-section-information")


result_type_registry.register(GetSectionInformationResult)


@dataclass
class UpdateDNSCacheResult(AutomationResult):
    n_updated: int
    failed_hosts: Sequence[HostName]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("update-dns-cache")


result_type_registry.register(UpdateDNSCacheResult)


@dataclass
class UpdatePasswordsMergedFileResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("update-passwords-merged-file")


result_type_registry.register(UpdatePasswordsMergedFileResult)


@dataclass
class GetAgentOutputResult(AutomationResult):
    success: bool
    service_details: ServiceDetails
    raw_agent_data: AgentRawData

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-agent-output")


result_type_registry.register(GetAgentOutputResult)


@dataclass
class BakeAgentsResult(AutomationResult):
    output: str | None

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("bake-agents")


result_type_registry.register(BakeAgentsResult)


@dataclass
class BakeryChangedTargetsResult(AutomationResult):
    # Targets are carried as their .serialize() form (see BakeryTarget); decode
    # with cmk.bakery.shared.type_defs.get_bakery_target() on the consumer side
    # when typed objects are needed. Avoids pulling non-free types into this
    # open-source result module.
    changed: Sequence[str]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("bakery-changed-targets")


result_type_registry.register(BakeryChangedTargetsResult)
