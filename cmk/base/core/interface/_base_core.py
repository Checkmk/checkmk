#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from typing import Final, Literal

from cmk import trace
from cmk.base.config import ConfigCache
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.plugins import AgentBasedPlugins, ServiceID
from cmk.utils import ip_lookup
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.labels import Labels
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.licensing.helper import get_licensed_state_file_path
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import ServiceName

tracer = trace.get_tracer()


class CoreAction(enum.Enum):
    START = "start"
    RESTART = "restart"
    RELOAD = "reload"
    STOP = "stop"


class MonitoringCore(abc.ABC):
    def __init__(self, licensing_handler_type: type[LicensingHandler]):
        self.licensing_handler_type: Final = licensing_handler_type

    @classmethod
    @abc.abstractmethod
    def name(cls) -> Literal["nagios", "cmc"]:
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def is_cmc() -> bool:
        raise NotImplementedError

    def create_config(
        self,
        config_path: VersionedConfigPath,
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
        passwords: Mapping[str, str],
        hosts_to_update: set[HostName] | None,
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> None:
        licensing_handler = self.licensing_handler_type.make()
        licensing_handler.persist_licensed_state(get_licensed_state_file_path())
        self._create_config(
            config_path,
            config_cache,
            hosts_config,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            get_ip_stack_config,
            default_address_family,
            ip_address_of,
            ip_address_of_mgmt,
            licensing_handler,
            plugins,
            discovery_rules,
            passwords,
            hosts_to_update=hosts_to_update,
            service_depends_on=service_depends_on,
        )

    @abc.abstractmethod
    def _create_config(
        self,
        config_path: VersionedConfigPath,
        config_cache: ConfigCache,
        hosts_config: Hosts,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
        default_address_family: Callable[
            [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
        ],
        ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
        ip_address_of_mgmt: ip_lookup.IPLookupOptional,
        licensing_handler: LicensingHandler,
        plugins: AgentBasedPlugins,
        discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
        passwords: Mapping[str, str],
        *,
        hosts_to_update: set[HostName] | None = None,
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> None:
        raise NotImplementedError

    def run(
        self,
        action: CoreAction,
        *,
        log: Callable[[str], None] | None = None,
    ) -> None:
        if log is None:
            log = _print_
        with tracer.span(
            f"do_core_action[{action.value}]",
            attributes={
                "cmk.core_config.core": self.name(),
            },
        ):
            log("%sing monitoring core..." % action.value.title())

            completed_process = self._run_command(action)
            if completed_process.returncode != 0:
                log("ERROR: %r\n" % completed_process.stdout)
                raise MKGeneralException(
                    f"Cannot {action.value} the monitoring core: {completed_process.stdout!r}"
                )
            log(tty.ok + "\n")

    @abc.abstractmethod
    def _run_command(self, action: CoreAction) -> subprocess.CompletedProcess[bytes]:
        raise NotImplementedError


def _print_(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()
