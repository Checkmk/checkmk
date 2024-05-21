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

import itertools
import os
import py_compile
import re
import socket
import sys
from pathlib import Path

import cmk.utils.config_path
import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.check_utils import section_name_of
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.log import console

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.inventory import InventoryPluginName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.server_side_calls as server_side_calls
import cmk.base.utils
from cmk.base.config import ConfigCache
from cmk.base.ip_lookup import IPStackConfig

from cmk.discover_plugins import PluginLocation

from ._host_check_config import HostCheckConfig

_TEMPLATE_FILE = Path(__file__).parent / "_host_check_template.py"

_INSTANTIATION_PATTERN = re.compile(
    f" = {HostCheckConfig.__name__}\\(.*?\n\\)",
    re.DOTALL,
)


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

    def write(self, config_path: VersionedConfigPath, hostname: HostName, host_check: str) -> None:
        compiled_filename = self.host_check_file_path(config_path, hostname)
        source_filename = self.host_check_source_file_path(config_path, hostname)

        store.makedirs(compiled_filename.parent)

        store.save_text_to_file(source_filename, host_check)

        # compile python (either now or delayed - see host_check code for delay_precompile handling)
        if config.delay_precompile:
            compiled_filename.symlink_to(hostname + ".py")
        else:
            py_compile.compile(
                file=str(source_filename),
                cfile=str(compiled_filename),
                dfile=str(compiled_filename),
                doraise=True,
            )
            os.chmod(compiled_filename, 0o750)  # nosec B103 # BNS:c29b0e

        console.verbose(f" ==> {compiled_filename}.", file=sys.stderr)


def precompile_hostchecks(config_path: VersionedConfigPath, config_cache: ConfigCache) -> None:
    console.verbose("Creating precompiled host check config...")
    hosts_config = config_cache.hosts_config

    config.save_packed_config(config_path, config_cache)

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
            )
            if host_check is None:
                console.verbose("(no Checkmk checks)")
                continue

            host_check_store.write(config_path, hostname, host_check)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error(f"Error precompiling checks for host {hostname}: {e}", file=sys.stderr)
            sys.exit(5)


def dump_precompiled_hostcheck(  # pylint: disable=too-many-branches
    config_cache: ConfigCache,
    config_path: VersionedConfigPath,
    hostname: HostName,
    *,
    verify_site_python: bool = True,
) -> str | None:
    (
        needed_legacy_check_plugin_names,
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    ) = _get_needed_plugin_names(config_cache, hostname)

    if hostname in config_cache.hosts_config.clusters:
        assert config_cache.nodes(hostname)
        for node in config_cache.nodes(hostname):
            (
                node_needed_legacy_check_plugin_names,
                node_needed_agent_based_check_plugin_names,
                node_needed_agent_based_inventory_plugin_names,
            ) = _get_needed_plugin_names(config_cache, node)
            needed_legacy_check_plugin_names.update(node_needed_legacy_check_plugin_names)
            needed_agent_based_check_plugin_names.update(node_needed_agent_based_check_plugin_names)
            needed_agent_based_inventory_plugin_names.update(
                node_needed_agent_based_inventory_plugin_names
            )

    needed_legacy_check_plugin_names.update(
        _get_required_legacy_check_sections(
            needed_agent_based_check_plugin_names,
            needed_agent_based_inventory_plugin_names,
        )
    )

    if not any(
        (
            needed_legacy_check_plugin_names,
            needed_agent_based_check_plugin_names,
            needed_agent_based_inventory_plugin_names,
        )
    ):
        return None

    locations = _get_needed_agent_based_locations(
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    )

    checks_to_load = sorted(_get_legacy_check_file_names_to_load(needed_legacy_check_plugin_names))

    for check_plugin_name in sorted(needed_legacy_check_plugin_names):
        console.verbose_no_lf(f" {tty.green}{check_plugin_name}{tty.normal}", file=sys.stderr)

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
                needed_ipaddresses[node] = config.lookup_ip_address(
                    config_cache, node, family=socket.AddressFamily.AF_INET
                )

            if IPStackConfig.IPv6 in node_ip_stack_config:
                needed_ipv6addresses[node] = config.lookup_ip_address(
                    config_cache, node, family=socket.AddressFamily.AF_INET6
                )

        try:
            if IPStackConfig.IPv4 in ip_stack_config:
                needed_ipaddresses[hostname] = config.lookup_ip_address(
                    config_cache, hostname, family=socket.AddressFamily.AF_INET
                )
        except Exception:
            pass

        try:
            if IPStackConfig.IPv6 in ip_stack_config:
                needed_ipv6addresses[hostname] = config.lookup_ip_address(
                    config_cache, hostname, family=socket.AddressFamily.AF_INET6
                )
        except Exception:
            pass
    else:
        if IPStackConfig.IPv4 in ip_stack_config:
            needed_ipaddresses[hostname] = config.lookup_ip_address(
                config_cache, hostname, family=socket.AddressFamily.AF_INET
            )

        if IPStackConfig.IPv6 in ip_stack_config:
            needed_ipv6addresses[hostname] = config.lookup_ip_address(
                config_cache, hostname, family=socket.AddressFamily.AF_INET6
            )

    # assign the values here, just to let the type checker do its job
    host_check_config = HostCheckConfig(
        delay_precompile=bool(config.delay_precompile),
        src=str(HostCheckStore.host_check_source_file_path(config_path, hostname)),
        dst=str(HostCheckStore.host_check_file_path(config_path, hostname)),
        verify_site_python=verify_site_python,
        locations=locations,
        checks_to_load=checks_to_load,
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
    config_cache: ConfigCache, host_name: HostName
) -> tuple[set[str], set[CheckPluginName], set[InventoryPluginName]]:
    ssc_api_special_agents = {p.name for p in server_side_calls.load_special_agents()[1].values()}
    needed_legacy_check_plugin_names = {
        f"agent_{name}"
        for name, _p in config_cache.special_agents(host_name)
        if name not in ssc_api_special_agents
    }

    # Collect the needed check plug-in names using the host check table.
    # Even auto-migrated checks must be on the list of needed *agent based* plugins:
    # In those cases, the module attribute will be `None`, so nothing will
    # be imported; BUT: we need it in the list, because it must be considered
    # when determining the needed *section* plugins.
    # This matters in cases where the section is migrated, but the check
    # plugins are not.
    needed_agent_based_check_plugin_names = config_cache.check_table(
        host_name,
        filter_mode=config.FilterMode.INCLUDE_CLUSTERED,
        skip_ignored=False,
    ).needed_check_names()

    legacy_names = (_resolve_legacy_plugin_name(pn) for pn in needed_agent_based_check_plugin_names)
    needed_legacy_check_plugin_names.update(ln for ln in legacy_names if ln is not None)

    # Inventory plugins get passed parsed data these days.
    # Load the required sections, or inventory plugins will crash upon unparsed data.
    needed_agent_based_inventory_plugin_names: set[InventoryPluginName] = set()
    if config_cache.hwsw_inventory_parameters(host_name).status_data_inventory:
        for inventory_plugin in agent_based_register.iter_all_inventory_plugins():
            needed_agent_based_inventory_plugin_names.add(inventory_plugin.name)
            for parsed_section_name in inventory_plugin.sections:
                # check if we must add the legacy check plugin:
                legacy_check_name = config.legacy_check_plugin_names.get(
                    CheckPluginName(str(parsed_section_name))
                )
                if legacy_check_name is not None:
                    needed_legacy_check_plugin_names.add(legacy_check_name)

    return (
        needed_legacy_check_plugin_names,
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    )


