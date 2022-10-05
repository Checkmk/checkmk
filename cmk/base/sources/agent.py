#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Optional

import cmk.utils.misc
import cmk.utils.paths
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers.agent import AgentParser, AgentRawDataSection
from cmk.core_helpers.cache import SectionStore
from cmk.core_helpers.controller import FetcherType
from cmk.core_helpers.host_sections import HostSections

from ._abstract import Source

__all__ = ["AgentSource"]


class AgentSource(Source[AgentRawData, AgentRawDataSection]):
    """Configure agent checkers and fetchers.

    Args:
        main_data_source: The data source that is the "main" agent
            based data source uses the cache and persisted directories
            that existed before the data source concept has been added
            where each data source has it's own set of directories.

    """

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        fetcher_type: FetcherType,
        description: str,
        id_: str,
        main_data_source: bool,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
        file_cache_max_age: file_cache.MaxAge,
    ):
        super().__init__(
            hostname,
            ipaddress,
            source_type=source_type,
            fetcher_type=fetcher_type,
            description=description,
            default_raw_data=AgentRawData(b""),
            default_host_sections=HostSections[AgentRawDataSection](),
            id_=id_,
        )
        # TODO: We should cleanup these old directories one day.
        #       Then we can remove this special case
        self.main_data_source: Final[bool] = main_data_source
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self.agent_simulator: Final = agent_simulator
        self.check_interval: Final = check_interval
        if self.main_data_source:
            persisted_section_dir = Path(cmk.utils.paths.var_dir) / "persisted"
        else:
            persisted_section_dir = Path(cmk.utils.paths.var_dir) / "persisted_sections" / self.id
        self.persisted_section_dir: Final[Path] = persisted_section_dir
        if self.main_data_source:
            cache_dir = Path(cmk.utils.paths.tcp_cache_dir)
        else:
            cache_dir = Path(cmk.utils.paths.data_source_cache_dir) / self.id
        self.file_cache_base_path: Final[Path] = cache_dir
        self.simulation_mode: Final = simulation_mode
        self.file_cache_max_age: Final = file_cache_max_age

    def _make_parser(self) -> AgentParser:
        return AgentParser(
            self.hostname,
            SectionStore[AgentRawDataSection](
                self.persisted_section_dir / self.hostname,
                logger=self._logger,
            ),
            check_interval=self.check_interval,
            keep_outdated=self.use_outdated_persisted_sections,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            simulation=self.agent_simulator,
            logger=self._logger,
        )
