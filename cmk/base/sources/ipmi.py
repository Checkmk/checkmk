#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final, Literal, Optional

from cmk.utils.exceptions import MKAgentError
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, IPMICredentials, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, IPMIFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentFileCacheFactory
from cmk.core_helpers.ipmi import IPMISummarizer

from .agent import AgentSource


class IPMISource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        id_: Literal["mgmt_ipmi"],
        simulation_mode: bool,
        agent_simulator: bool,
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
            description=IPMISource._make_description(ipaddress, management_credentials),
            id_=id_,
            main_data_source=False,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
            file_cache_max_age=file_cache_max_age,
        )
        self.credentials: Final = management_credentials

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCacheFactory(
            self.hostname,
            base_path=self.file_cache_base_path,
            simulation=self.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

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

    @staticmethod
    def _make_description(  # type:ignore[no-untyped-def]
        ipaddress: Optional[HostAddress], credentials: IPMICredentials
    ):
        description = "Management board - IPMI"
        items = []
        if ipaddress:
            items.append("Address: %s" % ipaddress)
        if credentials:
            items.append("User: %s" % credentials["username"])
        if items:
            description = "%s (%s)" % (description, ", ".join(items))
        return description
