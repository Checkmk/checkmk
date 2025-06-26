#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple, TypeVar

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId

from cmk.utils.diagnostics import DiagnosticsCLParameters
from cmk.utils.labels import HostLabel, Labels
from cmk.utils.notify import NotificationContext
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import Item, ServiceName

from cmk.automations import results
from cmk.automations.results import SetAutochecksInput

from cmk.checkengine.discovery import DiscoverySettings
from cmk.checkengine.plugins import CheckPluginName

from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.watolib.activate_changes import sync_changes_before_remote_automation
from cmk.gui.watolib.automations import (
    check_mk_local_automation_serialized,
    check_mk_remote_automation_serialized,
    get_local_automation_failure_message,
    LocalAutomationConfig,
    make_automation_config,
    MKAutomationException,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.hosts_and_folders import collect_all_hosts


class AutomationResponse(NamedTuple):
    command: str
    serialized_result: results.SerializedResult
    local: bool
    cmdline: Iterable[str]


def _automation_serialized(
    command: str,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    args: Sequence[str] | None = None,
    indata: Any = "",
    stdin_data: str | None = None,
    timeout: int | None = None,
    sync: bool = True,
    non_blocking_http: bool = False,
    force_cli_interface: bool = False,
    debug: bool,
) -> AutomationResponse:
    if args is None:
        args = []

    if isinstance(automation_config, LocalAutomationConfig):
        cmdline, serialized_result = check_mk_local_automation_serialized(
            command=command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
            force_cli_interface=force_cli_interface,
            debug=debug,
            collect_all_hosts=collect_all_hosts,
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
            automation_config=automation_config,
            command=command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
            sync=sync_changes_before_remote_automation if sync else lambda site_id, debug: None,
            non_blocking_http=non_blocking_http,
            debug=debug,
        ),
        local=False,
        cmdline=[],
    )


def _automation_failure(
    response: AutomationResponse,
    exception: SyntaxError,
    debug: bool,
) -> MKAutomationException:
    if response.local:
        msg = get_local_automation_failure_message(
            command=response.command,
            cmdline=response.cmdline,
            out=response.serialized_result,
            exc=exception,
            debug=debug,
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
    *,
    debug: bool,
) -> _ResultType:
    try:
        return result_type.deserialize(response.serialized_result)
    except SyntaxError as excpt:
        raise _automation_failure(
            response,
            excpt,
            debug,
        )


def local_discovery(
    mode: DiscoverySettings,
    host_names: Iterable[HostName],
    *,
    scan: bool,
    raise_errors: bool,
    timeout: int | None = None,
    non_blocking_http: bool = False,
    debug: bool,
) -> results.ServiceDiscoveryResult:
    return discovery(
        site_id=omd_site(),
        mode=mode,
        host_names=host_names,
        scan=scan,
        raise_errors=raise_errors,
        timeout=timeout,
        non_blocking_http=non_blocking_http,
        debug=debug,
    )


def discovery(
    site_id: SiteId,
    mode: DiscoverySettings,
    host_names: Iterable[HostName],
    *,
    scan: bool,
    raise_errors: bool,
    timeout: int | None = None,
    non_blocking_http: bool = False,
    debug: bool,
) -> results.ServiceDiscoveryResult:
    return _deserialize(
        _automation_serialized(
            "service-discovery",
            automation_config=make_automation_config(active_config.sites[site_id]),
            args=[
                *(("@scan",) if scan else ()),
                *(("@raiseerrors",) if raise_errors else ()),
                mode.to_automation_arg(),
                *host_names,
            ],
            timeout=timeout,
            non_blocking_http=non_blocking_http,
            debug=debug,
        ),
        results.ServiceDiscoveryResult,
        debug=debug,
    )


def special_agent_discovery_preview(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    special_agent_preview_input: results.DiagSpecialAgentInput,
    *,
    debug: bool,
) -> results.SpecialAgentDiscoveryPreviewResult:
    return _deserialize(
        _automation_serialized(
            "special-agent-discovery-preview",
            automation_config=automation_config,
            args=None,
            stdin_data=special_agent_preview_input.serialize(
                cmk_version.Version.from_str(cmk_version.__version__)
            ),
            force_cli_interface=True,
            # the special agent discovery preview can take a long time depending on the underlying
            # datasource agent which can be problematic for remote setups
            timeout=5 * 60,
            debug=debug,
        ),
        results.SpecialAgentDiscoveryPreviewResult,
        debug=debug,
    )


