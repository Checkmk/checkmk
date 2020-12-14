#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, List, Optional, Tuple

from cmk.utils.paths import tmp_dir
from cmk.utils.piggyback import get_piggyback_raw_data
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, ServiceCheckResult, SourceType

from cmk.fetchers import FetcherType, PiggybackFetcher
from cmk.fetchers.agent import NoCache

import cmk.base.config as config

from ._abstract import Mode
from .agent import AgentHostSections, AgentSource, AgentSummarizer, NoCacheFactory


class PiggybackSource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PIGGYBACK,
            description=PiggybackSource._make_description(hostname),
            id_="piggyback",
            main_data_source=False,
        )
        self.time_settings: Final = (config.get_config_cache().get_piggybacked_hosts_time_settings(
            piggybacked_hostname=hostname))

    def _make_file_cache(self) -> NoCache:
        return NoCacheFactory(
            path=self.file_cache_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> PiggybackFetcher:
        return PiggybackFetcher(
            self._make_file_cache(),
            hostname=self.hostname,
            address=self.ipaddress,
            time_settings=self.time_settings,
        )

    def _make_summarizer(self) -> "PiggybackSummarizer":
        return PiggybackSummarizer(
            self.exit_spec,
            hostname=self.hostname,
            ipaddress=self.ipaddress,
            time_settings=self.time_settings,
            # Tag: 'Always use and expect piggback data'
            always='piggyback' in self.host_config.tags,
        )

    @staticmethod
    def _make_description(hostname: HostName):
        return "Process piggyback data from %s" % (Path(tmp_dir) / "piggyback" / hostname)


class PiggybackSummarizer(AgentSummarizer):
    def __init__(
        self,
        exit_spec: ExitSpec,
        *,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        time_settings: List[Tuple[Optional[str], str, int]],
        always: bool,
    ) -> None:
        super().__init__(exit_spec)
        self.hostname = hostname
        self.ipaddress = ipaddress
        self.time_settings = time_settings
        self.always = always

    def summarize_success(
        self,
        host_sections: AgentHostSections,
        *,
        mode: Mode,
    ) -> ServiceCheckResult:
        """Returns useful information about the data source execution

        Return only summary information in case there is piggyback data"""

        if mode is not Mode.CHECKING:
            # Check_MK Discovery: Do not display information about piggyback files
            # and source status file
            return 0, '', []

        summary = self._summarize_impl()
        if self.always and not summary:
            return 1, 'Missing data', []

        if not host_sections:
            return 0, "", []

        return summary

    def _summarize_impl(self) -> ServiceCheckResult:
        states = [0]
        infotexts = set()
        for origin in (self.hostname, self.ipaddress):
            for src in get_piggyback_raw_data(
                    origin if origin else "",
                    self.time_settings,
            ):
                states.append(src.reason_status)
                infotexts.add(src.reason)
        return max(states), ", ".join(infotexts), []
