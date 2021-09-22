#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Iterable, NamedTuple, Optional, Sequence, Tuple, Type, TypeVar

from livestatus import SiteId

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import DiscoveredHostLabelsDict, HostName, ServiceName, SetAutochecksTable

from cmk.automations import results

from cmk.gui.i18n import _
from cmk.gui.sites import site_is_local
from cmk.gui.watolib.automations import (
    _check_mk_remote_automation_serialized,
    check_mk_local_automation_serialized,
    local_automation_failure,
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
    siteid: Optional[SiteId] = None,
    args: Optional[Sequence[str]] = None,
    indata: Any = "",
    stdin_data: Optional[str] = None,
    timeout: Optional[int] = None,
    sync: bool = True,
    non_blocking_http: bool = False,
) -> AutomationResponse:
    if args is None:
        args = []

    if not siteid or site_is_local(siteid):
        cmdline, serialized_result = check_mk_local_automation_serialized(
            command=command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
        )
        return AutomationResponse(
            command=command,
            serialized_result=serialized_result,
            local=True,
            cmdline=cmdline,
        )

    return AutomationResponse(
        command=command,
        serialized_result=_check_mk_remote_automation_serialized(
            site_id=siteid,
            command=command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
            sync=sync,
            non_blocking_http=non_blocking_http,
        ),
        local=False,
        cmdline=[],
    )


def _automation_failure(
    response: AutomationResponse,
    exception: SyntaxError,
) -> MKGeneralException:
    if response.local:
        return local_automation_failure(
            command=response.command,
            cmdline=response.cmdline,
            out=response.serialized_result,
            exc=exception,
        )
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
    result_type: Type[_ResultType],
) -> _ResultType:
    try:
        return result_type.deserialize(response.serialized_result)
    except SyntaxError as excpt:
        raise _automation_failure(
            response,
            excpt,
        )


def discovery(
    site_id: SiteId,
    mode: str,
    flags: Iterable[str],
    host_names: Iterable[HostName],
    *,
    timeout: Optional[int] = None,
    non_blocking_http: bool = False,
) -> results.DiscoveryResult:
    return _deserialize(
        _automation_serialized(
            "inventory",
            siteid=site_id,
            args=[*flags, mode, *host_names],
            timeout=timeout,
            non_blocking_http=non_blocking_http,
        ),
        results.DiscoveryResult,
    )


def try_discovery(
    site_id: SiteId,
    flags: Iterable[str],
    host_name: HostName,
) -> results.TryDiscoveryResult:
    return _deserialize(
        _automation_serialized(
            "try-inventory",
            siteid=site_id,
            args=[*flags, host_name],
        ),
        results.TryDiscoveryResult,
    )


def set_autochecks(
    site_id: SiteId,
    host_name: HostName,
    checks: SetAutochecksTable,
) -> results.SetAutochecksResult:
    return _deserialize(
        _automation_serialized(
            "set-autochecks",
            siteid=site_id,
            args=[host_name],
            indata=checks,
        ),
        results.SetAutochecksResult,
    )


def update_host_labels(
    site_id: SiteId,
    host_name: HostName,
    host_labels: DiscoveredHostLabelsDict,
) -> results.UpdateHostLabelsResult:
    return _deserialize(
        _automation_serialized(
            "update-host-labels",
            siteid=site_id,
            args=[host_name],
            indata=host_labels,
        ),
        results.UpdateHostLabelsResult,
    )


def rename_hosts(
    site_id: SiteId,
    name_pairs: Sequence[Tuple[HostName, HostName]],
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
