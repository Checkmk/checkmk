#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Precompiling creates on dedicated Python file per host, which just
contains that code and information that is needed for executing all
checks of that host. Also static data that cannot change during the
normal monitoring process is being precomputed and hard coded. This
all saves substantial CPU resources as opposed to running Checkmk
in adhoc mode (about 75%).
"""

import enum
import itertools
import os
import py_compile
import re
import socket
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import assert_never

import cmk.ccc.debug
from cmk.ccc import store, tty
from cmk.ccc.exceptions import MKIPAddressLookupError
from cmk.ccc.hostaddress import HostAddress, HostName

import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils.ip_lookup import IPLookup, IPStackConfig
from cmk.utils.log import console
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

import cmk.checkengine.plugin_backend as agent_based_register
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPlugin,
    InventoryPlugin,
    LegacyPluginLocation,
    SectionPlugin,
)

from cmk.base.config import ConfigCache, FilterMode, save_packed_config
from cmk.base.configlib.servicename import PassiveServiceNameConfig

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls_backend import load_special_agents

from ._host_check_config import HostCheckConfig

_TEMPLATE_FILE = Path(__file__).parent / "_host_check_template.py"

_INSTANTIATION_PATTERN = re.compile(
    f" = {HostCheckConfig.__name__}\\(.*?\n\\)",
    re.DOTALL,
)


class PrecompileMode(enum.Enum):
    DELAYED = enum.auto()
    INSTANT = enum.auto()


class HostCheckStore:
    """Caring about persistence of the precompiled host check files"""

    @staticmethod
    def host_check_file_path(config_path: Path, hostname: HostName) -> Path:
        return config_path / "host_checks" / hostname

    @staticmethod
    def host_check_source_file_path(config_path: Path, hostname: HostName) -> Path:
        # TODO: Use append_suffix(".py") once we are on Python 3.10
        path = HostCheckStore.host_check_file_path(config_path, hostname)
        return path.with_suffix(path.suffix + ".py")

    def write(
        self,
        config_path: Path,
        hostname: HostName,
        host_check: str,
        *,
        precompile_mode: PrecompileMode,
    ) -> None:
        compiled_filename = self.host_check_file_path(config_path, hostname)
        source_filename = self.host_check_source_file_path(config_path, hostname)

        compiled_filename.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_text_to_file(source_filename, host_check)

        # compile python (either now or delayed - see host_check code for delay_precompile handling)
        match precompile_mode:
            case PrecompileMode.DELAYED:
                compiled_filename.symlink_to(hostname + ".py")
            case PrecompileMode.INSTANT:
                py_compile.compile(
                    file=str(source_filename),
                    cfile=str(compiled_filename),
                    dfile=str(compiled_filename),
                    doraise=True,
                )
                os.chmod(compiled_filename, 0o750)  # nosec B103 # BNS:c29b0e
            case other:
                assert_never(other)

        console.verbose(f" ==> {compiled_filename}.", file=sys.stderr)


def precompile_hostchecks(
    config_path: Path,
    config_cache: ConfigCache,
    service_name_config: PassiveServiceNameConfig,
    plugins: AgentBasedPlugins,
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
    get_ip_stack_config: Callable[[HostName], IPStackConfig],
    ip_address_of: IPLookup,
    *,
    precompile_mode: PrecompileMode,
) -> None:
    console.verbose("Creating precompiled host check config...")
    hosts_config = config_cache.hosts_config

    save_packed_config(config_path, config_cache, discovery_rules)

    console.verbose("Precompiling host checks...")

    host_check_store = HostCheckStore()
    for hostname in {
        # Inconsistent with `create_config` above.
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    }:
        try:
            console.verbose_no_lf(
                f"{tty.bold}{tty.blue}{hostname:<16}{tty.normal}:", file=sys.stderr
            )
            host_check = dump_precompiled_hostcheck(
                config_cache,
                service_name_config,
                config_path,
                hostname,
                get_ip_stack_config,
                plugins,
                ip_address_of=ip_address_of,
                precompile_mode=precompile_mode,
            )

            host_check_store.write(
                config_path, hostname, host_check, precompile_mode=precompile_mode
            )
        except MKIPAddressLookupError as e:
            console.error(f"Error precompiling checks for host {hostname}: {e}", file=sys.stderr)
        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            console.error(f"Error precompiling checks for host {hostname}: {e}", file=sys.stderr)
            sys.exit(5)


def dump_precompiled_hostcheck(
    config_cache: ConfigCache,
    service_name_config: PassiveServiceNameConfig,
    config_path: Path,
    hostname: HostName,
    get_ip_stack_config: Callable[[HostName], IPStackConfig],
    plugins: AgentBasedPlugins,
    *,
    ip_address_of: IPLookup,
    verify_site_python: bool = True,
    precompile_mode: PrecompileMode,
) -> str:
    locations, legacy_checks_to_load = _make_needed_plugins_locations(
        config_cache, service_name_config, hostname, plugins
    )
    ip_stack_config = get_ip_stack_config(hostname)

    # IP addresses
    needed_ipaddresses: dict[HostName, HostAddress] = {}
    needed_ipv6addresses: dict[HostName, HostAddress] = {}
    if hostname in config_cache.hosts_config.clusters:
        assert config_cache.nodes(hostname)
        for node in config_cache.nodes(hostname):
            node_ip_stack_config = get_ip_stack_config(node)
            if IPStackConfig.IPv4 in node_ip_stack_config:
                needed_ipaddresses[node] = ip_address_of(node, socket.AddressFamily.AF_INET)

            if IPStackConfig.IPv6 in node_ip_stack_config:
                needed_ipv6addresses[node] = ip_address_of(node, socket.AddressFamily.AF_INET6)

        try:
            if IPStackConfig.IPv4 in ip_stack_config:
                needed_ipaddresses[hostname] = ip_address_of(hostname, socket.AddressFamily.AF_INET)
        except Exception:
            pass

        try:
            if IPStackConfig.IPv6 in ip_stack_config:
                needed_ipv6addresses[hostname] = ip_address_of(
                    hostname, socket.AddressFamily.AF_INET6
                )
        except Exception:
            pass
    else:
        if IPStackConfig.IPv4 in ip_stack_config:
            needed_ipaddresses[hostname] = ip_address_of(hostname, socket.AddressFamily.AF_INET)

        if IPStackConfig.IPv6 in ip_stack_config:
            needed_ipv6addresses[hostname] = ip_address_of(hostname, socket.AddressFamily.AF_INET6)

    # assign the values here, just to let the type checker do its job
    host_check_config = HostCheckConfig(
        delay_precompile=precompile_mode
        is PrecompileMode.DELAYED,  # propagation of enum would break b/c of the repr() below :-(
        src=str(HostCheckStore.host_check_source_file_path(config_path, hostname)),
        dst=str(HostCheckStore.host_check_file_path(config_path, hostname)),
        verify_site_python=verify_site_python,
        locations=locations,
        checks_to_load=legacy_checks_to_load,
        ipaddresses=needed_ipaddresses,
        ipv6addresses=needed_ipv6addresses,
        hostname=hostname,
    )

    template = _TEMPLATE_FILE.read_text()
    if (m_placeholder := _INSTANTIATION_PATTERN.search(template)) is None:
        raise ValueError(f"broken template at: {_TEMPLATE_FILE})")

    return template.replace(
        m_placeholder.group(0),
        f" = {host_check_config!r}",
    )


def _make_needed_plugins_locations(
    config_cache: ConfigCache,
    service_name_config: PassiveServiceNameConfig,
    hostname: HostName,
    plugins: AgentBasedPlugins,
) -> tuple[  # we need `list` for the weird template replacement technique
    list[PluginLocation],
    list[str],  # TODO: change this to `LegacyPluginLocation` once the special agents are migrated
]:
    needed_agent_based_plugins = _get_needed_plugins(
        config_cache, service_name_config, hostname, plugins
    )

    if hostname in config_cache.hosts_config.clusters:
        assert config_cache.nodes(hostname)
        for node in config_cache.nodes(hostname):
            # we're deduplicating later.
            needed_agent_based_plugins.extend(
                _get_needed_plugins(config_cache, service_name_config, node, plugins)
            )

    needed_legacy_special_agents = _get_needed_legacy_special_agents(config_cache, hostname)

    needed_agent_based_sections = agent_based_register.filter_relevant_raw_sections(
        consumers=needed_agent_based_plugins,
        sections=itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
    ).values()

    return (
        _get_needed_agent_based_locations(
            itertools.chain(needed_agent_based_sections, needed_agent_based_plugins)
        ),
        _get_needed_legacy_check_files(
            itertools.chain(needed_agent_based_sections, needed_agent_based_plugins),
            needed_legacy_special_agents,
        ),
    )


def _get_needed_plugins(
    config_cache: ConfigCache,
    service_name_config: PassiveServiceNameConfig,
    host_name: HostName,
    agent_based_plugins: AgentBasedPlugins,
) -> list[CheckPlugin | InventoryPlugin]:
    # Collect the needed check plug-in names using the host check table.
    # Even auto-migrated checks must be on the list of needed *agent based* plugins:
    # In those cases, the module attribute will be `None`, so nothing will
    # be imported; BUT: we need it in the list, because it must be considered
    # when determining the needed *section* plugins.
    # This matters in cases where the section is migrated, but the check
    # plugins are not.
    return [
        *(
            plugin
            for name in config_cache.check_table(
                host_name,
                agent_based_plugins.check_plugins,
                config_cache.make_service_configurer(
                    agent_based_plugins.check_plugins, service_name_config
                ),
                service_name_config,
                filter_mode=FilterMode.INCLUDE_CLUSTERED,
                skip_ignored=False,
            ).needed_check_names()
            if (plugin := agent_based_plugins.check_plugins.get(name))
        ),
        *(
            agent_based_plugins.inventory_plugins.values()
            if config_cache.hwsw_inventory_parameters(host_name).status_data_inventory
            else ()
        ),
    ]


def _get_needed_legacy_special_agents(config_cache: ConfigCache, host_name: HostName) -> set[str]:
    ssc_api_special_agents = {
        p.name for p in load_special_agents(raise_errors=cmk.ccc.debug.enabled()).values()
    }
    return {
        f"agent_{name}"
        for name, _p in config_cache.special_agents(host_name)
        if name not in ssc_api_special_agents
    }


def _get_needed_legacy_check_files(
    # Note: we don't *have* any InventoryPlugins that match the condition below, but
    # it's easier to type it like this.
    plugins: Iterable[SectionPlugin | CheckPlugin | InventoryPlugin],
    legacy_special_agent_names: set[str],
) -> list[str]:
    return sorted(
        {p.location.file_name for p in plugins if isinstance(p.location, LegacyPluginLocation)}
        | {
            f"{os.path.join(base, name)}.py"
            for base in (cmk.utils.paths.local_checks_dir, cmk.utils.paths.checks_dir)
            for name in legacy_special_agent_names
        }
    )


def _get_needed_agent_based_locations(
    plugins: Iterable[SectionPlugin | CheckPlugin | InventoryPlugin],
) -> list[PluginLocation]:
    modules = {plugin.location for plugin in plugins if isinstance(plugin.location, PluginLocation)}
    return sorted(modules, key=lambda l: (l.module, l.name or ""))
