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

from cmk.automations.internal import AutomationID, AutomationResult
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.helper_interface import AgentRawData
from cmk.checkengine.submitters import ServiceDetails
from cmk.utils.config_warnings import ConfigurationWarnings


@dataclass
class RenameHostsResult(AutomationResult):
    action_counts: Mapping[str, int]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("rename-hosts")


@dataclass
class DeleteHostsResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("delete-hosts")


@dataclass
class DeleteHostsKnownRemoteResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("delete-hosts-known-remote")


@dataclass
class RestartResult(AutomationResult):
    config_warnings: ConfigurationWarnings

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("restart")


@dataclass
class ReloadResult(RestartResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("reload")


@dataclass
class GetConfigurationResult(AutomationResult):
    result: Mapping[str, object]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-configuration")


@dataclass
class GetCheckInformationResult(AutomationResult):
    plugin_infos: Mapping[str, Mapping[str, object]]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-check-information")


@dataclass
class GetSectionInformationResult(AutomationResult):
    section_infos: Mapping[str, Mapping[str, str]]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-section-information")


@dataclass
class UpdateDNSCacheResult(AutomationResult):
    n_updated: int
    failed_hosts: Sequence[HostName]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("update-dns-cache")


@dataclass
class UpdatePasswordsMergedFileResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("update-passwords-merged-file")


@dataclass
class GetAgentOutputResult(AutomationResult):
    success: bool
    service_details: ServiceDetails
    raw_agent_data: AgentRawData

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("get-agent-output")


@dataclass
class BakeAgentsResult(AutomationResult):
    output: str | None

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("bake-agents")


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
