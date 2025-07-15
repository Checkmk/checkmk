#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils import password_store

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import HostConfig, SpecialAgentConfig

from ._commons import ExecutableFinderProtocol, replace_passwords
from .config_processing import (
    process_configuration_to_parameters,
    ProxyConfig,
)


@dataclass(frozen=True)
class SpecialAgentCommandLine:
    cmdline: str
    stdin: str | None = None


class SpecialAgent:
    def __init__(
        self,
        plugins: Mapping[PluginLocation, SpecialAgentConfig],
        host_name: HostName,
        host_address: HostAddress | None,
        host_config: HostConfig,
        host_attrs: Mapping[str, str],
        http_proxies: Mapping[str, Mapping[str, str]],
        stored_passwords: Mapping[str, str],
        password_store_file: Path,
        finder: ExecutableFinderProtocol,
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_address = host_address
        self.host_config = host_config
        self.host_attrs = host_attrs
        self._http_proxies = http_proxies
        self.stored_passwords = stored_passwords
        self.password_store_file = password_store_file
        self._finder = finder

    def _make_source_path(self, agent_name: str) -> str:
        return self._finder(f"agent_{agent_name}", self._modules.get(agent_name))

    def _iter_commands(
        self, special_agent: SpecialAgentConfig, conf_dict: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        proxy_config = ProxyConfig(self.host_name, self._http_proxies)
        processed = process_configuration_to_parameters(conf_dict, proxy_config)

        for command in special_agent(processed.value, self.host_config):
            args = " ".join(
                replace_passwords(
                    self.host_name,
                    command.command_arguments,
                    self.stored_passwords,
                    self.password_store_file,
                    processed.surrogates,
                    apply_password_store_hack=password_store.hack.HACK_AGENTS.get(
                        special_agent.name, False
                    ),
                )
            )
            # there's a test that currently prevents us from moving this out of the loop
            path = self._make_source_path(special_agent.name)
            yield SpecialAgentCommandLine(f"{path} {args}", command.stdin)

    def iter_special_agent_commands(
        self, agent_name: str, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        if (special_agent := self._plugins.get(agent_name.removeprefix("agent_"))) is not None:
            yield from self._iter_commands(special_agent, params)
