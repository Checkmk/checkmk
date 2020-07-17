#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
from pathlib import Path
from typing import Dict, Optional

from six import ensure_str

import cmk.utils.paths
from cmk.utils.type_defs import HostAddress, HostName, RawAgentData

from cmk.fetchers import ProgramDataFetcher

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import SelectedRawSections, SpecialAgentConfiguration
from cmk.base.exceptions import MKAgentError

from .agent import AgentDataSource


class ABCProgramDataSource(AgentDataSource):
    """Abstract base class for all data source classes that execute external programs"""
    @property
    @abc.abstractmethod
    def source_cmdline(self) -> str:
        """Return the command line to the source."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def source_stdin(self) -> Optional[str]:
        """Return the standard in of the source, or None."""
        raise NotImplementedError()

    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> RawAgentData:
        self._logger.debug("Calling external program %r" % (self.source_cmdline))
        # TODO(ml): Do something with the selection.
        with ProgramDataFetcher(
                self.source_cmdline,
                self.source_stdin,
                config.is_cmc(),
        ) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def describe(self) -> str:
        """Return a short textual description of the agent"""
        response = ["Program: %s" % self.source_cmdline]
        if self.source_stdin:
            response.extend(["  Program stdin:", self.source_stdin])
        return "\n".join(response)


class DSProgramDataSource(ABCProgramDataSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        command_template: str,
        main_data_source: bool = False,
        id_="agent",
        cpu_tracking_id="ds",
    ) -> None:
        super(DSProgramDataSource, self).__init__(
            hostname,
            ipaddress,
            main_data_source=main_data_source,
            id_="agent",
            cpu_tracking_id="ds",
        )
        self._command_template = command_template

    def name(self) -> str:
        """Return a unique (per host) textual identification of the data source"""
        program = self.source_cmdline.split(" ")[0]
        return os.path.basename(program)

    @property
    def source_cmdline(self) -> str:
        return DSProgramDataSource._translate(
            self._command_template,
            self._host_config,
            self.ipaddress,
        )

    @property
    def source_stdin(self):
        return None

    @staticmethod
    def _translate(
        cmd: str,
        host_config: config.HostConfig,
        ipaddress: Optional[HostAddress],
    ) -> str:
        return DSProgramDataSource._translate_host_macros(
            DSProgramDataSource._translate_legacy_macros(cmd, host_config.hostname, ipaddress),
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


class SpecialAgentDataSource(ABCProgramDataSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
        main_data_source: bool = False,
    ) -> None:
        super(SpecialAgentDataSource, self).__init__(
            hostname,
            ipaddress,
            main_data_source=main_data_source,
            id_="special_%s" % special_agent_id,
            cpu_tracking_id="ds",
        )
        self._special_agent_id = special_agent_id
        self._params = params
        self._cmdline = SpecialAgentDataSource._make_cmdline(
            hostname,
            ipaddress,
            special_agent_id,
            params,
        )
        self._stdin = SpecialAgentDataSource._make_stdin(
            hostname,
            ipaddress,
            special_agent_id,
            params,
        )
        self.special_agent_plugin_file_name = "agent_%s" % special_agent_id

    @property
    def source_cmdline(self) -> str:
        """Create command line using the special_agent_info"""
        return self._cmdline

    @property
    def source_stdin(self) -> Optional[str]:
        """Create command line using the special_agent_info"""
        return self._stdin

    @staticmethod
    def _make_cmdline(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> str:
        path = SpecialAgentDataSource._make_source_path(special_agent_id)
        args = SpecialAgentDataSource._make_source_args(
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
