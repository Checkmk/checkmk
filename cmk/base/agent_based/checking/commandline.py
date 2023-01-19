#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container
from functools import partial

import cmk.utils.version as cmk_version
from cmk.utils.log import console
from cmk.utils.type_defs import CheckPluginName, EVERYTHING, HostAddress, HostName, ServiceState

from cmk.fetchers import FetcherFunction

from cmk.checkers import ParserFunction, SummarizerFunction
from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.submitters import Submitter

import cmk.base.agent_based.error_handling as error_handling
from cmk.base.config import ConfigCache

from ._checking import execute_checkmk_checks

__all__ = ["commandline_checking"]


def commandline_checking(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: SummarizerFunction,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    submitter: Submitter,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
    perfdata_with_times: bool,
) -> ServiceState:
    # The error handling is required for the Nagios core.
    return error_handling.check_result(
        partial(
            _commandline_checking,
            host_name,
            ipaddress,
            config_cache=config_cache,
            fetcher=fetcher,
            parser=parser,
            summarizer=summarizer,
            run_plugin_names=run_plugin_names,
            perfdata_with_times=perfdata_with_times,
            submitter=submitter,
        ),
        exit_spec=config_cache.exit_code_spec(host_name),
        host_name=host_name,
        service_name="Check_MK",
        plugin_name="mk",
        is_cluster=config_cache.is_cluster(host_name),
        snmp_backend=config_cache.get_snmp_backend(host_name),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )


def _commandline_checking(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    perfdata_with_times: bool,
    submitter: Submitter,
) -> ActiveCheckResult:
    console.vverbose("Checkmk version %s\n", cmk_version.__version__)
    fetched = fetcher(host_name, ip_address=ipaddress)
    return execute_checkmk_checks(
        hostname=host_name,
        config_cache=config_cache,
        fetched=fetched,
        parser=parser,
        summarizer=summarizer,
        run_plugin_names=run_plugin_names,
        perfdata_with_times=perfdata_with_times,
        submitter=submitter,
    )