def _resolve_legacy_plugin_name(check_plugin_name: CheckPluginName) -> str | None:
    legacy_name = config.legacy_check_plugin_names.get(check_plugin_name)
    if legacy_name:
        return legacy_name

    if not check_plugin_name.is_management_name():
        return None

    # See if me must include a legacy plug-in from which we derived the given one:
    # A management plug-in *could have been* created on the fly, from a 'regular' legacy
    # check plugin. In this case, we must load that.
    plugin = agent_based_register.get_check_plugin(check_plugin_name)
    if not plugin or plugin.location is not None:
        # it does *not* result from a legacy plugin, if module is not None
        return None

    # just try to get the legacy name of the 'regular' plugin:
    return config.legacy_check_plugin_names.get(check_plugin_name.create_basic_name())


def _get_legacy_check_file_names_to_load(
    needed_check_plugin_names: set[str],
) -> set[str]:
    # check info table
    # We need to include all those plugins that are referenced in the hosts
    # check table.
    return {
        filename
        for check_plugin_name in needed_check_plugin_names
        for filename in _find_check_plugins(check_plugin_name)
    }


def _find_check_plugins(checktype: str) -> set[str]:
    """Find files to be included in precompile host check for a certain
    check (for example df or mem.used).

    In case of checks with a period (subchecks) we might have to include both "mem" and "mem.used".
    The subcheck *may* be implemented in a separate file."""
    return {
        filename
        for candidate in (section_name_of(checktype), checktype)
        # in case there is no "main check" anymore, the lookup fails -> skip.
        if (filename := config.legacy_check_plugin_files.get(candidate)) is not None
    }


def _get_needed_agent_based_locations(
    check_plugin_names: set[CheckPluginName],
    inventory_plugin_names: set[InventoryPluginName],
) -> list[PluginLocation]:
    modules = {
        plugin.location
        for plugin in [agent_based_register.get_check_plugin(p) for p in check_plugin_names]
        if plugin is not None and plugin.location is not None
    }
    modules.update(
        plugin.location
        for plugin in [agent_based_register.get_inventory_plugin(p) for p in inventory_plugin_names]
        if plugin is not None and plugin.location is not None
    )
    modules.update(
        section.location
        for section in agent_based_register.get_relevant_raw_sections(
            check_plugin_names=check_plugin_names,
            inventory_plugin_names=inventory_plugin_names,
        ).values()
        if section.location is not None
    )

    return sorted(modules, key=lambda l: (l.module, l.name or ""))


def _get_required_legacy_check_sections(
    check_plugin_names: set[CheckPluginName],
    inventory_plugin_names: set[InventoryPluginName],
) -> set[str]:
    """
    new style plug-in may have a dependency to a legacy check
    """
    required_legacy_check_sections = set()
    for section in agent_based_register.get_relevant_raw_sections(
        check_plugin_names=check_plugin_names,
        inventory_plugin_names=inventory_plugin_names,
    ).values():
        if section.location is None:
            required_legacy_check_sections.add(str(section.name))
    return required_legacy_check_sections
