#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Optional

from cmk.utils.paths import tmp_dir
from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.fetchers import FetcherType, PiggybackFetcher
from cmk.fetchers.agent import NoCache, NoCacheFactory
from cmk.fetchers.piggyback import PiggybackSummarizer
from cmk.fetchers.type_defs import Mode

import cmk.base.config as config

from .agent import AgentSource


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

    def _make_summarizer(self) -> PiggybackSummarizer:
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