def local_discovery_preview(
    host_name: HostName,
    *,
    prevent_fetching: bool,
    raise_errors: bool,
    debug: bool,
) -> results.ServiceDiscoveryPreviewResult:
    return _deserialize(
        _automation_serialized(
            "service-discovery-preview",
            automation_config=LocalAutomationConfig(),
            args=[
                *(("@nofetch",) if prevent_fetching else ()),
                *(("@raiseerrors",) if raise_errors else ()),
                host_name,
            ],
            debug=debug,
        ),
        results.ServiceDiscoveryPreviewResult,
        debug=debug,
    )


def autodiscovery(*, debug: bool) -> results.AutodiscoveryResult:
    return _deserialize(
        _automation_serialized(
            "autodiscovery",
            automation_config=LocalAutomationConfig(),
            debug=debug,
        ),
        results.AutodiscoveryResult,
        debug=debug,
    )


def set_autochecks_v2(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    checks: SetAutochecksInput,
    *,
    debug: bool,
) -> results.SetAutochecksV2Result:
    return _deserialize(
        _automation_serialized(
            "set-autochecks-v2",
            automation_config=automation_config,
            args=None,
            stdin_data=checks.serialize(),
            debug=debug,
        ),
        results.SetAutochecksV2Result,
        debug=debug,
    )


def update_host_labels(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    host_labels: Sequence[HostLabel],
    *,
    debug: bool,
) -> results.UpdateHostLabelsResult:
    return _deserialize(
        _automation_serialized(
            "update-host-labels",
            automation_config=automation_config,
            args=[host_name],
            indata={label.name: label.to_dict() for label in host_labels},
            debug=debug,
        ),
        results.UpdateHostLabelsResult,
        debug=debug,
    )


def rename_hosts(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    name_pairs: Sequence[tuple[HostName, HostName]],
    *,
    debug: bool,
) -> results.RenameHostsResult:
    return _deserialize(
        _automation_serialized(
            "rename-hosts",
            automation_config=automation_config,
            indata=name_pairs,
            non_blocking_http=True,
            debug=debug,
        ),
        results.RenameHostsResult,
        debug=debug,
    )


def get_services_labels(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    service_names: Iterable[ServiceName],
    *,
    debug: bool,
) -> results.GetServicesLabelsResult:
    return _deserialize(
        _automation_serialized(
            "get-services-labels",
            automation_config=automation_config,
            args=[host_name, *service_names],
            debug=debug,
        ),
        results.GetServicesLabelsResult,
        debug=debug,
    )


def get_service_name(
    host_name: HostName, check_plugin_name: CheckPluginName, item: Item, *, debug: bool
) -> results.GetServiceNameResult:
    return _deserialize(
        _automation_serialized(
            "get-service-name",
            automation_config=LocalAutomationConfig(),
            args=[host_name, str(check_plugin_name), repr(item)],
            debug=debug,
        ),
        results.GetServiceNameResult,
        debug=debug,
    )


def analyse_service(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    service_name: ServiceName,
    *,
    debug: bool,
) -> results.AnalyseServiceResult:
    return _deserialize(
        _automation_serialized(
            "analyse-service",
            automation_config=automation_config,
            args=[host_name, service_name],
            debug=debug,
        ),
        results.AnalyseServiceResult,
        debug=debug,
    )


def analyse_host(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    *,
    debug: bool,
) -> results.AnalyseHostResult:
    return _deserialize(
        _automation_serialized(
            "analyse-host",
            automation_config=automation_config,
            args=[host_name],
            debug=debug,
        ),
        results.AnalyseHostResult,
        debug=debug,
    )


def analyze_host_rule_matches(
    host_name: HostName,
    rules: Sequence[Sequence[RuleSpec]],
    *,
    debug: bool,
) -> results.AnalyzeHostRuleMatchesResult:
    return _deserialize(
        _automation_serialized(
            "analyze-host-rule-matches",
            automation_config=LocalAutomationConfig(),
            args=[host_name],
            indata=rules,
            debug=debug,
        ),
        results.AnalyzeHostRuleMatchesResult,
        debug=debug,
    )


def analyze_service_rule_matches(
    host_name: HostName,
    service_or_item: str,
    service_labels: Labels,
    rules: Sequence[Sequence[RuleSpec]],
    *,
    debug: bool,
) -> results.AnalyzeServiceRuleMatchesResult:
    return _deserialize(
        _automation_serialized(
            "analyze-service-rule-matches",
            automation_config=LocalAutomationConfig(),
            args=[host_name, service_or_item],
            indata=(rules, service_labels),
            debug=debug,
        ),
        results.AnalyzeServiceRuleMatchesResult,
        debug=debug,
    )


