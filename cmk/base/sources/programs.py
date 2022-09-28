#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, SourceType

from cmk.core_helpers import FetcherType, ProgramFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentFileCacheFactory, AgentSummarizerDefault

import cmk.base.config as config

from .agent import AgentSource


class ProgramSource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
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
        check_interval: int,
    ) -> None:
        super().__init__(
            hostname,
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
            check_interval=check_interval,
        )
        self.cmdline = cmdline
        self.stdin = stdin

    @staticmethod
    def special_agent(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        agentname: str,
        cmdline: str,
        stdin: Optional[str],
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
    ) -> "SpecialAgentSource":
        return SpecialAgentSource(
            hostname,
            ipaddress,
            main_data_source=main_data_source,
            agentname=agentname,
            cmdline=cmdline,
            stdin=stdin,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
        )

    @staticmethod
    def ds(
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        main_data_source: bool = False,
        cmdline: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
    ) -> "DSProgramSource":
        return DSProgramSource(
            hostname,
            ipaddress,
            main_data_source=main_data_source,
            cmdline=cmdline,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
        )

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCacheFactory(
            self.hostname,
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

    def _make_summarizer(self, *, exit_spec: ExitSpec) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(exit_spec)

    @staticmethod
    def _make_description(cmdline, stdin):
        response = ["Program: %s" % cmdline]
        if stdin:
            response.extend(["  Program stdin:", stdin])
        return "\n".join(response)


class DSProgramSource(ProgramSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        cmdline: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            id_="agent",
            main_data_source=main_data_source,
            cmdline=cmdline,
            stdin=None,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
        )


class SpecialAgentSource(ProgramSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        agentname: str,
        cmdline: str,
        stdin: Optional[str],
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            id_=f"special_{agentname}",
            main_data_source=main_data_source,
            cmdline=cmdline,
            stdin=stdin,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
        )
        self.special_agent_id = agentname
        self.special_agent_plugin_file_name = "agent_%s" % agentname
