#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Literal, Optional

from cmk.utils.exceptions import MKAgentError
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, IPMICredentials, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, IPMIFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentRawDataSection
from cmk.core_helpers.cache import FileCacheGlobals

from ._abstract import Source


class IPMISource(Source[AgentRawData, AgentRawDataSection]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        fetcher_type: FetcherType,
        id_: Literal["mgmt_ipmi"],
        cache_dir: Path,
        simulation_mode: bool,
        management_credentials: IPMICredentials,
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

        self.credentials: Final = management_credentials

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCache(
            self.hostname,
            base_path=self.file_cache_base_path,
            max_age=self.file_cache_max_age,
            use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
            simulation=self.simulation_mode,
            use_only_cache=False,
            file_cache_mode=FileCacheGlobals.file_cache_mode(),
        )

    def _make_fetcher(self) -> IPMIFetcher:
        if self.ipaddress is None:
            raise MKAgentError("Missing IP address")

        return IPMIFetcher(
            ident=self.id,
            address=self.ipaddress,
            username=self.credentials.get("username"),
            password=self.credentials.get("password"),
        )
