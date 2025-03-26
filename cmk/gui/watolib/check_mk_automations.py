#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple, TypeVar

from livestatus import SiteId

import cmk.ccc.version as cmk_version

from cmk.utils.diagnostics import DiagnosticsCLParameters
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import HostLabel, Labels
from cmk.utils.notify import NotificationContext
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import Item, ServiceName

from cmk.automations import results
from cmk.automations.results import SetAutochecksInput

from cmk.checkengine.plugins import CheckPluginName

from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.site_config import site_is_local
from cmk.gui.watolib.activate_changes import sync_changes_before_remote_automation
from cmk.gui.watolib.automations import (
    check_mk_local_automation_serialized,
    check_mk_remote_automation_serialized,
    get_local_automation_failure_message,
    MKAutomationException,
)


class AutomationResponse(NamedTuple):
    command: str
    serialized_result: results.SerializedResult
    local: bool
    cmdline: Iterable[str]


def _automation_serialized(
    command: str,
    *,
    siteid: SiteId | None = None,
    args: Sequence[str] | None = None,
    indata: Any = "",
    stdin_data: str | None = None,
    timeout: int | None = None,
    sync: bool = True,
    non_blocking_http: bool = False,
    force_cli_interface: bool = False,
) -> AutomationResponse:
    if args is None:
        args = []

    if not siteid or site_is_local(active_config, siteid):
        cmdline, serialized_result = check_mk_local_automation_serialized(
            command=command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
            force_cli_interface=force_cli_interface,
        )
        return AutomationResponse(
            command=command,
            serialized_result=serialized_result,
            local=True,
            cmdline=cmdline,
        )

    return AutomationResponse(
        command=command,
        serialized_result=check_mk_remote_automation_serialized(
            site_id=siteid,
            command=command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
            sync=sync_changes_before_remote_automation if sync else lambda site_id: None,
            non_blocking_http=non_blocking_http,
        ),
        local=False,
        cmdline=[],
    )


def _automation_failure(
    response: AutomationResponse,
    exception: SyntaxError,
) -> MKAutomationException:
    if response.local:
        msg = get_local_automation_failure_message(
            command=response.command,
            cmdline=response.cmdline,
            out=response.serialized_result,
            exc=exception,
        )
        return MKAutomationException(msg)
    return MKAutomationException(
        "%s: <pre>%s</pre>"
        % (
            _("Got invalid data"),
            response.serialized_result,
        )
    )


_ResultType = TypeVar("_ResultType", bound=results.ABCAutomationResult)


def _deserialize(
    response: AutomationResponse,
    result_type: type[_ResultType],
) -> _ResultType:
    try:
        return result_type.deserialize(response.serialized_result)
    except SyntaxError as excpt:
        raise _automation_failure(
            response,
            excpt,
        )


def local_discovery(
    mode: str,
    host_names: Iterable[HostName],
    *,
    scan: bool,
    raise_errors: bool,
    timeout: int | None = None,
    non_blocking_http: bool = False,
) -> results.ServiceDiscoveryResult:
    return discovery(
        None,
        mode,
        host_names,
        scan=scan,
        raise_errors=raise_errors,
        timeout=timeout,
        non_blocking_http=non_blocking_http,
    )


def discovery(
    site_id: SiteId | None,
    mode: str,
    host_names: Iterable[HostName],
    *,
    scan: bool,
    raise_errors: bool,
    timeout: int | None = None,
    non_blocking_http: bool = False,
) -> results.ServiceDiscoveryResult:
    return _deserialize(
        _automation_serialized(
            "service-discovery",
            siteid=site_id,
            args=[
                *(("@scan",) if scan else ()),
                *(("@raiseerrors",) if raise_errors else ()),
                mode,
                *host_names,
            ],
            timeout=timeout,
            non_blocking_http=non_blocking_http,
        ),
        results.ServiceDiscoveryResult,
    )


def special_agent_discovery_preview(
    site_id: SiteId,
    special_agent_preview_input: results.DiagSpecialAgentInput,
) -> results.SpecialAgentDiscoveryPreviewResult:
    return _deserialize(
        _automation_serialized(
            "special-agent-discovery-preview",
            siteid=site_id,
            args=None,
            stdin_data=special_agent_preview_input.serialize(
                cmk_version.Version.from_str(cmk_version.__version__)
            ),
            force_cli_interface=True,
            # the special agent discovery preview can take a long time depending on the underlying
            # datasource agent which can be problematic for remote setups
            timeout=5 * 60,
        ),
        results.SpecialAgentDiscoveryPreviewResult,
    )


