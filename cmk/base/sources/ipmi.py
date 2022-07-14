#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, Final, Optional

from cmk.utils.exceptions import MKAgentError
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import HostAddress, SourceType

from cmk.core_helpers import FetcherType, IPMIFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentFileCacheFactory
from cmk.core_helpers.ipmi import IPMISummarizer

from cmk.base.config import HostConfig, IPMICredentials

from .agent import AgentSource


class IPMISource(AgentSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            source_type=SourceType.MANAGEMENT,
            fetcher_type=FetcherType.IPMI,
            description=IPMISource._make_description(
                ipaddress,
                cast(IPMICredentials, host_config.management_credentials),
            ),
            id_="mgmt_ipmi",
            main_data_source=False,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )
        self.credentials: Final[IPMICredentials] = self.get_ipmi_credentials(host_config)

    @staticmethod
    def get_ipmi_credentials(host_config: HostConfig) -> IPMICredentials:
        credentials = host_config.management_credentials
        if credentials is None:
            return {}
        # The cast is required because host_config.management_credentials
        # has type `Union[None, str, Tuple[str, ...], Dict[str, str]]`
        return cast(IPMICredentials, credentials)

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCacheFactory(
            self.host_config.hostname,
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

    def _make_summarizer(self) -> IPMISummarizer:
        return IPMISummarizer(self.exit_spec)

    @staticmethod
    def _make_description(ipaddress: Optional[HostAddress], credentials: IPMICredentials):
        description = "Management board - IPMI"
        items = []
        if ipaddress:
            items.append("Address: %s" % ipaddress)
        if credentials:
            items.append("User: %s" % credentials["username"])
        if items:
            description = "%s (%s)" % (description, ", ".join(items))
        return description
