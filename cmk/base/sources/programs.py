#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Optional

from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.core_helpers import FetcherType, ProgramFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentFileCacheFactory, AgentSummarizerDefault

import cmk.base.config as config
from cmk.base.config import HostConfig

from .agent import AgentSource


class ProgramSource(AgentSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        id_: str,
        main_data_source: bool,
        cmdline: str,
        stdin: Optional[str],
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PROGRAM,
            description=ProgramSource._make_description(
                cmdline,
                stdin,
            ),
            id_=id_,
            main_data_source=main_data_source,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )
        self.cmdline = cmdline
        self.stdin = stdin

    @staticmethod
    def special_agent(
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        agentname: str,
        params: Dict,
        cmdline: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> "SpecialAgentSource":
        return SpecialAgentSource(
            host_config,
            ipaddress,
            main_data_source=main_data_source,
            agentname=agentname,
            params=params,
            cmdline=cmdline,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )

    @staticmethod
    def ds(
        host_config: HostConfig,
        ipaddress: HostAddress,
        *,
        main_data_source: bool = False,
        cmdline: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> "DSProgramSource":
        return DSProgramSource(
            host_config,
            ipaddress,
            main_data_source=main_data_source,
            cmdline=cmdline,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCacheFactory(
            self.host_config.hostname,
            base_path=self.file_cache_base_path,
            simulation=self.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> ProgramFetcher:
        return ProgramFetcher(
            cmdline=self.cmdline,
            stdin=self.stdin,
            is_cmc=config.is_cmc(),
        )

    def _make_summarizer(self) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(self.exit_spec)

    @staticmethod
    def _make_description(cmdline, stdin):
        response = ["Program: %s" % cmdline]
        if stdin:
            response.extend(["  Program stdin:", stdin])
        return "\n".join(response)


class DSProgramSource(ProgramSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        cmdline: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            id_="agent",
            main_data_source=main_data_source,
            cmdline=cmdline,
            stdin=None,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )


class SpecialAgentSource(ProgramSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        agentname: str,
        cmdline: str,
        params: Dict,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            id_=f"special_{agentname}",
            main_data_source=main_data_source,
            cmdline=cmdline,
            stdin=SpecialAgentSource._make_stdin(
                host_config.hostname,
                ipaddress,
                agentname,
                params,
            ),
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )
        self.special_agent_id = agentname
        self.special_agent_plugin_file_name = "agent_%s" % agentname

    @staticmethod
    def _make_stdin(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        agentname: str,
        params: Dict,
    ) -> Optional[str]:
        info_func = config.special_agent_info[agentname]
        # TODO: We call a user supplied function here.
        # If this crashes during config generation, it can get quite ugly.
        # We should really wrap this and implement proper sanitation and exception handling.
        # Deal with this when modernizing the API (CMK-3812).
        agent_configuration = info_func(params, hostname, ipaddress)
        return getattr(agent_configuration, "stdin", None)
