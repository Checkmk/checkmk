#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Dict, Optional

from six import ensure_str

import cmk.utils.paths
from cmk.utils.type_defs import HostAddress, HostName, RawAgentData, SourceType

from cmk.fetchers import ProgramDataFetcher

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import SelectedRawSections, SpecialAgentConfiguration
from cmk.base.exceptions import MKAgentError

from ._abstract import Mode
from .agent import AgentConfigurator, AgentDataSource


class ProgramConfigurator(AgentConfigurator):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        id_: str,
        cpu_tracking_id: str,
        cmdline: str,
        stdin: Optional[str],
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.HOST,
            description=ProgramConfigurator._make_description(
                cmdline,
                stdin,
            ),
            id_=id_,
            cpu_tracking_id=cpu_tracking_id,
        )
        self.cmdline = cmdline
        self.stdin = stdin

    @staticmethod
    def special_agent(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        special_agent_id: str,
        params: Dict,
    ) -> "SpecialAgentConfigurator":
        return SpecialAgentConfigurator(
            hostname,
            ipaddress,
            mode=mode,
            special_agent_id=special_agent_id,
            params=params,
        )

    @staticmethod
    def ds(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        template: str,
    ) -> "DSProgramConfigurator":
        return DSProgramConfigurator(hostname, ipaddress, mode=mode, template=template)

    def configure_fetcher(self) -> Dict[str, Any]:
        return {
            "cmdline": self.cmdline,
            "stdin": self.stdin,
            "is_cmc": config.is_cmc(),
        }

    @staticmethod
    def _make_description(cmdline, stdin):
        response = ["Program: %s" % cmdline]
        if stdin:
            response.extend(["  Program stdin:", stdin])
        return "\n".join(response)


class DSProgramConfigurator(ProgramConfigurator):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        template: str,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            id_="agent",
            cpu_tracking_id="ds",
            cmdline=DSProgramConfigurator._translate(
                template,
                hostname,
                ipaddress,
            ),
            stdin=None,
        )

    @staticmethod
    def _translate(
        cmd: str,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> str:
        host_config = config.HostConfig.make_host_config(hostname)
        return DSProgramConfigurator._translate_host_macros(
            DSProgramConfigurator._translate_legacy_macros(cmd, hostname, ipaddress),
            host_config,
        )

    @staticmethod
    def _translate_legacy_macros(
        cmd: str,
        hostname: HostName,
        ipaddress: Optional[HostName],
    ) -> str:
        # Make "legacy" translation. The users should use the $...$ macros in future
        return cmd.replace("<IP>", ipaddress or "").replace("<HOST>", hostname)

    @staticmethod
    def _translate_host_macros(cmd: str, host_config: config.HostConfig) -> str:
        config_cache = config.get_config_cache()
        attrs = core_config.get_host_attributes(host_config.hostname, config_cache)
        if host_config.is_cluster:
            parents_list = core_config.get_cluster_nodes_for_config(
                config_cache,
                host_config,
            )
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(
                core_config.get_cluster_attributes(
                    config_cache,
                    host_config,
                    parents_list,
                ))

        macros = core_config.get_host_macros_from_attributes(host_config.hostname, attrs)
        return ensure_str(core_config.replace_macros(cmd, macros))


class SpecialAgentConfigurator(ProgramConfigurator):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        special_agent_id: str,
        params: Dict,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            id_="special_%s" % special_agent_id,
            cpu_tracking_id="ds",
            cmdline=SpecialAgentConfigurator._make_cmdline(
                hostname,
                ipaddress,
                special_agent_id,
                params,
            ),
            stdin=SpecialAgentConfigurator._make_stdin(
                hostname,
                ipaddress,
                special_agent_id,
                params,
            ),
        )
        self.special_agent_id = special_agent_id
        self.special_agent_plugin_file_name = "agent_%s" % special_agent_id

    @staticmethod
    def _make_cmdline(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> str:
        path = SpecialAgentConfigurator._make_source_path(special_agent_id)
        args = SpecialAgentConfigurator._make_source_args(
            hostname,
            ipaddress,
            special_agent_id,
            params,
        )
        return "%s %s" % (path, args)

    @staticmethod
    def _make_stdin(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> Optional[str]:
        info_func = config.special_agent_info[special_agent_id]
        agent_configuration = info_func(params, hostname, ipaddress)
        if isinstance(agent_configuration, SpecialAgentConfiguration):
            return agent_configuration.stdin
        return None

    @staticmethod
    def _make_source_path(special_agent_id: str) -> Path:
        file_name = "agent_%s" % special_agent_id
        local_path = cmk.utils.paths.local_agents_dir / "special" / file_name
        if local_path.exists():
            return local_path
        return Path(cmk.utils.paths.agents_dir) / "special" / file_name

    @staticmethod
    def _make_source_args(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> str:
        info_func = config.special_agent_info[special_agent_id]
        agent_configuration = info_func(params, hostname, ipaddress)
        return core_config.active_check_arguments(hostname, None, agent_configuration)


class ProgramDataSource(AgentDataSource):
    """Abstract base class for all data source classes that execute external programs"""
    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> RawAgentData:
        # TODO(ml): Do something with the selection.
        with ProgramDataFetcher.from_json(self.configurator.configure_fetcher()) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")
