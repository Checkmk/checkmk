#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final, Optional

from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.core_helpers import FetcherType, PushAgentFetcher
from cmk.core_helpers.agent import AgentSummarizerDefault
from cmk.core_helpers.push_agent import PushAgentFileCache, PushAgentFileCacheFactory

import cmk.base.config as config

from .agent import AgentSource


class PushAgentSource(AgentSource):
    use_only_cache = False

    ID: Final = "push-agent"

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PUSH_AGENT,
            description="Checkmk push agent",
            id_=self.ID,
            main_data_source=False,
        )

    def _make_file_cache(self) -> PushAgentFileCache:
        return PushAgentFileCacheFactory(
            self.hostname,
            base_path=self.file_cache_base_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> PushAgentFetcher:
        return PushAgentFetcher(
            self._make_file_cache(),
            allowed_age=self._make_allowed_age(),
            use_only_cache=self.use_only_cache,
        )

    def _make_summarizer(self) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(
            self.exit_spec,
            is_cluster=self.host_config.is_cluster,
            agent_min_version=config.agent_min_version,
            agent_target_version=self.host_config.agent_target_version,
            only_from=None,
        )

    def _make_allowed_age(self) -> int:
        # convert to seconds and add grace period
        return int(1.5 * 60 * self.host_config.check_mk_check_interval)
