#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Host and configuration management results.

Groups CRUD-like and infrastructure operations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.automations.results._base import ABCAutomationResult, result_type_registry
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.submitters import ServiceDetails
from cmk.helper_interface import AgentRawData
from cmk.utils.config_warnings import ConfigurationWarnings

from ..types import AutomationID


@dataclass
class RenameHostsResult(ABCAutomationResult):
    action_counts: Mapping[str, int]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("rename-hosts")


result_type_registry.register(RenameHostsResult)


@dataclass
class DeleteHostsResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("delete-hosts")


result_type_registry.register(DeleteHostsResult)


@dataclass
class DeleteHostsKnownRemoteResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("delete-hosts-known-remote")


result_type_registry.register(DeleteHostsKnownRemoteResult)


@dataclass
class RestartResult(ABCAutomationResult):
    config_warnings: ConfigurationWarnings

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("restart")


result_type_registry.register(RestartResult)


@dataclass
class ReloadResult(RestartResult):
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("reload")


result_type_registry.register(ReloadResult)


@dataclass
class GetConfigurationResult(ABCAutomationResult):
    result: Mapping[str, Any]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("get-configuration")


result_type_registry.register(GetConfigurationResult)


@dataclass
class GetCheckInformationResult(ABCAutomationResult):
    plugin_infos: Mapping[str, Mapping[str, Any]]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("get-check-information")


result_type_registry.register(GetCheckInformationResult)


@dataclass
class GetSectionInformationResult(ABCAutomationResult):
    section_infos: Mapping[str, Mapping[str, str]]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("get-section-information")


result_type_registry.register(GetSectionInformationResult)


@dataclass
class UpdateDNSCacheResult(ABCAutomationResult):
    n_updated: int
    failed_hosts: Sequence[HostName]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("update-dns-cache")


result_type_registry.register(UpdateDNSCacheResult)


@dataclass
class UpdatePasswordsMergedFileResult(ABCAutomationResult):
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("update-passwords-merged-file")


result_type_registry.register(UpdatePasswordsMergedFileResult)


@dataclass
class GetAgentOutputResult(ABCAutomationResult):
    success: bool
    service_details: ServiceDetails
    raw_agent_data: AgentRawData

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("get-agent-output")


result_type_registry.register(GetAgentOutputResult)


@dataclass
class BakeAgentsResult(ABCAutomationResult):
    output: str | None

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("bake-agents")


result_type_registry.register(BakeAgentsResult)
