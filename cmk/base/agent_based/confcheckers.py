#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Concrete implementation of checkers functionality."""

from __future__ import annotations

import itertools
import logging
from collections.abc import Iterable, Sequence
from typing import Final

import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, result

from cmk.snmplib.type_defs import SNMPRawData

from cmk.fetchers import fetch_all, Mode, SourceInfo
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkers import parse_raw_data
from cmk.checkers.host_sections import HostSections
from cmk.checkers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.config as config
from cmk.base.config import ConfigCache
from cmk.base.sources import make_parser, make_sources

__all__ = ["ConfiguredParser", "ConfiguredFetcher"]


class ConfiguredParser:
    def __init__(
        self,
        config_cache: ConfigCache,
        *,
        selected_sections: SectionNameCollection,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        self.config_cache: Final = config_cache
        self.selected_sections: Final = selected_sections
        self.keep_outdated: Final = keep_outdated
        self.logger: Final = logger

    def __call__(
        self,
        fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        """Parse fetched data."""
        console.vverbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())
        output: list[tuple[SourceInfo, result.Result[HostSections, Exception]]] = []
        # Special agents can produce data for the same check_plugin_name on the same host, in this case
        # the section lines need to be extended
        for source, raw_data in fetched:
            source_result = parse_raw_data(
                make_parser(
                    self.config_cache,
                    source,
                    checking_sections=self.config_cache.make_checking_sections(
                        source.hostname, selected_sections=NO_SELECTION
                    ),
                    keep_outdated=self.keep_outdated,
                    logger=self.logger,
                ),
                raw_data,
                selection=self.selected_sections,
            )
            output.append((source, source_result))
        return output


class ConfiguredFetcher:
    def __init__(
        self,
        config_cache: ConfigCache,
        *,
        # alphabetically sorted
        file_cache_options: FileCacheOptions,
        force_snmp_cache_refresh: bool,
        mode: Mode,
        on_error: OnError,
        selected_sections: SectionNameCollection,
        simulation_mode: bool,
        max_cachefile_age: MaxAge | None = None,
    ) -> None:
        self.config_cache: Final = config_cache
        self.file_cache_options: Final = file_cache_options
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.mode: Final = mode
        self.on_error: Final = on_error
        self.selected_sections: Final = selected_sections
        self.simulation_mode: Final = simulation_mode
        self.max_cachefile_age: Final = max_cachefile_age

    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        nodes = self.config_cache.nodes_of(host_name)
        if nodes is None:
            # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
            # address is unknown). When called as non keepalive ipaddress may be None or
            # is already an address (2nd argument)
            hosts = [
                (host_name, ip_address or config.lookup_ip_address(self.config_cache, host_name))
            ]
        else:
            hosts = [(node, config.lookup_ip_address(self.config_cache, node)) for node in nodes]

        return fetch_all(
            itertools.chain.from_iterable(
                make_sources(
                    host_name_,
                    ip_address_,
                    config_cache=self.config_cache,
                    force_snmp_cache_refresh=(
                        self.force_snmp_cache_refresh if nodes is None else False
                    ),
                    selected_sections=self.selected_sections if nodes is None else NO_SELECTION,
                    on_scan_error=self.on_error if nodes is None else OnError.RAISE,
                    simulation_mode=self.simulation_mode,
                    file_cache_options=self.file_cache_options,
                    file_cache_max_age=self.max_cachefile_age
                    or self.config_cache.max_cachefile_age(host_name),
                )
                for host_name_, ip_address_ in hosts
            ),
            mode=self.mode,
        )
