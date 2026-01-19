#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for support of Nagios (and compatible) cores"""

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

import base64
import itertools
import os
import socket
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from io import StringIO
from pathlib import Path
from socket import AddressFamily
from typing import Any, assert_never, Final, IO, Literal

import cmk.utils.paths
from cmk.base import config
from cmk.base.config import (
    ConfigCache,
    HostgroupName,
    ObjectAttributes,
    ServicegroupName,
)
from cmk.base.core.interface import CoreAction, MonitoringCore
from cmk.base.core.shared import (
    AbstractServiceID,
    autodetect_plugin,
    check_icmp_arguments_of,
    CoreCommand,
    CoreCommandName,
    duplicate_service_warning,
    get_cluster_nodes_for_config,
    get_cmk_passive_service_attributes,
    get_labels_from_attributes,
    get_service_attributes,
    get_tags_with_groups_from_attributes,
    host_check_command,
)
from cmk.ccc import store, tty
from cmk.ccc.config_path import cleanup_old_configs, ConfigCreationContext
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.plugin_backend import plugin_index
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPlugin,
    CheckPluginName,
    ServiceID,
)
from cmk.fetchers import StoredSecrets
from cmk.password_store.v1_unstable import Secret
from cmk.server_side_calls_backend import ActiveServiceData
from cmk.utils import config_warnings, ip_lookup, password_store
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import LabelManager, Labels
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.notify import (
    create_notify_host_files,
    make_notify_host_file_path,
    NotificationHostConfig,
    NotifyHostFiles,
)
from cmk.utils.notify_types import Contact
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import MAX_SERVICE_NAME_LEN, ServiceName
from cmk.utils.timeperiod import TimeperiodSpecs

from ._precompile_host_checks import precompile_hostchecks, PrecompileMode

_ContactgroupName = str
ObjectSpec = dict[str, Any]


