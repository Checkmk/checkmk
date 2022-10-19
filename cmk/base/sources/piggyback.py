#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Literal, Optional, Sequence, Tuple

from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, PiggybackFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentRawDataSection
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode

from ._abstract import Source


class PiggybackSource(Source[AgentRawData, AgentRawDataSection]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        fetcher_type: FetcherType,
        id_: Literal["piggyback"],
        cache_dir: Path,
        simulation_mode: bool,
        time_settings: Sequence[Tuple[Optional[str], str, int]],
        file_cache_max_age: file_cache.MaxAge,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=source_type,
            fetcher_type=fetcher_type,
            id_=id_,
        )
        self.file_cache_base_path: Final = cache_dir
        self.simulation_mode: Final = simulation_mode
        self.file_cache_max_age: Final = file_cache_max_age

        self.time_settings: Final = time_settings

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCache(
            self.hostname,
            path_template="",
            max_age=self.file_cache_max_age,
            use_outdated=FileCacheGlobals.use_outdated,
            simulation=False,  # TODO Quickfix for SUP-9912, should be handled in a better way
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    def _make_fetcher(self) -> PiggybackFetcher:
        return PiggybackFetcher(
            ident=self.id,
            hostname=self.hostname,
            address=self.ipaddress,
            time_settings=self.time_settings,
        )
