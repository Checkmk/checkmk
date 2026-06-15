#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Automation result types.

All public symbols are re-exported here so that existing imports of the form
``from cmk.automations.results import X`` continue to work unchanged.
"""

from cmk.automations.results._base import (
    ABCAutomationResult as ABCAutomationResult,
)
from cmk.automations.results._base import (
    DiscoveredHostLabelsDict as DiscoveredHostLabelsDict,
)
from cmk.automations.results._base import (
    result_type_registry as result_type_registry,
)
from cmk.automations.results._base import (
    ResultTypeRegistry as ResultTypeRegistry,
)
from cmk.automations.results._base import (
    SerializedResult as SerializedResult,
)
from cmk.automations.results.analysis import (
    ActiveCheckResult as ActiveCheckResult,
)
from cmk.automations.results.analysis import (
    AnalyseHostResult as AnalyseHostResult,
)
from cmk.automations.results.analysis import (
    AnalyseServiceResult as AnalyseServiceResult,
)
from cmk.automations.results.analysis import (
    AnalyzeHostRuleEffectivenessResult as AnalyzeHostRuleEffectivenessResult,
)
from cmk.automations.results.analysis import (
    AnalyzeHostRuleMatchesResult as AnalyzeHostRuleMatchesResult,
)
from cmk.automations.results.analysis import (
    AnalyzeServiceRuleMatchesResult as AnalyzeServiceRuleMatchesResult,
)
from cmk.automations.results.analysis import (
    GetServiceNameResult as GetServiceNameResult,
)
from cmk.automations.results.analysis import (
    GetServicesLabelsResult as GetServicesLabelsResult,
)
from cmk.automations.results.analysis import (
    ServiceInfo as ServiceInfo,
)
from cmk.automations.results.analysis import (
    UnknownCheckParameterRuleSetsResult as UnknownCheckParameterRuleSetsResult,
)
from cmk.automations.results.diagnostics import (
    CreateDiagnosticsDumpResult as CreateDiagnosticsDumpResult,
)
from cmk.automations.results.diagnostics import (
    DiagCmkAgentInput as DiagCmkAgentInput,
)
from cmk.automations.results.diagnostics import (
    DiagCmkAgentResult as DiagCmkAgentResult,
)
from cmk.automations.results.diagnostics import (
    DiagHostResult as DiagHostResult,
)
from cmk.automations.results.diagnostics import (
    DiagSnmpInput as DiagSnmpInput,
)
from cmk.automations.results.diagnostics import (
    DiagSnmpResult as DiagSnmpResult,
)
from cmk.automations.results.diagnostics import (
    DiagSpecialAgentHostConfig as DiagSpecialAgentHostConfig,
)
from cmk.automations.results.diagnostics import (
    DiagSpecialAgentInput as DiagSpecialAgentInput,
)
from cmk.automations.results.diagnostics import (
    DiagSpecialAgentResult as DiagSpecialAgentResult,
)
from cmk.automations.results.diagnostics import (
    Gateway as Gateway,
)
from cmk.automations.results.diagnostics import (
    GatewayResult as GatewayResult,
)
from cmk.automations.results.diagnostics import (
    PingHostCmd as PingHostCmd,
)
from cmk.automations.results.diagnostics import (
    PingHostInput as PingHostInput,
)
from cmk.automations.results.diagnostics import (
    PingHostResult as PingHostResult,
)
from cmk.automations.results.diagnostics import (
    ScanParentsResult as ScanParentsResult,
)
from cmk.automations.results.diagnostics import (
    SnmpV3AuthProtocol as SnmpV3AuthProtocol,
)
from cmk.automations.results.diagnostics import (
    SnmpV3SecurityLevel as SnmpV3SecurityLevel,
)
from cmk.automations.results.diagnostics import (
    SpecialAgentResult as SpecialAgentResult,
)
from cmk.automations.results.discovery import (
    AutodiscoveryResult as AutodiscoveryResult,
)
from cmk.automations.results.discovery import (
    ServiceDiscoveryPreviewResult as ServiceDiscoveryPreviewResult,
)
from cmk.automations.results.discovery import (
    ServiceDiscoveryResult as ServiceDiscoveryResult,
)
from cmk.automations.results.discovery import (
    SetAutochecksInput as SetAutochecksInput,
)
from cmk.automations.results.discovery import (
    SetAutochecksV2Result as SetAutochecksV2Result,
)
from cmk.automations.results.discovery import (
    SpecialAgentDiscoveryPreviewResult as SpecialAgentDiscoveryPreviewResult,
)
from cmk.automations.results.discovery import (
    UpdateHostLabelsResult as UpdateHostLabelsResult,
)
from cmk.automations.results.host_management import (
    BakeAgentsResult as BakeAgentsResult,
)
from cmk.automations.results.host_management import (
    BakeryChangedTargetsResult as BakeryChangedTargetsResult,
)
from cmk.automations.results.host_management import (
    DeleteHostsKnownRemoteResult as DeleteHostsKnownRemoteResult,
)
from cmk.automations.results.host_management import (
    DeleteHostsResult as DeleteHostsResult,
)
from cmk.automations.results.host_management import (
    GetAgentOutputResult as GetAgentOutputResult,
)
from cmk.automations.results.host_management import (
    GetCheckInformationResult as GetCheckInformationResult,
)
from cmk.automations.results.host_management import (
    GetConfigurationResult as GetConfigurationResult,
)
from cmk.automations.results.host_management import (
    GetSectionInformationResult as GetSectionInformationResult,
)
from cmk.automations.results.host_management import (
    ReloadResult as ReloadResult,
)
from cmk.automations.results.host_management import (
    RenameHostsResult as RenameHostsResult,
)
from cmk.automations.results.host_management import (
    RestartResult as RestartResult,
)
from cmk.automations.results.host_management import (
    UpdateDNSCacheResult as UpdateDNSCacheResult,
)
from cmk.automations.results.host_management import (
    UpdatePasswordsMergedFileResult as UpdatePasswordsMergedFileResult,
)
from cmk.automations.results.notification import (
    NotificationAnalyseResult as NotificationAnalyseResult,
)
from cmk.automations.results.notification import (
    NotificationGetBulksResult as NotificationGetBulksResult,
)
from cmk.automations.results.notification import (
    NotificationReplayResult as NotificationReplayResult,
)
from cmk.automations.results.notification import (
    NotificationTestResult as NotificationTestResult,
)
from cmk.automations.results.notification import (
    NotifyResult as NotifyResult,
)
