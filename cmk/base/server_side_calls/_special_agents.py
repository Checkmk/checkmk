#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.hostaddress import HostAddress, HostName

from cmk.discover_plugins import discover_executable, family_libexec_dir, PluginLocation
from cmk.server_side_calls.v1 import HostConfig, HTTPProxy, SpecialAgentConfig

from ._commons import (
    commandline_arguments,
    InfoFunc,
    replace_macros,
    replace_passwords,
    SpecialAgentInfoFunctionResult,
)


@dataclass(frozen=True)
class SpecialAgentCommandLine:
    cmdline: str
    stdin: str | None = None


class SpecialAgent:
    def __init__(
        self,
        plugins: Mapping[PluginLocation, SpecialAgentConfig],
        legacy_plugins: Mapping[str, InfoFunc],
        host_name: HostName,
        host_address: HostAddress | None,
        host_config: HostConfig,
        host_attrs: Mapping[str, str],
        http_proxies: Mapping[str, Mapping[str, str]],
        stored_passwords: Mapping[str, str],
        macros: Mapping[str, str] | None,
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self._legacy_plugins = legacy_plugins
        self.host_name = host_name
        self.host_address = host_address
        self.host_config = host_config
        self.host_attrs = host_attrs
        self._http_proxies = http_proxies
        self.stored_passwords = stored_passwords

        # add legacy macros
        self.macros = {**(macros or {}), "<IP>": self.host_address or "", "<HOST>": self.host_name}

    def _make_source_path(self, agent_name: str) -> Path | str:
        file_name = f"agent_{agent_name}"

        libexec_paths = (
            (family_libexec_dir(self._modules[agent_name]),) if agent_name in self._modules else ()
        )
        nagios_paths = (
            cmk.utils.paths.local_agents_dir / "special",
            Path(cmk.utils.paths.agents_dir, "special"),
        )
        return discover_executable(file_name, *libexec_paths, *nagios_paths) or file_name

    def _make_special_agent_cmdline(
        self,
        agent_name: str,
        agent_configuration: SpecialAgentInfoFunctionResult,
    ) -> str:
        path = self._make_source_path(agent_name)
        args = commandline_arguments(self.host_name, None, agent_configuration)
        return replace_macros(f"{path} {args}", self.macros)

    def _iter_legacy_commands(
        self, agent_name: str, info_func: InfoFunc, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        agent_configuration = info_func(params, self.host_name, self.host_address)

        cmdline = self._make_special_agent_cmdline(
            agent_name,
            agent_configuration,
        )
        stdin = getattr(agent_configuration, "stdin", None)

        yield SpecialAgentCommandLine(cmdline, stdin)

    def _iter_commands(
        self, special_agent: SpecialAgentConfig, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        http_proxies = {
            id: HTTPProxy(id, proxy["title"], proxy["proxy_url"])
            for id, proxy in self._http_proxies.items()
        }

        parsed_params = special_agent.parameter_parser(params)
        for command in special_agent.commands_function(
            parsed_params, self.host_config, http_proxies
        ):
            path = self._make_source_path(special_agent.name)
            args = replace_passwords(
                self.host_name, self.stored_passwords, command.command_arguments
            )
            yield SpecialAgentCommandLine(f"{path} {args}", command.stdin)

    def iter_special_agent_commands(
        self, agent_name: str, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        try:
            if (info_func := self._legacy_plugins.get(agent_name)) is not None:
                yield from self._iter_legacy_commands(agent_name, info_func, params)

            if (special_agent := self._plugins.get(agent_name.replace("agent_", ""))) is not None:
                yield from self._iter_commands(special_agent, params)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            config_warnings.warn(
                f"Config creation for special agent {agent_name} failed on {self.host_name}: {e}"
            )