class NagiosCore(MonitoringCore):
    def __init__(
        self,
        licensing_handler_type: type[LicensingHandler],
        init_script_path: Path,
        objects_file_path: Path,
        # we should consider passing a NagiosConfig here, in analogy to CmcPb
        timeperiods: TimeperiodSpecs,
    ) -> None:
        super().__init__(licensing_handler_type)
        self.init_script_path: Final = init_script_path
        self.objects_file_path: Final = objects_file_path
        self.timeperiods: Final = timeperiods

    @classmethod
    def name(cls) -> Literal["nagios"]:
        return "nagios"

    @staticmethod
    def cleanup_old_configs(base: Path) -> None:
        cleanup_old_configs(base)

    @staticmethod
    def objects_file() -> str:
        return str(cmk.utils.paths.nagios_objects_file)

    def _run_command(self, action: CoreAction) -> subprocess.CompletedProcess[bytes]:
        os.putenv("CORE_NOVERIFY", "yes")
        return subprocess.run(
            [str(self.init_script_path), action.value],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            check=False,
        )

    def _create_config(
        self,
        config_creation_context: ConfigCreationContext,
        config_cache: ConfigCache,
        hosts_config: Hosts,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        get_ip_stack_config: Callable[[HostName], IPStackConfig],
        default_address_family: Callable[
            [HostName], Literal[AddressFamily.AF_INET, AddressFamily.AF_INET6]
        ],
        ip_address_of: ip_lookup.IPLookup,
        ip_address_of_mgmt: ip_lookup.IPLookupOptional,
        licensing_handler: LicensingHandler,
        plugins: AgentBasedPlugins,
        discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
        passwords: Mapping[str, Secret[str]],
        *,
        hosts_to_update: set[HostName] | None = None,
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> None:
        self._config_cache = config_cache
        self._create_core_config(
            config_creation_context.path_created,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            plugins.check_plugins,
            licensing_handler,
            passwords,
            get_ip_stack_config,
            default_address_family,
            ip_address_of,
            service_depends_on,
        )
        store.save_text_to_file(
            plugin_index.make_index_file(config_creation_context.path_created),
            plugin_index.create_plugin_index(plugins),
        )
        self._precompile_hostchecks(
            config_creation_context.path_created,
            passive_service_name_config,
            enforced_services_table,
            plugins,
            discovery_rules,
            get_ip_stack_config,
            ip_address_of,
            precompile_mode=(
                PrecompileMode.DELAYED if config.delay_precompile else PrecompileMode.INSTANT
            ),
        )

    def _create_core_config(
        self,
        config_path: Path,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        plugins: Mapping[CheckPluginName, CheckPlugin],
        licensing_handler: LicensingHandler,
        passwords: Mapping[str, Secret[str]],
        get_ip_stack_config: Callable[[HostName], IPStackConfig],
        default_address_family: Callable[
            [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
        ],
        ip_address_of: ip_lookup.IPLookup,
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> None:
        """Tries to create a new Checkmk object configuration file for the Nagios core

        During create_config() exceptions may be raised which are caused by configuration issues.
        Don't produce a half written object file. Simply throw away everything and keep the old file.

        The user can then start the site with the old configuration and fix the configuration issue
        while the monitoring is running.
        """

        config_buffer = StringIO()
        hosts_config = self._config_cache.hosts_config
        notify_host_files = create_config(
            config_buffer,
            self._config_cache,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            plugins,
            hostnames=sorted(
                {
                    hn
                    for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                    if self._config_cache.is_active(hn) and self._config_cache.is_online(hn)
                }
            ),
            licensing_handler=licensing_handler,
            passwords=passwords,
            get_ip_stack_config=get_ip_stack_config,
            default_address_family=default_address_family,
            ip_address_of=ip_address_of,
            service_depends_on=service_depends_on,
            timeperiods=self.timeperiods,
            get_relay_id=lambda host_name: config.get_relay_id(
                self._config_cache.label_manager.labels_of_host(host_name)
            ),
        )

        store.save_text_to_file(self.objects_file_path, config_buffer.getvalue())
        for host, content in notify_host_files.items():
            store.save_bytes_to_file(make_notify_host_file_path(config_path, host), content)

    def _precompile_hostchecks(
        self,
        config_path: Path,
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        plugins: AgentBasedPlugins,
        discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
        get_ip_stack_config: Callable[[HostName], IPStackConfig],
        ip_address_of: ip_lookup.IPLookup,
        *,
        precompile_mode: PrecompileMode,
    ) -> None:
        with suppress(IOError):
            sys.stdout.write("Precompiling host checks...")
            sys.stdout.flush()
        precompile_hostchecks(
            config_path,
            self._config_cache,
            passive_service_name_config,
            enforced_services_table,
            plugins,
            discovery_rules,
            get_ip_stack_config,
            ip_address_of,
            precompile_mode=precompile_mode,
        )
        with suppress(IOError):
            sys.stdout.write(tty.ok + "\n")
            sys.stdout.flush()


#   .--Create config-------------------------------------------------------.
#   |      ____                _                          __ _             |
#   |     / ___|_ __ ___  __ _| |_ ___    ___ ___  _ __  / _(_) __ _       |
#   |    | |   | '__/ _ \/ _` | __/ _ \  / __/ _ \| '_ \| |_| |/ _` |      |
#   |    | |___| | |  __/ (_| | ||  __/ | (_| (_) | | | |  _| | (_| |      |
#   |     \____|_|  \___|\__,_|\__\___|  \___\___/|_| |_|_| |_|\__, |      |
#   |                                                          |___/       |
#   +----------------------------------------------------------------------+
#   |  Create a configuration file for Nagios core with hosts + services   |
#   '----------------------------------------------------------------------'


class NagiosConfig:
    def __init__(
        self, outfile: IO[str], hostnames: Sequence[HostName] | None, timeperiods: TimeperiodSpecs
    ) -> None:
        super().__init__()
        self._outfile = outfile
        self.hostnames = hostnames

        self.hostgroups_to_define: set[HostgroupName] = set()
        self.servicegroups_to_define: set[ServicegroupName] = set()
        self.contactgroups_to_define: set[_ContactgroupName] = set()
        self.checknames_to_define: set[CheckPluginName] = set()
        self.active_checks_to_define: dict[str, str] = {}
        self.custom_commands_to_define: set[CoreCommandName] = set()
        self.hostcheck_commands_to_define: list[tuple[CoreCommand, str]] = []
        self.timeperiods: Final = timeperiods

    def write_str(self, x: str) -> None:
        self._outfile.write(x)

    def write_object(self, name: str, spec: ObjectSpec) -> None:
        self._outfile.write(_format_nagios_object(name, spec))


def _validate_licensing(
    hosts: Hosts, licensing_handler: LicensingHandler, licensing_counter: Counter
) -> None:
    if block_effect := licensing_handler.effect_core(
        licensing_counter["services"], len(hosts.shadow_hosts)
    ).block:
        raise MKGeneralException(block_effect.message_raw)


def create_config(
    outfile: IO[str],
    config_cache: ConfigCache,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    hostnames: Sequence[HostName],
    licensing_handler: LicensingHandler,
    passwords: Mapping[str, Secret[str]],
    get_ip_stack_config: Callable[[HostName], IPStackConfig],
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
    ip_address_of: ip_lookup.IPLookup,
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    timeperiods: TimeperiodSpecs,
    get_relay_id: Callable[[HostName], str | None],
) -> NotifyHostFiles:
    cfg = NagiosConfig(outfile, hostnames, timeperiods)

    _output_conf_header(cfg)

    licensing_counter = Counter("services")
    all_notify_host_configs: dict[HostName, NotificationHostConfig] = {}
    for hostname in hostnames:
        all_notify_host_configs[hostname] = _create_nagios_config_host(
            cfg,
            config_cache,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            plugins,
            hostname,
            get_ip_stack_config(hostname),
            default_address_family(hostname),
            passwords,
            licensing_counter,
            ip_address_of,
            service_depends_on,
            for_relay=get_relay_id(hostname) is not None,
        )

    _validate_licensing(config_cache.hosts_config, licensing_handler, licensing_counter)

    notify_host_files = create_notify_host_files(all_notify_host_configs)

    _create_nagios_config_contacts(cfg)
    if hostnames:
        _create_nagios_check_mk_notify_contact(cfg)
    _create_nagios_config_hostgroups(cfg)
    _create_nagios_config_servicegroups(cfg)
    _create_nagios_config_contactgroups(cfg)
    create_nagios_config_commands(cfg)
    _create_nagios_config_timeperiods(cfg)

    if config.extra_nagios_conf:
        cfg.write_str("\n# extra_nagios_conf\n\n")
        cfg.write_str(config.extra_nagios_conf)

    return notify_host_files


def _output_conf_header(cfg: NagiosConfig) -> None:
    cfg.write_str(
        """#
# Created by Check_MK. Do not edit.
#

"""
    )


def _create_nagios_config_host(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    hostname: HostName,
    ip_stack_config: IPStackConfig,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    stored_passwords: Mapping[str, Secret[str]],
    license_counter: Counter,
    ip_address_of: ip_lookup.IPLookup,
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    *,
    for_relay: bool,
) -> NotificationHostConfig:
    cfg.write_str("\n# ----------------------------------------------------\n")
    cfg.write_str("# %s\n" % hostname)
    cfg.write_str("# ----------------------------------------------------\n")

    host_attrs = config_cache.get_host_attributes(hostname, host_ip_family, ip_address_of)
    if config.generate_hostconf:
        host_spec = create_nagios_host_spec(
            cfg, config_cache, hostname, host_ip_family, host_attrs, ip_address_of
        )
        cfg.write_object("host", host_spec)

    return NotificationHostConfig(
        host_labels=get_labels_from_attributes(list(host_attrs.items())),
        service_labels=create_nagios_servicedefs(
            cfg,
            config_cache,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            plugins,
            hostname,
            ip_stack_config,
            host_ip_family,
            host_attrs,
            stored_passwords,
            license_counter,
            ip_address_of,
            service_depends_on,
            for_relay=for_relay,
        ),
        tags=get_tags_with_groups_from_attributes(list(host_attrs.items())),
    )


def create_nagios_host_spec(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    attrs: ObjectAttributes,
    ip_address_of: ip_lookup.IPLookup,
) -> ObjectSpec:
    ip = attrs["address"]

    if hostname in config_cache.hosts_config.clusters:
        ip_lookup_config = config_cache.ip_lookup_config()
        nodes = get_cluster_nodes_for_config(
            hostname,
            config_cache.nodes(hostname),
            ip_lookup_config.ip_stack_config(hostname),
            ip_lookup_config.default_address_family,
            config_cache.host_tags,
            config_cache.hosts_config.hosts,
            lambda h: config_cache.is_active(h) and config_cache.is_online(h),
        )
        attrs.update(
            config_cache.get_cluster_attributes(hostname, host_ip_family, nodes, ip_address_of)
        )

    #   _
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    host_spec = {
        "host_name": hostname,
        "use": (
            config.cluster_template
            if hostname in config_cache.hosts_config.clusters
            else config.host_template
        ),
        "address": (ip if ip else ip_lookup.fallback_ip_for(host_ip_family)),
        "alias": attrs["alias"],
    }

    # Add custom macros
    for key, value in attrs.items():
        if key[0] == "_":
            host_spec[key] = value

    def host_check_via_service_status(service: ServiceName) -> CoreCommand:
        command = "check-mk-host-custom-%d" % (len(cfg.hostcheck_commands_to_define) + 1)
        service_with_hostname = replace_macros_in_str(
            service,
            {"$HOSTNAME$": hostname},
        )
        cfg.hostcheck_commands_to_define.append(
            (
                command,
                'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$'
                % (
                    hostname,
                    service_with_hostname,
                    hostname,
                    service_with_hostname,
                ),
            ),
        )
        return command

    def host_check_via_custom_check(
        command_name: CoreCommandName, command: CoreCommand
    ) -> CoreCommand:
        cfg.custom_commands_to_define.add(command_name)
        return command

    # Host check command might differ from default
    command = host_check_command(
        config_cache,
        hostname,
        host_ip_family,
        ip,
        hostname in config_cache.hosts_config.clusters,
        "ping",
        host_check_via_service_status,
        host_check_via_custom_check,
    )
    if command:
        host_spec["check_command"] = command

    hostgroups = config_cache.hostgroups(hostname)
    if config.define_hostgroups or hostgroups == [config.default_host_group]:
        cfg.hostgroups_to_define.update(hostgroups)
    host_spec["hostgroups"] = ",".join(sorted(hostgroups))

    # Contact groups
    contactgroups = config_cache.contactgroups(hostname)
    if contactgroups:
        host_spec["contact_groups"] = ",".join(sorted(contactgroups))
        cfg.contactgroups_to_define.update(contactgroups)

    if hostname not in config_cache.hosts_config.clusters:
        # Parents for non-clusters

        # Get parents explicitly defined for host/folder via extra_host_conf["parents"]. Only honor
        # the ruleset "parents" in case no explicit parents are set
        if not attrs.get("parents", []):
            parents_list = config_cache.parents(hostname)
            if parents_list:
                host_spec["parents"] = ",".join(sorted(parents_list))

    elif hostname in config_cache.hosts_config.clusters:
        # Special handling of clusters
        host_spec["parents"] = ",".join(sorted(nodes))

    # Custom configuration last -> user may override all other values
    # TODO: Find a generic mechanism for CMC and Nagios
    for key, value in _to_nagios_core_attributes(
        config_cache.extra_host_attributes(hostname)
    ).items():
        if key == "cmk_agent_connection":
            continue
        if hostname in config_cache.hosts_config.clusters and key == "parents":
            continue
        host_spec[key] = value

    return host_spec


def transform_active_service_command(cfg: NagiosConfig, service_data: ActiveServiceData) -> str:
    if config.simulation_mode:
        cfg.custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"

    if service_data.command_name == "check-mk-custom":
        cfg.custom_commands_to_define.add("check-mk-custom")
        return f"{service_data.command_name}!{service_data.command}"

    escaped_args = " ".join(service_data.command[1:]).replace("\\", "\\\\").replace("!", "\\!")
    return f"{service_data.command_name}!{escaped_args}"


_ServiceLabels = dict[ServiceName, Labels]


def _process_services_data(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    hostname: HostName,
    license_counter: Counter,
    check_mk_attrs: dict[str, Any],
) -> tuple[dict[ServiceName, AbstractServiceID], _ServiceLabels]:
    host_check_table = config_cache.check_table(
        hostname,
        plugins,
        config_cache.make_service_configurer(plugins, passive_service_name_config),
        passive_service_name_config,
        enforced_services_table,
    )
    services_ids: dict[ServiceName, AbstractServiceID] = {}
    service_labels: dict[ServiceName, Labels] = {}
    for service in sorted(host_check_table.values(), key=lambda s: s.sort_key()):
        if not service.description:
            config_warnings.warn(
                f"Skipping invalid service with empty description (plugin: {service.check_plugin_name}) on host {hostname}"
            )
            continue

        if len(service.description) > MAX_SERVICE_NAME_LEN:
            config_warnings.warn(
                f"Skipping invalid service exceeding the name length limit of {MAX_SERVICE_NAME_LEN} "
                f"(plugin: {service.check_plugin_name}) on host: {hostname}, Service: {service.description}"
            )
            continue

        if service.description in services_ids:
            duplicate_service_warning(
                checktype="auto",
                description=service.description,
                host_name=hostname,
                first_occurrence=services_ids[service.description],
                second_occurrence=service.id(),
            )
            continue
        services_ids[service.description] = service.id()

        # Services Dependencies for autochecks
        cfg.write_str(_get_dependencies(service_depends_on, hostname, service.description))

        passive_service_attributes = _to_nagios_core_attributes(
            get_cmk_passive_service_attributes(
                config_cache,
                hostname,
                service.description,
                service.labels,
                check_mk_attrs,
            )
        )

        service_labels[service.description] = service.labels

        service_spec = (
            {
                "use": config.passive_service_template_perf,
                "host_name": hostname,
                "service_description": service.description,
                "check_command": "check_mk-%s" % service.check_plugin_name,
            }
            | passive_service_attributes
            | _extra_service_conf_of(
                cfg, config_cache, hostname, service.description, service.labels
            )
        )

        cfg.write_object("service", service_spec)
        license_counter["services"] += 1

        cfg.checknames_to_define.add(service.check_plugin_name)
    return services_ids, service_labels


_PingServiceNames = Literal["PING", "PING IPv4", "PING IPv6"]


def create_nagios_servicedefs(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ],
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    hostname: HostName,
    ip_stack_config: IPStackConfig,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    host_attrs: ObjectAttributes,
    stored_passwords: Mapping[str, Secret[str]],
    license_counter: Counter,
    ip_address_of: ip_lookup.IPLookup,
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    *,
    for_relay: bool,
) -> dict[ServiceName, Labels]:
    check_mk_labels = _get_service_labels(config_cache.label_manager, hostname, "Check_MK")
    check_mk_attrs = _to_nagios_core_attributes(
        get_service_attributes(config_cache, hostname, "Check_MK", check_mk_labels)
    )

    services_ids, service_labels = _process_services_data(
        cfg,
        config_cache,
        passive_service_name_config,
        enforced_services_table,
        service_depends_on,
        plugins,
        hostname,
        license_counter,
        check_mk_attrs,
    )

    # Active check for Check_MK
    if config_cache.checkmk_check_parameters(hostname).enabled:
        service_spec = (
            {
                "use": config.active_service_template,
                "host_name": hostname,
                "service_description": "Check_MK",
            }
            | check_mk_attrs
            | _extra_service_conf_of(cfg, config_cache, hostname, "Check_MK", check_mk_labels)
        )

        cfg.write_object("service", service_spec)
        license_counter["services"] += 1

    # legacy checks via active_checks
    active_services = []
    for service_data in config_cache.active_check_services(
        hostname,
        ip_stack_config,
        host_ip_family,
        host_attrs,
        final_service_name_config,
        ip_address_of,
        StoredSecrets(
            path=password_store.active_secrets_path_site(),
            secrets=stored_passwords,
        ),
        for_relay=for_relay,
    ):
        active_service_labels = _get_service_labels(
            config_cache.label_manager, hostname, service_data.description
        )

        if _skip_service(config_cache, hostname, service_data.description, active_service_labels):
            continue

        if (existing_plugin := services_ids.get(service_data.description)) is not None:
            duplicate_service_warning(
                checktype="active",
                description=service_data.description,
                host_name=hostname,
                first_occurrence=existing_plugin,
                second_occurrence=(f"active({service_data.plugin_name})", None),
            )
            continue

        services_ids[service_data.description] = (
            f"active({service_data.plugin_name})",
            service_data.description,
        )

        service_attributes = _to_nagios_core_attributes(
            get_service_attributes(
                config_cache,
                hostname,
                service_data.description,
                active_service_labels,
            )
        )

        service_labels[service_data.description] = dict(
            get_labels_from_attributes(list(service_attributes.items()))
        )

        service_spec = (
            {
                "use": "check_mk_perf,check_mk_default",
                "host_name": hostname,
                "service_description": service_data.description,
                "check_command": transform_active_service_command(cfg, service_data),
                "active_checks_enabled": str(1),
            }
            | service_attributes
            | _extra_service_conf_of(
                cfg, config_cache, hostname, service_data.description, active_service_labels
            )
        )

        cfg.active_checks_to_define[service_data.plugin_name] = service_data.command[0]
        active_services.append(service_spec)

    active_checks_rules_exist = any(params for _, params in config_cache.active_checks(hostname))
    # Note: ^- This is not the same as `active_checks_present = bool(active_services)`
    # Services can be omitted, or rules can result in zero services (theoretically).
    # I am not sure if this is intentional.
    if active_checks_rules_exist:
        cfg.write_str("\n\n# Active checks\n")

        license_counter["services"] += len(active_services)
        for service_spec in active_services:
            cfg.write_object("service", service_spec)
            cfg.write_str(
                _get_dependencies(service_depends_on, hostname, service_spec["service_description"])
            )

    # Legacy checks via custom_checks
    custom_checks = config_cache.custom_checks(hostname)
    if custom_checks:
        cfg.write_str("\n\n# Custom checks\n")
        for entry in custom_checks:
            _create_custom_check(
                entry,
                cfg,
                config_cache,
                final_service_name_config,
                hostname,
                license_counter,
                services_ids,
                service_labels,
                service_depends_on,
            )
    service_discovery_name = ConfigCache.service_discovery_name()

    # Inventory checks - if user has configured them.
    if not (disco_params := config_cache.discovery_check_parameters(hostname)).commandline_only:
        labels = _get_service_labels(config_cache.label_manager, hostname, service_discovery_name)
        service_spec = (
            {
                "use": config.inventory_check_template,
                "host_name": hostname,
                "service_description": service_discovery_name,
            }
            | _to_nagios_core_attributes(
                get_service_attributes(config_cache, hostname, service_discovery_name, labels)
            )
            | _extra_service_conf_of(cfg, config_cache, hostname, service_discovery_name, labels)
            | {
                "check_interval": str(disco_params.check_interval),
                "retry_interval": str(disco_params.check_interval),
            }
        )

        cfg.write_object("service", service_spec)
        license_counter["services"] += 1

        if services_ids:
            cfg.write_object(
                "servicedependency",
                {
                    "use": config.service_dependency_template,
                    "host_name": hostname,
                    "service_description": "Check_MK",
                    "dependent_host_name": hostname,
                    "dependent_service_description": service_discovery_name,
                },
            )

    ping_services: list[_PingServiceNames] = []

    # No check_mk service, no legacy service -> create PING service
    if not services_ids and not active_checks_rules_exist and not custom_checks:
        ping_services.append("PING")

    if ip_stack_config is IPStackConfig.DUAL_STACK:
        if host_ip_family is AddressFamily.AF_INET6:
            if "PING IPv4" not in services_ids:
                ping_services.append("PING IPv4")
        elif "PING IPv6" not in services_ids:
            ping_services.append("PING IPv6")

    for ping_service in ping_services:
        _add_ping_service(
            cfg, config_cache, hostname, host_ip_family, host_attrs, ping_service, license_counter
        )

    return service_labels


def _create_custom_check(
    entry: dict[str, Any],
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ],
    hostname: HostName,
    license_counter: Counter,
    services_ids: dict[ServiceName, AbstractServiceID],
    service_labels: dict[ServiceName, Labels],
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
) -> None:
    # entries are dicts with the following keys:
    # "service_description"        Service name to use
    # "command_line"  (optional)   Unix command line for executing the check
    #                              If this is missing, we create a passive check
    # "command_name"  (optional)   Name of Monitoring command to define. If missing,
    #                              we use "check-mk-custom"
    description = final_service_name_config(
        hostname,
        ServiceName(entry["service_description"]),
        config_cache.label_manager.labels_of_host,
    )
    command_name = entry.get("command_name", "check-mk-custom")
    command_line = entry.get("command_line", "")

    if not description:
        config_warnings.warn(
            "Skipping invalid service with empty description on host %s" % hostname
        )
        return

    if command_line:
        command_line = autodetect_plugin(command_line).replace("\\", "\\\\").replace("!", "\\!")

    if "freshness" in entry:
        freshness = {
            "check_freshness": 1,
            "freshness_threshold": 60 * entry["freshness"]["interval"],
        }
        command_line = "echo %s && exit %d" % (
            _quote_nagios_string(entry["freshness"]["output"]),
            entry["freshness"]["state"],
        )
    else:
        freshness = {}

    cfg.custom_commands_to_define.add(command_name)

    if description in services_ids:
        cn, _ = services_ids[description]
        # If we have the same active check again with the same description,
        # then we do not regard this as an error, but simply ignore the
        # second one.
        if cn == "custom(%s)" % command_name:
            return

        duplicate_service_warning(
            checktype="custom",
            description=description,
            host_name=hostname,
            first_occurrence=services_ids[description],
            second_occurrence=("custom(%s)" % command_name, description),
        )
        return

    services_ids[description] = ("custom(%s)" % command_name, description)

    command = f"{command_name}!{command_line}"

    labels = _get_service_labels(config_cache.label_manager, hostname, description)

    service_attr = _to_nagios_core_attributes(
        get_service_attributes(config_cache, hostname, description, labels)
    )
    service_spec = (
        {
            "use": "check_mk_perf,check_mk_default",
            "host_name": hostname,
            "service_description": description,
            "check_command": _simulate_command(cfg, command),
            "active_checks_enabled": str(1 if (command_line and not freshness) else 0),
        }
        | freshness
        | service_attr
        | _extra_service_conf_of(cfg, config_cache, hostname, description, labels)
    )

    service_labels[description] = dict(get_labels_from_attributes(list(service_attr.items())))

    cfg.write_object("service", service_spec)
    license_counter["services"] += 1

    # write service dependencies for custom checks
    cfg.write_str(_get_dependencies(service_depends_on, hostname, description))


def _get_service_labels(
    label_manager: LabelManager, hostname: HostName, service_name: ServiceName
) -> Labels:
    return label_manager.labels_of_service(hostname, service_name, {})


def _skip_service(
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    service_labels: Labels,
) -> bool:
    if config_cache.service_ignored(host_name, service_name, service_labels):
        return True
    if host_name != config_cache.effective_host(host_name, service_name, service_labels):
        return True
    return False


def _get_dependencies(
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    hostname: HostName,
    service_name: ServiceName,
) -> str:
    return "".join(
        _format_nagios_object(
            "servicedependency",
            {
                "use": config.service_dependency_template,
                "host_name": hostname,
                "service_description": dep,
                "dependent_host_name": hostname,
                "dependent_service_description": service_name,
            },
        )
        for dep in service_depends_on(hostname, service_name)
    )


def _add_ping_service(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    host_name: HostName,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    host_attrs: Mapping[str, Any],
    ping_service: _PingServiceNames,
    licensing_counter: Counter,
) -> None:
    ipaddress = host_attrs["address"]
    service_labels = _get_service_labels(config_cache.label_manager, host_name, ping_service)
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    match ping_service:
        case "PING IPv4":
            family = AddressFamily.AF_INET
            node_ips_name = "_NODEIPS_4"
        case "PING IPv6":
            family = AddressFamily.AF_INET6
            node_ips_name = "_NODEIPS_6"
        case "PING":
            family = host_ip_family
            node_ips_name = "_NODEIPS"
        case _:
            assert_never(f"Unexpected ping service name: {ping_service}")

    arguments = check_icmp_arguments_of(config_cache, host_name, family)

    if host_name in config_cache.hosts_config.clusters:
        arguments += " -m 1 " + host_attrs[node_ips_name]  # may raise exception - it's intentional
    else:
        arguments += " " + ipaddress

    service_spec = _make_ping_only_spec(
        cfg, config_cache, host_name, ping_service, arguments, service_labels
    )

    cfg.write_object("service", service_spec)
    licensing_counter["services"] += 1


def _make_ping_only_spec(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    arguments: str,
    service_labels: Labels,
) -> dict[str, str | HostAddress]:
    ping_command = "check-mk-ping"
    return (
        {
            "use": config.pingonly_template,
            "host_name": host_name,
            "service_description": service_name,
            "check_command": f"{ping_command}!{arguments}",
        }
        | _to_nagios_core_attributes(
            get_service_attributes(config_cache, host_name, service_name, service_labels)
        )
        | _extra_service_conf_of(cfg, config_cache, host_name, service_name, service_labels)
    )


def _format_nagios_object(object_type: str, object_spec: ObjectSpec) -> str:
    lines = ["define %s {" % object_type]
    for key, val in sorted(object_spec.items(), key=lambda x: x[0]):
        # Use a base16 encoding for names and values of tags, labels and label
        # sources to work around the syntactic restrictions in Nagios' object
        # configuration files.
        if key[0] == "_":  # quick pre-check: custom variable?
            for prefix in ("__TAG_", "__LABEL_", "__LABELSOURCE_"):
                if key.startswith(prefix):
                    key = prefix + _b16encode(key[len(prefix) :])
                    val = _b16encode(val)
        lines.append("  %-29s %s" % (key, val))
    lines.append("}")

    return "\n".join(lines) + "\n\n"


def _b16encode(b: str) -> str:
    return (base64.b16encode(b.encode())).decode()


def _simulate_command(cfg: NagiosConfig, command: CoreCommand) -> CoreCommand:
    if config.simulation_mode:
        cfg.custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"
    return command


def _create_nagios_config_hostgroups(cfg: NagiosConfig) -> None:
    if config.define_hostgroups:
        cfg.write_str("\n# ------------------------------------------------------------\n")
        cfg.write_str("# Host groups (controlled by define_hostgroups)\n")
        cfg.write_str("# ------------------------------------------------------------\n")
        for hg in sorted(cfg.hostgroups_to_define):
            cfg.write_object(
                "hostgroup",
                {
                    "hostgroup_name": hg,
                    "alias": config.define_hostgroups.get(hg, hg),
                },
            )

    # No creation of host groups but we need to define default host group
    elif config.default_host_group in cfg.hostgroups_to_define:
        cfg.write_object(
            "hostgroup",
            {
                "hostgroup_name": config.default_host_group,
                "alias": "Check_MK default hostgroup",
            },
        )


def _create_nagios_config_servicegroups(cfg: NagiosConfig) -> None:
    if not config.define_servicegroups:
        return
    cfg.write_str("\n# ------------------------------------------------------------\n")
    cfg.write_str("# Service groups (controlled by define_servicegroups)\n")
    cfg.write_str("# ------------------------------------------------------------\n")
    for sg in sorted(cfg.servicegroups_to_define):
        cfg.write_object(
            "servicegroup",
            {
                "servicegroup_name": sg,
                "alias": config.define_servicegroups.get(sg, sg),
            },
        )


def _create_nagios_config_contactgroups(cfg: NagiosConfig) -> None:
    if not cfg.contactgroups_to_define:
        return
    cfg.write_str("\n# ------------------------------------------------------------\n")
    cfg.write_str("# Contact groups (controlled by define_contactgroups)\n")
    cfg.write_str("# ------------------------------------------------------------\n\n")
    for name in sorted(cfg.contactgroups_to_define):
        contactgroup_spec = {
            "contactgroup_name": name,
            "alias": config.define_contactgroups.get(name, name),
        }
        if members := config.contactgroup_members.get(name):
            contactgroup_spec["members"] = ",".join(sorted(members))
        cfg.write_object("contactgroup", contactgroup_spec)


def create_nagios_config_commands(cfg: NagiosConfig) -> None:
    if config.generate_dummy_commands:
        cfg.write_str("\n# ------------------------------------------------------------\n")
        cfg.write_str("# Dummy check commands and active check commands\n")
        cfg.write_str("# ------------------------------------------------------------\n\n")
        for checkname in sorted(cfg.checknames_to_define):
            cfg.write_object(
                "command",
                {
                    "command_name": "check_mk-%s" % checkname,
                    "command_line": config.dummy_check_commandline,
                },
            )

    # active_checks
    for acttype, detected_executable in sorted(cfg.active_checks_to_define.items()):
        cfg.write_object(
            "command",
            {
                "command_name": f"check_mk_active-{acttype}",
                "command_line": f"{detected_executable} $ARG1$",
            },
        )

    # custom_checks
    for command_name in sorted(cfg.custom_commands_to_define):
        cfg.write_object(
            "command",
            {
                "command_name": command_name,
                "command_line": "$ARG1$",
            },
        )

    # custom host checks
    for command_name, command_line in sorted(cfg.hostcheck_commands_to_define):
        cfg.write_object(
            "command",
            {
                "command_name": command_name,
                "command_line": command_line,
            },
        )


def _create_nagios_config_timeperiods(cfg: NagiosConfig) -> None:
    cfg.write_str("\n# ------------------------------------------------------------\n")
    cfg.write_str("# Timeperiod definitions (controlled by variable 'timeperiods')\n")
    cfg.write_str("# ------------------------------------------------------------\n\n")
    for name, tp in sorted(cfg.timeperiods.items()):
        timeperiod_spec = {
            "timeperiod_name": name,
            "alias": tp["alias"],
        }
        for key in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            if key in tp and (times := ",".join((f"{fr}-{to}") for fr, to in tp[key])):
                timeperiod_spec[key] = times
        if exclude := tp.get("exclude", []):
            timeperiod_spec["exclude"] = ",".join(sorted(exclude))
        cfg.write_object("timeperiod", timeperiod_spec)


def _create_nagios_config_contacts(cfg: NagiosConfig) -> None:
    if config.contacts:
        cfg.write_str("\n# ------------------------------------------------------------\n")
        cfg.write_str("# Contact definitions (controlled by variable 'contacts')\n")
        cfg.write_str("# ------------------------------------------------------------\n\n")
        for cname, contact in sorted(config.contacts.items()):
            if contact_groups := _update_contact_groups(cfg, contact):
                contact_spec = _make_contact_spec(cname, contact, contact_groups)
                cfg.write_object("contact", contact_spec)


def _update_contact_groups(cfg: NagiosConfig, contact: Contact) -> list[str]:
    # Create contact groups in nagios, even when they are empty. This is needed
    # for RBN to work correctly when using contactgroups as recipients which are
    # not assigned to any host
    cfg.contactgroups_to_define.update(contact.get("contactgroups", []))
    # If the contact is in no contact group or all of the contact groups
    # of the contact have neither hosts nor services assigned - in other
    # words if the contact is not assigned to any host or service, then
    # we do not create this contact in Nagios. It's useless and will produce
    # warnings.
    return [cgr for cgr in contact.get("contactgroups", []) if cgr in cfg.contactgroups_to_define]


def _make_contact_spec(name: str, contact: Contact, contact_groups: Sequence[str]) -> ObjectSpec:
    contact_spec: ObjectSpec = {
        "contact_name": name,
    }

    if "alias" in contact:
        contact_spec["alias"] = contact["alias"]

    if "email" in contact:
        contact_spec["email"] = contact["email"]

    if "pager" in contact:
        contact_spec["pager"] = contact["pager"]

    for what in ["host", "service"]:
        if what == "host":
            no: str = contact.get("host_notification_options", "")
        elif what == "service":
            no = contact.get("service_notification_options", "")
        else:
            raise ValueError()

        if not no:
            contact_spec["%s_notifications_enabled" % what] = 0
            no = "n"

        contact_spec.update(
            {
                "%s_notification_options" % what: ",".join(sorted(no)),
                "%s_notification_period" % what: contact.get("notification_period", "24X7"),
                "%s_notification_commands" % what: contact.get(
                    "%s_notification_commands" % what, "check-mk-notify"
                ),
            }
        )

    # Add custom macros
    contact_spec.update({key: val for key, val in contact.items() if key.startswith("_")})
    contact_spec["contactgroups"] = ", ".join(sorted(contact_groups))

    return contact_spec


def _create_nagios_check_mk_notify_contact(cfg: NagiosConfig) -> None:
    cfg.contactgroups_to_define.add("check-mk-notify")
    cfg.write_str("# Needed for rule based notifications\n")
    cfg.write_object(
        "contact",
        {
            "contact_name": "check-mk-notify",
            "alias": "Contact for rule based notifications",
            "host_notification_options": "d,u,r,f,s",
            "service_notification_options": "u,c,w,r,f,s",
            "host_notification_period": "24X7",
            "service_notification_period": "24X7",
            "host_notification_commands": "check-mk-notify",
            "service_notification_commands": "check-mk-notify",
            "contactgroups": "check-mk-notify",
        },
    )


def _quote_nagios_string(s: str) -> str:
    """Quote string for use in a nagios command execution.  Please note that also
    quoting for ! and backslash for Nagios itself takes place here."""
    return "'" + s.replace("\\", "\\\\").replace("'", "'\"'\"'").replace("!", "\\!") + "'"


def _to_nagios_core_attributes(attrs: ObjectAttributes) -> ObjectAttributes:
    # The field service_period does not exist in Nagios while it exists natively in the CMC. To
    # make it available in the Nagios configuration, we add a custom macro _SERVICE_PERIOD.
    return {
        "_SERVICE_PERIOD" if key == "service_period" else key: value for key, value in attrs.items()
    }


def _extra_service_conf_of(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    service_labels: Labels,
) -> ObjectSpec:
    """Collect all extra configuration data for a service"""
    service_spec: ObjectSpec = {}

    # Add contact groups to the config only if the user has defined them.
    # Otherwise inherit the contact groups from the host.
    # "check-mk-notify" is always returned for rulebased notifications and
    # the Nagios core and not defined by the user.
    sercgr = config_cache.contactgroups_of_service(host_name, service_name, service_labels)
    if sercgr != ["check-mk-notify"]:
        service_spec["contact_groups"] = ",".join(sorted(sercgr))
        cfg.contactgroups_to_define.update(sercgr)

    sergr = config_cache.servicegroups_of_service(host_name, service_name, service_labels)
    if sergr:
        service_spec["service_groups"] = ",".join(sorted(sergr))
        if config.define_servicegroups:
            cfg.servicegroups_to_define.update(sergr)

    return service_spec
