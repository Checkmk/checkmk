#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Container, Iterable, Iterator, Mapping
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.discover_plugins import discover_families, PluginLocation
from cmk.server_side_calls import internal, v1
from cmk.utils import password_store

from ._commons import ExecutableFinderProtocol, replace_passwords, SecretsConfig
from .config_processing import (
    GlobalProxiesWithLookup,
    OAuth2Connection,
    process_configuration_to_parameters,
)


@dataclass(frozen=True)
class PluginFamily:
    name: str


@dataclass(frozen=True)
class SpecialAgentCommandLine:
    cmdline: str
    stdin: str | None = None


class NotSupportedError(ValueError):
    pass


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
        secrets_config: SecretsConfig,
        finder: ExecutableFinderProtocol,
        for_relay: bool,
        relay_compatible_families: Container[PluginFamily],
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_address = host_address
        self.host_config = host_config
        self.host_attrs = host_attrs
        self._global_proxies_with_lookup = global_proxies_with_lookup
        self._oauth2_connections = oauth2_connections
        self._secrets_config = secrets_config
        self._finder = finder
        self._for_relay = for_relay
        self._relay_compatible_families = relay_compatible_families

    def _make_source_path(self, agent_name: str) -> str:
        return self._finder(f"agent_{agent_name}", self._modules.get(agent_name))

    def _make_family(self, agent_name: str) -> PluginFamily:
        match self._modules[agent_name].split("."):
            case ("cmk" | "cmk_addons", "plugins", family, *_):
                return PluginFamily(family)
            case _:
                raise ValueError(f"Cannot determine family for special agent {agent_name}")

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
                    self._secrets_config,
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
            if self._make_family(name) not in self._relay_compatible_families:
                raise NotSupportedError("This special agent is not supported on relays.")

        yield from self._iter_commands(special_agent, params)


def relay_compatible_plugin_families(local_root: Path) -> Container[PluginFamily]:
    return [
        *(
            PluginFamily(ep.name)
            for ep in entry_points(group="cmk.special_agent_supported_on_relay")
        ),
        *_discover_local_plugin_families(local_root),
    ]


def _discover_local_plugin_families(local_root: Path) -> Iterable[PluginFamily]:
    return [
        PluginFamily(module.split(".")[2])
        for module, (first_path, *_) in discover_families(raise_errors=False).items()
        if first_path.startswith(str(local_root))
    ]
