#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.discover_plugins import PluginLocation
from cmk.password_store.v1_unstable import Secret as StoreSecret
from cmk.server_side_calls import internal, v1
from cmk.utils import config_warnings, password_store

from ._commons import ExecutableFinderProtocol, replace_passwords
from .config_processing import (
    GlobalProxiesWithLookup,
    OAuth2Connection,
    process_configuration_to_parameters,
)


@dataclass(frozen=True)
class SpecialAgentCommandLine:
    cmdline: str
    stdin: str | None = None


class SpecialAgent:
    def __init__(
        self,
        plugins: Mapping[PluginLocation, v1.SpecialAgentConfig | internal.SpecialAgentConfig],
        host_name: HostName,
        host_address: HostAddress | None,
        host_config: v1.HostConfig,
        host_attrs: Mapping[str, str],
        global_proxies_with_lookup: GlobalProxiesWithLookup,
        oauth2_connections: Mapping[str, OAuth2Connection],
        stored_passwords: Mapping[str, StoreSecret[str]],
        password_store_file: Path,
        finder: ExecutableFinderProtocol,
        for_relay: bool,
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_address = host_address
        self.host_config = host_config
        self.host_attrs = host_attrs
        self._global_proxies_with_lookup = global_proxies_with_lookup
        self._oauth2_connections = oauth2_connections
        self.stored_passwords = stored_passwords
        self.password_store_file = password_store_file
        self._finder = finder
        self._for_relay = for_relay

    def _make_source_path(self, agent_name: str) -> str:
        return self._finder(f"agent_{agent_name}", self._modules.get(agent_name))

    def _iter_commands(
        self,
        special_agent: v1.SpecialAgentConfig | internal.SpecialAgentConfig,
        conf_dict: Mapping[str, object],
    ) -> Iterator[SpecialAgentCommandLine]:
        processed = process_configuration_to_parameters(
            conf_dict,
            self._global_proxies_with_lookup,
            self._oauth2_connections,
            usage_hint=f"special agent: {special_agent.name}",
            is_internal=isinstance(special_agent, internal.SpecialAgentConfig),
        )

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
        name = agent_name.removeprefix("agent_")
        if (special_agent := self._plugins.get(name)) is None:
            return

        if self._for_relay:
            if name not in _relay_compatible_plugin_families():
                msg = f"Config creation for special agent {agent_name} failed on {self.host_name}: Agent is not supported on relays."
                config_warnings.warn(msg)
                # Continue anyway. The datasource will fail on the relay side, and the Checkmk service will go CRIT.

        yield from self._iter_commands(special_agent, params)


def _relay_compatible_plugin_families() -> list[str]:
    return [ep.name for ep in entry_points(group="cmk.special_agent_supported_on_relay")]