def analyze_host_rule_effectiveness(
    rules: Sequence[Sequence[RuleSpec]], *, debug: bool
) -> results.AnalyzeHostRuleEffectivenessResult:
    return _deserialize(
        _automation_serialized(
            "analyze-host-rule-effectiveness",
            automation_config=LocalAutomationConfig(),
            args=[],
            indata=rules,
            debug=debug,
        ),
        results.AnalyzeHostRuleEffectivenessResult,
        debug=debug,
    )


def delete_hosts(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_names: Sequence[HostName],
    debug: bool,
) -> results.DeleteHostsResult:
    return _deserialize(
        _automation_serialized(
            "delete-hosts",
            automation_config=automation_config,
            args=host_names,
            debug=debug,
        ),
        results.DeleteHostsResult,
        debug=debug,
    )


def restart(hosts_to_update: Sequence[HostName] | None, *, debug: bool) -> results.RestartResult:
    return _deserialize(
        _automation_serialized(
            "restart",
            automation_config=LocalAutomationConfig(),
            args=hosts_to_update,
            debug=debug,
        ),
        results.RestartResult,
        debug=debug,
    )


def reload(hosts_to_update: Sequence[HostName] | None, *, debug: bool) -> results.ReloadResult:
    return _deserialize(
        _automation_serialized(
            "reload",
            automation_config=LocalAutomationConfig(),
            args=hosts_to_update,
            debug=debug,
        ),
        results.ReloadResult,
        debug=debug,
    )


def get_configuration(
    config_var_names: Sequence[str],
    *,
    debug: bool,
) -> results.GetConfigurationResult:
    return _deserialize(
        _automation_serialized(
            "get-configuration",
            automation_config=LocalAutomationConfig(),
            indata=config_var_names,
            # We must not call this through the automation helper,
            # see automation call execution.
            force_cli_interface=True,
            debug=debug,
        ),
        results.GetConfigurationResult,
        debug=debug,
    )


def update_merged_password_file(*, debug: bool) -> results.UpdatePasswordsMergedFileResult:
    return _deserialize(
        _automation_serialized(
            "update-passwords-merged-file",
            automation_config=LocalAutomationConfig(),
            debug=debug,
        ),
        results.UpdatePasswordsMergedFileResult,
        debug=debug,
    )


def get_check_information(*, debug: bool) -> results.GetCheckInformationResult:
    return _deserialize(
        _automation_serialized(
            "get-check-information",
            automation_config=LocalAutomationConfig(),
            debug=debug,
        ),
        results.GetCheckInformationResult,
        debug=debug,
    )


@request_memoize()
def get_check_information_cached(*, debug: bool) -> Mapping[CheckPluginName, Mapping[str, str]]:
    raw_check_dict = get_check_information(debug=debug).plugin_infos
    return {CheckPluginName(name): info for name, info in sorted(raw_check_dict.items())}


def _get_section_information(*, debug: bool) -> results.GetSectionInformationResult:
    return _deserialize(
        _automation_serialized(
            "get-section-information",
            automation_config=LocalAutomationConfig(),
            debug=debug,
        ),
        results.GetSectionInformationResult,
        debug=debug,
    )


@request_memoize()
def get_section_information_cached(*, debug: bool) -> Mapping[str, Mapping[str, str]]:
    return _get_section_information(debug=debug).section_infos


def scan_parents(
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    timeout: int,
    probes: int,
    max_ttl: int,
    ping_probes: int,
    debug: bool,
) -> results.ScanParentsResult:
    return _deserialize(
        _automation_serialized(
            "scan-parents",
            automation_config=automation_config,
            args=[
                str(timeout),
                str(probes),
                str(max_ttl),
                str(ping_probes),
                host_name,
            ],
            debug=debug,
        ),
        results.ScanParentsResult,
        debug=debug,
    )


def diag_special_agent(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    diag_special_agent_input: results.DiagSpecialAgentInput,
    *,
    debug: bool,
) -> results.DiagSpecialAgentResult:
    return _deserialize(
        _automation_serialized(
            "diag-special-agent",
            automation_config=automation_config,
            args=None,
            stdin_data=diag_special_agent_input.serialize(
                cmk_version.Version.from_str(cmk_version.__version__)
            ),
            debug=debug,
        ),
        results.DiagSpecialAgentResult,
        debug=debug,
    )


def ping_host(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    ping_host_input: results.PingHostInput,
) -> results.PingHostResult:
    return _deserialize(
        _automation_serialized(
            "ping-host",
            automation_config=automation_config,
            args=None,
            stdin_data=ping_host_input.serialize(
                cmk_version.Version.from_str(cmk_version.__version__)
            ),
            debug=active_config.debug,
        ),
        results.PingHostResult,
        debug=active_config.debug,
    )


