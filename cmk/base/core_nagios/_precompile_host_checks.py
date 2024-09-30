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
from collections.abc import Iterable
from pathlib import Path
from typing import assert_never

import cmk.ccc.debug
from cmk.ccc import store

import cmk.utils.config_path
import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils import tty
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.log import console

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.inventory import InventoryPluginName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.utils
from cmk.base import server_side_calls
from cmk.base.api.agent_based.plugin_classes import LegacyPluginLocation, SectionPlugin
from cmk.base.config import ConfigCache, FilterMode, lookup_ip_address, save_packed_config

from cmk.discover_plugins import PluginLocation

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
    def host_check_file_path(config_path: VersionedConfigPath, hostname: HostName) -> Path:
        return Path(config_path) / "host_checks" / hostname

    @staticmethod
    def host_check_source_file_path(config_path: VersionedConfigPath, hostname: HostName) -> Path:
        # TODO: Use append_suffix(".py") once we are on Python 3.10
        path = HostCheckStore.host_check_file_path(config_path, hostname)
        return path.with_suffix(path.suffix + ".py")

    def write(
        self,
        config_path: VersionedConfigPath,
        hostname: HostName,
        host_check: str,
        *,
        precompile_mode: PrecompileMode,
    ) -> None:
        compiled_filename = self.host_check_file_path(config_path, hostname)
        source_filename = self.host_check_source_file_path(config_path, hostname)

        store.makedirs(compiled_filename.parent)

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
    config_path: VersionedConfigPath,
    config_cache: ConfigCache,
    *,
    precompile_mode: PrecompileMode,
) -> None:
    console.verbose("Creating precompiled host check config...")
    hosts_config = config_cache.hosts_config

    save_packed_config(config_path, config_cache)

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
                config_path,
                hostname,
                precompile_mode=precompile_mode,
            )
            if host_check is None:
                console.verbose("(no Checkmk checks)")
                continue

            host_check_store.write(
                config_path, hostname, host_check, precompile_mode=precompile_mode
            )
        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            console.error(f"Error precompiling checks for host {hostname}: {e}", file=sys.stderr)
            sys.exit(5)


def dump_precompiled_hostcheck(  # pylint: disable=too-many-branches
    config_cache: ConfigCache,
    config_path: VersionedConfigPath,
    hostname: HostName,
    *,
    verify_site_python: bool = True,
    precompile_mode: PrecompileMode,
) -> str | None:
    (
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    ) = _get_needed_plugin_names(config_cache, hostname)

    if hostname in config_cache.hosts_config.clusters:
        assert config_cache.nodes(hostname)
        for node in config_cache.nodes(hostname):
            (
                node_needed_agent_based_check_plugin_names,
                node_needed_agent_based_inventory_plugin_names,
            ) = _get_needed_plugin_names(config_cache, node)
            needed_agent_based_check_plugin_names.update(node_needed_agent_based_check_plugin_names)
            needed_agent_based_inventory_plugin_names.update(
                node_needed_agent_based_inventory_plugin_names
            )

    needed_legacy_special_agents = _get_needed_legacy_special_agents(config_cache, hostname)

    if not any(
        (
            needed_legacy_special_agents,
            needed_agent_based_check_plugin_names,
            needed_agent_based_inventory_plugin_names,
        )
    ):
        return None

    needed_agent_based_section_plugin_names = agent_based_register.get_relevant_raw_sections(
        check_plugin_names=needed_agent_based_check_plugin_names,
        inventory_plugin_names=needed_agent_based_inventory_plugin_names,
    )

    locations = _get_needed_agent_based_locations(
        needed_agent_based_section_plugin_names.values(),
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    )

    legacy_checks_to_load = sorted(
        _get_needed_legacy_check_files(
            needed_agent_based_section_plugin_names.values(),
            needed_agent_based_check_plugin_names,
            needed_legacy_special_agents,
        )
    )

    # IP addresses
    # FIXME:
    # What we construct here does not match what we need to assign it to `config.ipaddresses` and
    # `config.ipv6addresses` later.
    # But maybe it is in fact not a problem, because `config.lookup_ip_address` happens to never
    # return `None` the way we call it here.
    ip_stack_config = ConfigCache.ip_stack_config(hostname)
    needed_ipaddresses: dict[HostName, HostAddress | None] = {}
    needed_ipv6addresses: dict[HostName, HostAddress | None] = {}
    if hostname in config_cache.hosts_config.clusters:
        assert config_cache.nodes(hostname)
        for node in config_cache.nodes(hostname):
            node_ip_stack_config = ConfigCache.ip_stack_config(node)
            if IPStackConfig.IPv4 in node_ip_stack_config:
                needed_ipaddresses[node] = lookup_ip_address(
                    config_cache, node, family=socket.AddressFamily.AF_INET
                )

            if IPStackConfig.IPv6 in node_ip_stack_config:
                needed_ipv6addresses[node] = lookup_ip_address(
                    config_cache, node, family=socket.AddressFamily.AF_INET6
                )

        try:
            if IPStackConfig.IPv4 in ip_stack_config:
                needed_ipaddresses[hostname] = lookup_ip_address(
                    config_cache, hostname, family=socket.AddressFamily.AF_INET
                )
        except Exception:
            pass

        try:
            if IPStackConfig.IPv6 in ip_stack_config:
                needed_ipv6addresses[hostname] = lookup_ip_address(
                    config_cache, hostname, family=socket.AddressFamily.AF_INET6
                )
        except Exception:
            pass
    else:
        if IPStackConfig.IPv4 in ip_stack_config:
            needed_ipaddresses[hostname] = lookup_ip_address(
                config_cache, hostname, family=socket.AddressFamily.AF_INET
            )

        if IPStackConfig.IPv6 in ip_stack_config:
            needed_ipv6addresses[hostname] = lookup_ip_address(
                config_cache, hostname, family=socket.AddressFamily.AF_INET6
            )

    # assign the values here, just to let the type checker do its job
    host_check_config = HostCheckConfig(
        delay_precompile=precompile_mode
        is PrecompileMode.DELAYED,  # propagation of enum would break b/c of the repr() below :-(
        src=str(HostCheckStore.host_check_source_file_path(config_path, hostname)),
        dst=str(HostCheckStore.host_check_file_path(config_path, hostname)),
        verify_site_python=verify_site_python,
        locations=locations,
        checks_to_load=legacy_checks_to_load,
        ipaddresses=needed_ipaddresses,  # type: ignore[arg-type]  # see FIXME above.
        ipv6addresses=needed_ipv6addresses,  # type: ignore[arg-type]  # see FIXME above.
        hostname=hostname,
    )

    template = _TEMPLATE_FILE.read_text()
    if (m_placeholder := _INSTANTIATION_PATTERN.search(template)) is None:
        raise ValueError(f"broken template at: {_TEMPLATE_FILE})")

    return template.replace(
        m_placeholder.group(0),
        f" = {host_check_config!r}",
    )


