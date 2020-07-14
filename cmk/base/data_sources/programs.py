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
from cmk.utils.type_defs import HostAddress, HostName, RawAgentData, SectionName

from cmk.fetchers import ProgramDataFetcher

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.api.agent_based.section_types import AgentSectionPlugin
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

    def _execute(self) -> RawAgentData:
        self._logger.debug("Calling external program %r" % (self.source_cmdline))
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
        selected_raw_sections: Optional[Dict[SectionName, config.SectionPlugin]] = None,
        main_data_source: bool = False,
        id_="agent",
        cpu_tracking_id="ds",
    ) -> None:
        super(DSProgramDataSource, self).__init__(
            hostname,
            ipaddress,
            selected_raw_section_names=None if selected_raw_sections is None else
            {s.name for s in selected_raw_sections.values() if isinstance(s, AgentSectionPlugin)},
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
        selected_raw_sections: Optional[Dict[SectionName, config.SectionPlugin]] = None,
        main_data_source: bool = False,
    ) -> None:
        super(SpecialAgentDataSource, self).__init__(
            hostname,
            ipaddress,
            selected_raw_section_names=None if selected_raw_sections is None else
            {s.name for s in selected_raw_sections.values() if isinstance(s, AgentSectionPlugin)},
            main_data_source=main_data_source,
            id_="special_%s" % special_agent_id,
            cpu_tracking_id="ds",
        )
        self._special_agent_id = special_agent_id
        self._params = params

    @property
    def special_agent_plugin_file_name(self) -> str:
        return "agent_%s" % self._special_agent_id

    @property
    def _source_path(self) -> Path:
        local_path = cmk.utils.paths.local_agents_dir / "special" / self.special_agent_plugin_file_name
        if local_path.exists():
            return local_path
        return Path(cmk.utils.paths.agents_dir) / "special" / self.special_agent_plugin_file_name

    @property
    def _source_args(self) -> str:
        info_func = config.special_agent_info[self._special_agent_id]
        agent_configuration = info_func(self._params, self.hostname, self.ipaddress)
        return core_config.active_check_arguments(self.hostname, None, agent_configuration)

    @property
    def source_cmdline(self) -> str:
        """Create command line using the special_agent_info"""
        return "%s %s" % (self._source_path, self._source_args)

    @property
    def source_stdin(self) -> Optional[str]:
        """Create command line using the special_agent_info"""
        info_func = config.special_agent_info[self._special_agent_id]
        agent_configuration = info_func(self._params, self.hostname, self.ipaddress)
        if isinstance(agent_configuration, config.SpecialAgentConfiguration):
            return agent_configuration.stdin
        return None
