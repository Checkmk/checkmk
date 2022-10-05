#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Literal, Optional, Sequence, Tuple

from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, PiggybackFetcher
from cmk.core_helpers.agent import AgentFileCache
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode
from cmk.core_helpers.piggyback import PiggybackSummarizer

from .agent import AgentSource


class PiggybackSource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        id_: Literal["piggyback"],
        persisted_section_dir: Path,
        cache_dir: Path,
        simulation_mode: bool,
        agent_simulator: bool,
        time_settings: Sequence[Tuple[Optional[str], str, int]],
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
        is_piggyback_host: bool,
        file_cache_max_age: file_cache.MaxAge,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PIGGYBACK,
            id_=id_,
            persisted_section_dir=persisted_section_dir,
            cache_dir=cache_dir,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
            file_cache_max_age=file_cache_max_age,
        )
        self.time_settings: Final = time_settings
        # Tag: 'Always use and expect piggback data'
        self.is_piggyback_host: Final = is_piggyback_host

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCache(
            self.hostname,
            base_path=self.file_cache_base_path,
            max_age=self.file_cache_max_age,
            use_outdated=FileCacheGlobals.use_outdated,
            simulation=False,  # TODO Quickfix for SUP-9912, should be handled in a better way
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    def _make_fetcher(self) -> PiggybackFetcher:
        return PiggybackFetcher(
            hostname=self.hostname,
            address=self.ipaddress,
            time_settings=self.time_settings,
        )

    def _make_summarizer(self, *, exit_spec: ExitSpec) -> PiggybackSummarizer:
        return PiggybackSummarizer(
            exit_spec,
            hostname=self.hostname,
            ipaddress=self.ipaddress,
            time_settings=self.time_settings,
            always=self.is_piggyback_host,
        )
