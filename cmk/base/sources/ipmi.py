#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Literal, Optional

from cmk.utils.exceptions import MKAgentError
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, IPMICredentials, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, IPMIFetcher
from cmk.core_helpers.agent import AgentFileCache
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode
from cmk.core_helpers.ipmi import IPMISummarizer

from .agent import AgentSource


class IPMISource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        id_: Literal["mgmt_ipmi"],
        persisted_section_dir: Path,
        cache_dir: Path,
        simulation_mode: bool,
        agent_simulator: bool,
        keep_outdated: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
        management_credentials: IPMICredentials,
        file_cache_max_age: file_cache.MaxAge,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.MANAGEMENT,
            fetcher_type=FetcherType.IPMI,
            id_=id_,
            persisted_section_dir=persisted_section_dir,
            agent_simulator=agent_simulator,
            keep_outdated=keep_outdated,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
        )
        self.file_cache_base_path: Final = cache_dir
        self.simulation_mode: Final = simulation_mode
        self.file_cache_max_age: Final = file_cache_max_age

        self.credentials: Final = management_credentials

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCache(
            self.hostname,
            base_path=self.file_cache_base_path,
            max_age=self.file_cache_max_age,
            use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
            simulation=self.simulation_mode,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED
            if FileCacheGlobals.disabled
            else FileCacheMode.READ_WRITE,
        )

    def _make_fetcher(self) -> IPMIFetcher:
        if self.ipaddress is None:
            raise MKAgentError("Missing IP address")

        return IPMIFetcher(
            address=self.ipaddress,
            username=self.credentials.get("username"),
            password=self.credentials.get("password"),
        )

    def _make_summarizer(self, *, exit_spec: ExitSpec) -> IPMISummarizer:
        return IPMISummarizer(exit_spec)