def local_discovery_preview(
    host_name: HostName,
    *,
    prevent_fetching: bool,
    raise_errors: bool,
) -> results.ServiceDiscoveryPreviewResult:
    return _deserialize(
        _automation_serialized(
            "service-discovery-preview",
            siteid=None,
            args=[
                *(("@nofetch",) if prevent_fetching else ()),
                *(("@raiseerrors",) if raise_errors else ()),
                host_name,
            ],
        ),
        results.ServiceDiscoveryPreviewResult,
    )


def autodiscovery(site_id: SiteId) -> results.AutodiscoveryResult:
    return _deserialize(
        _automation_serialized("autodiscovery", siteid=site_id),
        results.AutodiscoveryResult,
    )


def set_autochecks_v2(
    site_id: SiteId,
    checks: SetAutochecksInput,
) -> results.SetAutochecksV2Result:
    return _deserialize(
        _automation_serialized(
            "set-autochecks-v2",
            siteid=site_id,
            args=None,
            stdin_data=checks.serialize(),
        ),
        results.SetAutochecksV2Result,
    )


def update_host_labels(
    site_id: SiteId,
    host_name: HostName,
    host_labels: Sequence[HostLabel],
) -> results.UpdateHostLabelsResult:
    return _deserialize(
        _automation_serialized(
            "update-host-labels",
            siteid=site_id,
            args=[host_name],
            indata={label.name: label.to_dict() for label in host_labels},
        ),
        results.UpdateHostLabelsResult,
    )


def rename_hosts(
    site_id: SiteId,
    name_pairs: Sequence[tuple[HostName, HostName]],
) -> results.RenameHostsResult:
    return _deserialize(
        _automation_serialized(
            "rename-hosts",
            siteid=site_id,
            indata=name_pairs,
            non_blocking_http=True,
        ),
        results.RenameHostsResult,
    )


def get_services_labels(
    site_id: SiteId,
    host_name: HostName,
    service_names: Sequence[ServiceName],
) -> results.GetServicesLabelsResult:
    return _deserialize(
        _automation_serialized(
            "get-services-labels",
            siteid=site_id,
            args=[host_name, *service_names],
        ),
        results.GetServicesLabelsResult,
    )


def get_service_name(
    host_name: HostName, check_plugin_name: CheckPluginName, item: Item
) -> results.GetServiceNameResult:
    return _deserialize(
        _automation_serialized(
            "get-service-name", args=[host_name, str(check_plugin_name), repr(item)]
        ),
        results.GetServiceNameResult,
    )


def analyse_service(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
) -> results.AnalyseServiceResult:
    return _deserialize(
        _automation_serialized(
            "analyse-service",
            siteid=site_id,
            args=[host_name, service_name],
        ),
        results.AnalyseServiceResult,
    )


def analyse_host(
    site_id: SiteId,
    host_name: HostName,
) -> results.AnalyseHostResult:
    return _deserialize(
        _automation_serialized(
            "analyse-host",
            siteid=site_id,
            args=[host_name],
        ),
        results.AnalyseHostResult,
    )


def analyze_host_rule_matches(
    host_name: HostName, rules: Sequence[Sequence[RuleSpec]]
) -> results.AnalyzeHostRuleMatchesResult:
    return _deserialize(
        _automation_serialized("analyze-host-rule-matches", args=[host_name], indata=rules),
        results.AnalyzeHostRuleMatchesResult,
    )


def analyze_service_rule_matches(
    host_name: HostName,
    service_or_item: str,
    service_labels: Labels,
    rules: Sequence[Sequence[RuleSpec]],
) -> results.AnalyzeServiceRuleMatchesResult:
    return _deserialize(
        _automation_serialized(
            "analyze-service-rule-matches",
            args=[host_name, service_or_item],
            indata=(rules, service_labels),
        ),
        results.AnalyzeServiceRuleMatchesResult,
    )


def delete_hosts(
    site_id: SiteId,
    host_names: Sequence[HostName],
) -> results.DeleteHostsResult:
    return _deserialize(
        _automation_serialized(
            "delete-hosts",
            siteid=site_id,
            args=host_names,
        ),
        results.DeleteHostsResult,
    )


def restart(hosts_to_update: Sequence[HostName] | None = None) -> results.RestartResult:
    return _deserialize(
        _automation_serialized("restart", args=hosts_to_update),
        results.RestartResult,
    )


def reload(hosts_to_update: Sequence[HostName] | None = None) -> results.ReloadResult:
    return _deserialize(
        _automation_serialized("reload", args=hosts_to_update),
        results.ReloadResult,
    )


def get_configuration(*config_var_names: str) -> results.GetConfigurationResult:
    return _deserialize(
        _automation_serialized(
            "get-configuration",
            indata=list(config_var_names),
            # We must not call this through the automation helper,
            # see automation call execution.
            force_cli_interface=True,
        ),
        results.GetConfigurationResult,
    )


def update_merged_password_file() -> results.UpdatePasswordsMergedFileResult:
    return _deserialize(
        _automation_serialized(
            "update-passwords-merged-file",
        ),
        results.UpdatePasswordsMergedFileResult,
    )


