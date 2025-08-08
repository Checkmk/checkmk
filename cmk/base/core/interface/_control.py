#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All core related things like direct communication with the running core"""

import os
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Literal

import cmk.ccc.debug
import cmk.utils.password_store
import cmk.utils.paths
from cmk import trace
from cmk.base.config import ConfigCache
from cmk.ccc import tty
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.ccc.store import activation_lock
from cmk.checkengine.plugins import AgentBasedPlugins, ConfiguredService, ServiceID
from cmk.utils import config_warnings, ip_lookup
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.labels import Labels
from cmk.utils.log import console
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import ServiceName

from ._base_core import CoreAction, MonitoringCore

tracer = trace.get_tracer()


type _LockingMode = Literal["abort", "wait"] | None


def do_reload(
    config_cache: ConfigCache,
    hosts_config: Hosts,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Mapping[str, str]]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], str],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
    ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
    ip_address_of_mgmt: ip_lookup.IPLookupOptional,
    core: MonitoringCore,
    plugins: AgentBasedPlugins,
    *,
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
    hosts_to_update: set[HostName] | None,
    service_depends_on: Callable[[HostName, ServiceName], Sequence[ServiceName]],
    locking_mode: _LockingMode,
    duplicates: Sequence[HostName],
    bake_on_restart: Callable[[], None],
) -> None:
    do_restart(
        config_cache,
        hosts_config,
        final_service_name_config,
        passive_service_name_config,
        enforced_services_table,
        get_ip_stack_config,
        default_address_family,
        ip_address_of,
        ip_address_of_mgmt,
        core,
        plugins,
        action=CoreAction.RELOAD,
        discovery_rules=discovery_rules,
        hosts_to_update=hosts_to_update,
        service_depends_on=service_depends_on,
        locking_mode=locking_mode,
        duplicates=duplicates,
        bake_on_restart=bake_on_restart,
    )


def do_restart(
    config_cache: ConfigCache,
    host_config: Hosts,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Mapping[str, str]]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], str],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
    ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
    ip_address_of_mgmt: ip_lookup.IPLookupOptional,
    core: MonitoringCore,
    plugins: AgentBasedPlugins,
    *,
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
    action: CoreAction = CoreAction.RESTART,
    hosts_to_update: set[HostName] | None = None,
    service_depends_on: Callable[[HostName, ServiceName], Sequence[ServiceName]],
    locking_mode: _LockingMode,
    duplicates: Sequence[HostName],
    bake_on_restart: Callable[[], None],
) -> None:
    try:
        with activation_lock(
            main_mk_file=cmk.utils.paths.default_config_dir / "main.mk", mode=locking_mode
        ):
            do_create_config(
                core=core,
                config_cache=config_cache,
                hosts_config=host_config,
                final_service_name_config=final_service_name_config,
                passive_service_name_config=passive_service_name_config,
                enforced_services_table=enforced_services_table,
                plugins=plugins,
                discovery_rules=discovery_rules,
                get_ip_stack_config=get_ip_stack_config,
                default_address_family=default_address_family,
                ip_address_of=ip_address_of,
                ip_address_of_mgmt=ip_address_of_mgmt,
                hosts_to_update=hosts_to_update,
                service_depends_on=service_depends_on,
                duplicates=duplicates,
                bake_on_restart=bake_on_restart,
            )
            core.run(action)

    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        raise MKBailOut("An error occurred: %s" % e)


def do_create_config(
    core: MonitoringCore,
    config_cache: ConfigCache,
    hosts_config: Hosts,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: AgentBasedPlugins,
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
    get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
    ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
    ip_address_of_mgmt: ip_lookup.IPLookupOptional,
    hosts_to_update: set[HostName] | None,
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    *,
    duplicates: Collection[HostName],
    bake_on_restart: Callable[[], None],
) -> None:
    """Creating the monitoring core configuration and additional files

    Ensures that everything needed by the monitoring core and it's helper processes is up-to-date
    and available for starting the monitoring.
    """
    with suppress(IOError):
        sys.stdout.write(
            "Generating configuration for core (type %s)...\n" % core.name(),
        )
        sys.stdout.flush()

    try:
        with tracer.span(
            "create_core_config",
            attributes={
                "cmk.core_config.core": core.name(),
                "cmk.core_config.core_config.hosts_to_update": repr(hosts_to_update),
            },
        ):
            _create_core_config(
                core,
                config_cache,
                hosts_config,
                final_service_name_config,
                passive_service_name_config,
                enforced_services_table,
                plugins,
                discovery_rules,
                get_ip_stack_config,
                default_address_family,
                ip_address_of,
                ip_address_of_mgmt,
                hosts_to_update=hosts_to_update,
                service_depends_on=service_depends_on,
                duplicates=duplicates,
            )
    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        raise MKGeneralException("Error creating configuration: %s" % e)

    with tracer.span("bake_on_restart"):
        bake_on_restart()