def _get_needed_plugin_names(
    config_cache: ConfigCache,
    host_name: HostName,
) -> tuple[set[CheckPluginName], set[InventoryPluginName]]:
    # Collect the needed check plug-in names using the host check table.
    # Even auto-migrated checks must be on the list of needed *agent based* plugins:
    # In those cases, the module attribute will be `None`, so nothing will
    # be imported; BUT: we need it in the list, because it must be considered
    # when determining the needed *section* plugins.
    # This matters in cases where the section is migrated, but the check
    # plugins are not.
    return (
        config_cache.check_table(
            host_name,
            filter_mode=FilterMode.INCLUDE_CLUSTERED,
            skip_ignored=False,
        ).needed_check_names(),
        {
            inventory_plugin.name
            for inventory_plugin in agent_based_register.iter_all_inventory_plugins()
        }
        if config_cache.hwsw_inventory_parameters(host_name).status_data_inventory
        else set(),
    )


def _get_needed_legacy_special_agents(config_cache: ConfigCache, host_name: HostName) -> set[str]:
    ssc_api_special_agents = {
        p.name
        for p in server_side_calls.load_special_agents(
            raise_errors=cmk.ccc.debug.enabled()
        ).values()
    }
    return {
        f"agent_{name}"
        for name, _p in config_cache.special_agents(host_name)
        if name not in ssc_api_special_agents
    }


def _get_needed_legacy_check_files(
    section_plugins: Iterable[SectionPlugin],
    check_plugin_names: Iterable[CheckPluginName],
    legacy_special_agent_names: set[str],
) -> set[str]:
    return (
        {
            section.location.file_name
            for section in section_plugins
            if isinstance(section.location, LegacyPluginLocation)
        }
        | {
            check_plugin.location.file_name
            for check_plugin_name in check_plugin_names
            if (check_plugin := agent_based_register.get_check_plugin(check_plugin_name))
            is not None
            and isinstance(check_plugin.location, LegacyPluginLocation)
        }
        | {
            f"{os.path.join(base, name)}.py"
            for base in (cmk.utils.paths.local_checks_dir, cmk.utils.paths.checks_dir)
            for name in legacy_special_agent_names
        }
    )


def _get_needed_agent_based_locations(
    section_plugins: Iterable[SectionPlugin],
    check_plugin_names: Iterable[CheckPluginName],
    inventory_plugin_names: Iterable[InventoryPluginName],
) -> list[PluginLocation]:
    modules = {
        plugin.location
        for plugin in [agent_based_register.get_check_plugin(p) for p in check_plugin_names]
        if plugin is not None and isinstance(plugin.location, PluginLocation)
    }
    modules.update(
        plugin.location
        for plugin in [agent_based_register.get_inventory_plugin(p) for p in inventory_plugin_names]
        if plugin is not None and isinstance(plugin.location, PluginLocation)
    )
    modules.update(
        section.location
        for section in section_plugins
        if isinstance(section.location, PluginLocation)
    )

    return sorted(modules, key=lambda l: (l.module, l.name or ""))