def get_check_information() -> results.GetCheckInformationResult:
    return _deserialize(
        _automation_serialized("get-check-information"),
        results.GetCheckInformationResult,
    )


@request_memoize()
def get_check_information_cached() -> Mapping[CheckPluginName, Mapping[str, str]]:
    raw_check_dict = get_check_information().plugin_infos
    return {CheckPluginName(name): info for name, info in sorted(raw_check_dict.items())}


def get_section_information() -> results.GetSectionInformationResult:
    return _deserialize(
        _automation_serialized("get-section-information"),
        results.GetSectionInformationResult,
    )


def scan_parents(
    site_id: SiteId,
    host_name: HostName,
    *params: str,
) -> results.ScanParentsResult:
    return _deserialize(
        _automation_serialized(
            "scan-parents",
            siteid=site_id,
            args=[*params, host_name],
        ),
        results.ScanParentsResult,
    )


def diag_special_agent(
    site_id: SiteId,
    diag_special_agent_input: results.DiagSpecialAgentInput,
) -> results.DiagSpecialAgentResult:
    return _deserialize(
        _automation_serialized(
            "diag-special-agent",
            siteid=site_id,
            args=None,
            stdin_data=diag_special_agent_input.serialize(
                cmk_version.Version.from_str(cmk_version.__version__)
            ),
        ),
        results.DiagSpecialAgentResult,
    )


def diag_host(
    site_id: SiteId,
    host_name: HostName,
    test: str,
    *args: str,
) -> results.DiagHostResult:
    return _deserialize(
        _automation_serialized(
            "diag-host",
            siteid=site_id,
            args=[host_name, test, *args],
        ),
        results.DiagHostResult,
    )


def active_check(
    site_id: SiteId,
    host_name: HostName,
    check_type: str,
    item: str,
) -> results.ActiveCheckResult:
    return _deserialize(
        _automation_serialized(
            "active-check",
            siteid=site_id,
            args=[host_name, check_type, item],
            sync=False,
        ),
        results.ActiveCheckResult,
    )


def update_dns_cache(site_id: SiteId) -> results.UpdateDNSCacheResult:
    return _deserialize(
        _automation_serialized(
            "update-dns-cache",
            siteid=site_id,
        ),
        results.UpdateDNSCacheResult,
    )


def get_agent_output(
    site_id: SiteId,
    host_name: HostName,
    agent_type: str,
) -> results.GetAgentOutputResult:
    return _deserialize(
        _automation_serialized(
            "get-agent-output",
            siteid=site_id,
            args=[host_name, agent_type],
        ),
        results.GetAgentOutputResult,
    )


def notification_replay(notification_number: int) -> results.NotificationReplayResult:
    return _deserialize(
        _automation_serialized(
            "notification-replay",
            args=[str(notification_number)],
        ),
        results.NotificationReplayResult,
    )


def notification_analyse(notification_number: int) -> results.NotificationAnalyseResult:
    return _deserialize(
        _automation_serialized(
            "notification-analyse",
            args=[str(notification_number)],
        ),
        results.NotificationAnalyseResult,
    )


def notification_test(
    raw_context: NotificationContext, dispatch: str
) -> results.NotificationTestResult:
    return _deserialize(
        _automation_serialized(
            "notification-test",
            args=[json.dumps(raw_context), dispatch],
        ),
        results.NotificationTestResult,
    )


def notification_get_bulks(only_ripe: bool) -> results.NotificationGetBulksResult:
    return _deserialize(
        _automation_serialized(
            "notification-get-bulks",
            args=[str(int(only_ripe))],
        ),
        results.NotificationGetBulksResult,
    )


def create_diagnostics_dump(
    site_id: SiteId,
    serialized_params: DiagnosticsCLParameters,
    timeout: int,
) -> results.CreateDiagnosticsDumpResult:
    return _deserialize(
        _automation_serialized(
            "create-diagnostics-dump",
            siteid=site_id,
            args=serialized_params,
            timeout=timeout,
            non_blocking_http=True,
        ),
        results.CreateDiagnosticsDumpResult,
    )


def bake_agents(
    indata: Mapping[str, Any] | None = None,
    force_automation_cli_interface: bool = False,
) -> results.BakeAgentsResult:
    return _deserialize(
        _automation_serialized(
            "bake-agents",
            indata="" if indata is None else indata,
            force_cli_interface=force_automation_cli_interface,
        ),
        results.BakeAgentsResult,
    )


def find_unknown_check_parameter_rule_sets() -> results.UnknownCheckParameterRuleSetsResult:
    return _deserialize(
        _automation_serialized(
            "find-unknown-check-parameter-rule-sets",
        ),
        results.UnknownCheckParameterRuleSetsResult,
    )