@contextmanager
def _backup_objects_file(core: MonitoringCore) -> Iterator[None]:
    # TODO: should be a property of MonitoringCore, it seems.
    if core.name() == "nagios":
        objects_file = str(cmk.utils.paths.nagios_objects_file)
    else:
        objects_file = str(cmk.utils.paths.var_dir / "core/config")

    backup_path = None
    if os.path.exists(objects_file):
        backup_path = objects_file + ".save"
        shutil.copy2(objects_file, backup_path)

    try:
        try:
            yield None
        except Exception:
            if backup_path:
                os.rename(backup_path, objects_file)
            raise

        if (  # TODO: should also be a property of the core?
            core.name() == "nagios"
            and cmk.utils.paths.nagios_config_file.exists()
            and not _do_check_nagiosconfig()
        ):
            broken_config_path = cmk.utils.paths.tmp_dir / "check_mk_objects.cfg.broken"
            shutil.move(cmk.utils.paths.nagios_objects_file, broken_config_path)

            if backup_path:
                os.rename(backup_path, objects_file)
            elif os.path.exists(objects_file):
                os.remove(objects_file)

            raise MKGeneralException(
                "Configuration for monitoring core is invalid. Rolling back. "
                'The broken file has been copied to "%s" for analysis.' % broken_config_path
            )
    finally:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)


def _create_core_config(
    core: MonitoringCore,
    config_cache: ConfigCache,
    hosts_config: Hosts,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: AgentBasedPlugins,
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
    get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
    ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
    ip_address_of_mgmt: ip_lookup.IPLookupOptional,
    hosts_to_update: set[HostName] | None,
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    *,
    duplicates: Collection[HostName],
) -> None:
    config_warnings.initialize()

    _verify_non_duplicate_hosts(duplicates)

    # recompute and save passwords, to ensure consistency:
    passwords = config_cache.collect_passwords()
    cmk.utils.password_store.save(passwords, cmk.utils.password_store.pending_password_store_path())

    config_path = VersionedConfigPath.next()
    with config_path.create(is_cmc=core.is_cmc()), _backup_objects_file(core):
        core.create_config(
            config_path,
            config_cache,
            hosts_config,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            plugins,
            discovery_rules,
            get_ip_stack_config,
            default_address_family,
            ip_address_of,
            ip_address_of_mgmt,
            hosts_to_update=hosts_to_update,
            service_depends_on=service_depends_on,
            passwords=passwords,
        )

    cmk.utils.password_store.save(
        passwords, cmk.utils.password_store.core_password_store_path(Path(config_path))
    )


def _verify_non_duplicate_hosts(duplicates: Collection[HostName]) -> None:
    if duplicates:
        config_warnings.warn(
            "The following host names have duplicates: %s. "
            "This might lead to invalid/incomplete monitoring for these hosts."
            % ", ".join(duplicates)
        )


def _print(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


def _do_check_nagiosconfig() -> bool:
    """Execute nagios config verification to ensure the created check_mk_objects.cfg is valid"""
    command = [str(cmk.utils.paths.nagios_binary), "-vp", str(cmk.utils.paths.nagios_config_file)]
    console.verbose(f"Running '{subprocess.list2cmdline(command)}'")
    _print("Validating Nagios configuration...")

    completed_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
        check=False,
    )
    if not completed_process.returncode:
        _print(tty.ok + "\n")
        return True

    _print(f"ERROR:\n{completed_process.stdout}")
    return False
