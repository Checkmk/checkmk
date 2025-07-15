#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All core related things like direct communication with the running core"""

import enum
import os
import socket
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from typing import Literal

import cmk.ccc.debug
from cmk.ccc import store, tty
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.ccc.hostaddress import HostName, Hosts

import cmk.utils.paths
from cmk.utils import ip_lookup
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import ServiceName

from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base import core_config
from cmk.base.config import ConfigCache
from cmk.base.configlib.servicename import PassiveServiceNameConfig
from cmk.base.core_config import MonitoringCore

from cmk import trace

tracer = trace.get_tracer()

# .
#   .--Control-------------------------------------------------------------.
#   |                   ____            _             _                    |
#   |                  / ___|___  _ __ | |_ _ __ ___ | |                   |
#   |                 | |   / _ \| '_ \| __| '__/ _ \| |                   |
#   |                 | |__| (_) | | | | |_| | | (_) | |                   |
#   |                  \____\___/|_| |_|\__|_|  \___/|_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Invoke actions affecting the core like reload/restart                |
#   '----------------------------------------------------------------------'

_LockingMode = Literal["abort", "wait"] | None


class CoreAction(enum.Enum):
    START = "start"
    RESTART = "restart"
    RELOAD = "reload"
    STOP = "stop"


def do_reload(
    config_cache: ConfigCache,
    hosts_config: Hosts,
    service_name_config: PassiveServiceNameConfig,
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
        service_name_config,
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
    service_name_config: PassiveServiceNameConfig,
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
        with activation_lock(mode=locking_mode):
            core_config.do_create_config(
                core=core,
                config_cache=config_cache,
                hosts_config=host_config,
                service_name_config=service_name_config,
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
            do_core_action(action, monitoring_core=core.name())

    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        raise MKBailOut("An error occurred: %s" % e)


# TODO: The store.lock_checkmk_configuration is doing something similar. It looks like we
# should unify these both locks. But: The lock_checkmk_configuration is currently acquired by the
# GUI process. In case the GUI calls an automation process, we would have a dead lock of these two
# processes. We'll have to check whether or not we can move the locking.
@contextmanager
def activation_lock(mode: Literal["abort", "wait"] | None) -> Iterator[None]:
    """Try to acquire the activation lock and raise exception in case it was not possible"""
    if mode is None:
        # TODO: We really should purge this strange case from being configurable
        yield None  # No locking at all
        return

    lock_file = str(cmk.utils.paths.default_config_dir / "main.mk")

    if mode == "abort":
        with store.try_locked(lock_file) as result:
            if result is False:
                raise MKBailOut("Other restart currently in progress. Aborting.")
            yield None
        return

    if mode == "wait":
        with store.locked(lock_file):
            yield None
        return

    raise ValueError(f"Invalid lock mode: {mode}")


def print_(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


def do_core_action(
    action: CoreAction,
    monitoring_core: Literal["nagios", "cmc"],
    quiet: bool = False,
) -> None:
    with tracer.span(
        f"do_core_action[{action.value}]",
        attributes={
            "cmk.core_config.core": monitoring_core,
        },
    ):
        if not quiet:
            print_("%sing monitoring core..." % action.value.title())

        if monitoring_core == "nagios":
            os.putenv("CORE_NOVERIFY", "yes")
            command = ["%s/etc/init.d/core" % cmk.utils.paths.omd_root, action.value]
        else:
            command = ["omd", action.value, "cmc"]

        completed_process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            check=False,
        )
        if completed_process.returncode != 0:
            if not quiet:
                print_("ERROR: %r\n" % completed_process.stdout)
            raise MKGeneralException(
                f"Cannot {action.value} the monitoring core: {completed_process.stdout!r}"
            )
        if not quiet:
            print_(tty.ok + "\n")
