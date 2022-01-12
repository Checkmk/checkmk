#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Optional

import cmk.utils.misc
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, SourceType

from cmk.core_helpers.agent import AgentParser, AgentRawDataSection
from cmk.core_helpers.cache import SectionStore
from cmk.core_helpers.controller import FetcherType
from cmk.core_helpers.host_sections import HostSections

import cmk.base.config as config

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
            cache_dir=Path(cmk.utils.paths.tcp_cache_dir) if main_data_source else None,
            persisted_section_dir=(Path(cmk.utils.paths.var_dir) / "persisted")
            if main_data_source
            else None,
        )
        # TODO: We should cleanup these old directories one day.
        #       Then we can remove this special case
        self.main_data_source: Final[bool] = main_data_source

    def _make_parser(self) -> AgentParser:
        check_interval = config.HostConfig.make_host_config(self.hostname).check_mk_check_interval
        return AgentParser(
            self.hostname,
            SectionStore[AgentRawDataSection](
                self.persisted_sections_file_path,
                logger=self._logger,
            ),
            check_interval=check_interval,
            keep_outdated=self.use_outdated_persisted_sections,
            translation=config.get_piggyback_translations(self.hostname),
            encoding_fallback=config.fallback_agent_output_encoding,
            simulation=config.agent_simulator,
            logger=self._logger,
        )
