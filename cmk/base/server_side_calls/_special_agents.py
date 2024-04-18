#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.password_store as password_store
import cmk.utils.paths
from cmk.utils.hostaddress import HostAddress, HostName

from cmk.discover_plugins import discover_executable, family_libexec_dir, PluginLocation
from cmk.server_side_calls.v1 import HostConfig, SpecialAgentConfig
from cmk.server_side_calls_backend.config_processing import (
    process_configuration_to_parameters,
    ProxyConfig,
)

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


def _ensure_mapping_str_object(value: object) -> Mapping[str, object]:
    # for the new API, we can be sure that there are only Mappings.
    if not isinstance(value, dict):
        raise TypeError(value)
    return value


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
        password_store_file: Path,
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
        self.password_store_file = password_store_file

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
        args = commandline_arguments(
            self.host_name,
            None,
            agent_configuration,
            self.stored_passwords,
            self.password_store_file,
        )
        return replace_macros(f"{path} {args}", self.host_config.macros)

    def _iter_legacy_commands(
        self, agent_name: str, info_func: InfoFunc, params: object
    ) -> Iterator[SpecialAgentCommandLine]:
        agent_configuration = info_func(params, self.host_name, self.host_address)

        cmdline = self._make_special_agent_cmdline(
            agent_name,
            agent_configuration,
        )
        stdin = getattr(agent_configuration, "stdin", None)

        yield SpecialAgentCommandLine(cmdline, stdin)

    def _iter_commands(
        self, special_agent: SpecialAgentConfig, conf_dict: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:

        proxy_config = ProxyConfig(self.host_name, self._http_proxies)
        processed = process_configuration_to_parameters(conf_dict, proxy_config)

        for command in special_agent(processed.value, self.host_config):
            args = replace_passwords(
                self.host_name,
                command.command_arguments,
                self.stored_passwords,
                self.password_store_file,
                processed.surrogates,
                apply_password_store_hack=password_store.hack.HACK_AGENTS.get(
                    special_agent.name, False
                ),
            )
            # there's a test that currently prevents us from moving this out of the loop
            path = self._make_source_path(special_agent.name)
            yield SpecialAgentCommandLine(f"{path} {args}", command.stdin)

    def iter_special_agent_commands(
        self, agent_name: str, params: Mapping[str, object] | object
    ) -> Iterator[SpecialAgentCommandLine]:
        try:
            if (info_func := self._legacy_plugins.get(agent_name)) is not None:
                yield from self._iter_legacy_commands(agent_name, info_func, params)

            if (special_agent := self._plugins.get(agent_name.replace("agent_", ""))) is not None:
                params = _ensure_mapping_str_object(params)
                yield from self._iter_commands(special_agent, params)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            config_warnings.warn(
                f"Config creation for special agent {agent_name} failed on {self.host_name}: {e}"
            )
