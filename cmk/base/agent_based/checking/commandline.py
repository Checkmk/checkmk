#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Mapping

import cmk.utils.version as cmk_version
from cmk.utils.log import console
from cmk.utils.type_defs import (
    CheckPluginName,
    EVERYTHING,
    HostAddress,
    HostName,
    InventoryPluginName,
    SectionName,
    ServiceState,
)

from cmk.fetchers import FetcherFunction

from cmk.checkers import ParserFunction, SummarizerFunction
from cmk.checkers.error_handling import CheckResultErrorHandler
from cmk.checkers.submitters import Submitter

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.inventory_classes import InventoryPlugin
from cmk.base.api.agent_based.type_defs import SectionPlugin
from cmk.base.config import ConfigCache

from ._checking import execute_checkmk_checks

__all__ = ["commandline_checking"]


def commandline_checking(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    error_handler: CheckResultErrorHandler,
    section_plugins: Mapping[SectionName, SectionPlugin],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    perfdata_with_times: bool,
    submitter: Submitter,
) -> tuple[ServiceState, str]:
    with error_handler:
        console.vverbose("Checkmk version %s\n", cmk_version.__version__)
        fetched = fetcher(host_name, ip_address=ipaddress)
        check_result = execute_checkmk_checks(
            hostname=host_name,
            config_cache=config_cache,
            fetched=fetched,
            parser=parser,
            summarizer=summarizer,
            section_plugins=section_plugins,
            check_plugins=check_plugins,
            inventory_plugins=inventory_plugins,
            run_plugin_names=run_plugin_names,
            perfdata_with_times=perfdata_with_times,
            submitter=submitter,
        )
        return check_result.state, check_result.as_text()

    if error_handler.result is not None:
        return error_handler.result

    return (3, "unknown error")