def diag_host(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    test: str,
    debug: bool,
    *args: str,
) -> results.DiagHostResult:
    return _deserialize(
        _automation_serialized(
            "diag-host",
            automation_config=automation_config,
            args=[host_name, test, *args],
            debug=debug,
        ),
        results.DiagHostResult,
        debug=debug,
    )


def diag_cmk_agent(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    diag_cmk_agent_input: results.DiagCmkAgentInput,
) -> results.DiagCmkAgentResult:
    return _deserialize(
        _automation_serialized(
            "diag-cmk-agent",
            automation_config=automation_config,
            args=None,
            stdin_data=diag_cmk_agent_input.serialize(
                cmk_version.Version.from_str(cmk_version.__version__)
            ),
            debug=active_config.debug,
        ),
        results.DiagCmkAgentResult,
        debug=active_config.debug,
    )


def active_check(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    check_type: str,
    item: str,
    *,
    debug: bool,
) -> results.ActiveCheckResult:
    return _deserialize(
        _automation_serialized(
            "active-check",
            automation_config=automation_config,
            args=[host_name, check_type, item],
            sync=False,
            debug=debug,
        ),
        results.ActiveCheckResult,
        debug=debug,
    )


def update_dns_cache(
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    debug: bool,
) -> results.UpdateDNSCacheResult:
    return _deserialize(
        _automation_serialized(
            "update-dns-cache",
            automation_config=automation_config,
            debug=debug,
        ),
        results.UpdateDNSCacheResult,
        debug=debug,
    )


def get_agent_output(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    host_name: HostName,
    agent_type: str,
    timeout: int | None,
    *,
    debug: bool,
) -> results.GetAgentOutputResult:
    return _deserialize(
        _automation_serialized(
            "get-agent-output",
            automation_config=automation_config,
            args=[host_name, agent_type],
            timeout=timeout,
            debug=debug,
        ),
        results.GetAgentOutputResult,
        debug=debug,
    )


def notification_replay(
    notification_number: int, *, debug: bool
) -> results.NotificationReplayResult:
    return _deserialize(
        _automation_serialized(
            "notification-replay",
            automation_config=LocalAutomationConfig(),
            args=[str(notification_number)],
            debug=debug,
        ),
        results.NotificationReplayResult,
        debug=debug,
    )


def notification_analyse(
    notification_number: int, *, debug: bool
) -> results.NotificationAnalyseResult:
    return _deserialize(
        _automation_serialized(
            "notification-analyse",
            automation_config=LocalAutomationConfig(),
            args=[str(notification_number)],
            debug=debug,
        ),
        results.NotificationAnalyseResult,
        debug=debug,
    )


def notification_test(
    raw_context: NotificationContext,
    dispatch: str,
    *,
    debug: bool,
) -> results.NotificationTestResult:
    return _deserialize(
        _automation_serialized(
            "notification-test",
            automation_config=LocalAutomationConfig(),
            args=[json.dumps(raw_context), dispatch],
            debug=debug,
        ),
        results.NotificationTestResult,
        debug=debug,
    )


def notification_get_bulks(*, only_ripe: bool, debug: bool) -> results.NotificationGetBulksResult:
    return _deserialize(
        _automation_serialized(
            "notification-get-bulks",
            automation_config=LocalAutomationConfig(),
            args=[str(int(only_ripe))],
            debug=debug,
        ),
        results.NotificationGetBulksResult,
        debug=debug,
    )


def create_diagnostics_dump(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    serialized_params: DiagnosticsCLParameters,
    timeout: int,
    *,
    debug: bool,
) -> results.CreateDiagnosticsDumpResult:
    return _deserialize(
        _automation_serialized(
            "create-diagnostics-dump",
            automation_config=automation_config,
            args=serialized_params,
            timeout=timeout,
            non_blocking_http=True,
            debug=debug,
        ),
        results.CreateDiagnosticsDumpResult,
        debug=debug,
    )


def bake_agents(
    *,
    indata: Mapping[str, Any] | None,
    force_automation_cli_interface: bool,
    debug: bool,
) -> results.BakeAgentsResult:
    return _deserialize(
        _automation_serialized(
            "bake-agents",
            automation_config=LocalAutomationConfig(),
            indata="" if indata is None else indata,
            force_cli_interface=force_automation_cli_interface,
            debug=debug,
        ),
        results.BakeAgentsResult,
        debug=debug,
    )


def find_unknown_check_parameter_rule_sets(
    *, debug: bool
) -> results.UnknownCheckParameterRuleSetsResult:
    return _deserialize(
        _automation_serialized(
            "find-unknown-check-parameter-rule-sets",
            automation_config=LocalAutomationConfig(),
            debug=debug,
        ),
        results.UnknownCheckParameterRuleSetsResult,
        debug=debug,
    )
