#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for support of Nagios (and compatible) cores"""

import base64
import itertools
import socket
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import suppress
from io import StringIO
from typing import Any, cast, Final, IO, Literal

import cmk.ccc.debug
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.config_path
import cmk.utils.paths
from cmk.utils import config_warnings, ip_lookup, password_store, tty
from cmk.utils.config_path import LATEST_CONFIG, VersionedConfigPath
from cmk.utils.hostaddress import HostAddress, HostName, Hosts
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import Labels
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.notify import NotificationHostConfig, write_notify_host_file
from cmk.utils.servicename import MAX_SERVICE_NAME_LEN, ServiceName

from cmk.checkengine.checking import CheckPluginName

import cmk.base.utils
from cmk.base import config, core_config
from cmk.base.api.agent_based.register import AgentBasedPlugins, get_check_plugin
from cmk.base.config import ConfigCache, HostgroupName, ObjectAttributes, ServicegroupName
from cmk.base.core_config import (
    AbstractServiceID,
    CoreCommand,
    CoreCommandName,
    get_labels_from_attributes,
    get_tags_with_groups_from_attributes,
)

from cmk.server_side_calls_backend import ActiveServiceData

from ._precompile_host_checks import precompile_hostchecks, PrecompileMode

_ContactgroupName = str
ObjectSpec = dict[str, Any]


_NO_DISCOVERED_LABELS: Final[Labels] = {}  # just for better readablity


class NagiosCore(core_config.MonitoringCore):
    @classmethod
    def name(cls) -> Literal["nagios"]:
        return "nagios"

    @staticmethod
    def is_cmc() -> Literal[False]:
        return False

    def _create_config(
        self,
        config_path: VersionedConfigPath,
        config_cache: ConfigCache,
        ip_address_of: config.IPLookup,
        licensing_handler: LicensingHandler,
        plugins: AgentBasedPlugins,
        passwords: Mapping[str, str],
        hosts_to_update: set[HostName] | None = None,
    ) -> None:
        self._config_cache = config_cache
        self._create_core_config(config_path, licensing_handler, passwords, ip_address_of)
        self._precompile_hostchecks(
            config_path,
            plugins,
            precompile_mode=(
                PrecompileMode.DELAYED if config.delay_precompile else PrecompileMode.INSTANT
            ),
        )

    def _create_core_config(
        self,
        config_path: VersionedConfigPath,
        licensing_handler: LicensingHandler,
        passwords: Mapping[str, str],
        ip_address_of: config.IPLookup,
    ) -> None:
        """Tries to create a new Checkmk object configuration file for the Nagios core

        During create_config() exceptions may be raised which are caused by configuration issues.
        Don't produce a half written object file. Simply throw away everything and keep the old file.

        The user can then start the site with the old configuration and fix the configuration issue
        while the monitoring is running.
        """

        config_buffer = StringIO()
        hosts_config = self._config_cache.hosts_config
        create_config(
            config_buffer,
            config_path,
            self._config_cache,
            hostnames=sorted(
                {
                    hn
                    for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                    if self._config_cache.is_active(hn) and self._config_cache.is_online(hn)
                }
            ),
            licensing_handler=licensing_handler,
            passwords=passwords,
            ip_address_of=ip_address_of,
        )

        store.save_text_to_file(cmk.utils.paths.nagios_objects_file, config_buffer.getvalue())

    def _precompile_hostchecks(
        self,
        config_path: VersionedConfigPath,
        plugins: AgentBasedPlugins,
        *,
        precompile_mode: PrecompileMode,
    ) -> None:
        with suppress(IOError):
            sys.stdout.write("Precompiling host checks...")
            sys.stdout.flush()
        precompile_hostchecks(
            config_path,
            self._config_cache,
            plugins,
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
    def __init__(self, outfile: IO[str], hostnames: Sequence[HostName] | None) -> None:
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

    def write(self, x: str) -> None:
        # TODO: Something seems to be mixed up in our call sites...
        self._outfile.write(x)


def _validate_licensing(
    hosts: Hosts, licensing_handler: LicensingHandler, licensing_counter: Counter
) -> None:
    if block_effect := licensing_handler.effect_core(
        licensing_counter["services"], len(hosts.shadow_hosts)
    ).block:
        raise MKGeneralException(block_effect.message_raw)


def create_config(
    outfile: IO[str],
    config_path: VersionedConfigPath,
    config_cache: ConfigCache,
    hostnames: Sequence[HostName],
    licensing_handler: LicensingHandler,
    passwords: Mapping[str, str],
    ip_address_of: config.IPLookup,
) -> None:
    cfg = NagiosConfig(outfile, hostnames)

    _output_conf_header(cfg)

    licensing_counter = Counter("services")
    all_notify_host_configs: dict[HostName, NotificationHostConfig] = {}
    for hostname in hostnames:
        all_notify_host_configs[hostname] = _create_nagios_config_host(
            cfg, config_cache, hostname, passwords, licensing_counter, ip_address_of
        )

    _validate_licensing(config_cache.hosts_config, licensing_handler, licensing_counter)

    write_notify_host_file(config_path, all_notify_host_configs)

    _create_nagios_config_contacts(cfg, hostnames)
    _create_nagios_config_hostgroups(cfg)
    _create_nagios_config_servicegroups(cfg)
    _create_nagios_config_contactgroups(cfg)
    create_nagios_config_commands(cfg)
    _create_nagios_config_timeperiods(cfg)

    if config.extra_nagios_conf:
        cfg.write("\n# extra_nagios_conf\n\n")
        cfg.write(config.extra_nagios_conf)


def _output_conf_header(cfg: NagiosConfig) -> None:
    cfg.write(
        """#
# Created by Check_MK. Do not edit.
#

"""
    )


def _create_nagios_config_host(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    stored_passwords: Mapping[str, str],
    license_counter: Counter,
    ip_address_of: config.IPLookup,
) -> NotificationHostConfig:
    cfg.write("\n# ----------------------------------------------------\n")
    cfg.write("# %s\n" % hostname)
    cfg.write("# ----------------------------------------------------\n")

    host_attrs = config_cache.get_host_attributes(hostname, ip_address_of)
    if config.generate_hostconf:
        host_spec = create_nagios_host_spec(cfg, config_cache, hostname, host_attrs, ip_address_of)
        cfg.write(format_nagios_object("host", host_spec))

    return NotificationHostConfig(
        host_labels=get_labels_from_attributes(list(host_attrs.items())),
        service_labels=create_nagios_servicedefs(
            cfg,
            config_cache,
            hostname,
            host_attrs,
            stored_passwords,
            license_counter,
            ip_address_of,
        ),
        tags=get_tags_with_groups_from_attributes(list(host_attrs.items())),
    )


def create_nagios_host_spec(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    attrs: ObjectAttributes,
    ip_address_of: config.IPLookup,
) -> ObjectSpec:
    ip = attrs["address"]

    if hostname in config_cache.hosts_config.clusters:
        nodes = config_cache.get_cluster_nodes_for_config(hostname)
        attrs.update(config_cache.get_cluster_attributes(hostname, nodes, ip_address_of))

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
        "address": (
            ip if ip else ip_lookup.fallback_ip_for(config_cache.default_address_family(hostname))
        ),
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
    command = core_config.host_check_command(
        config_cache,
        hostname,
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
    host_spec["hostgroups"] = ",".join(hostgroups)

    # Contact groups
    contactgroups = config_cache.contactgroups(hostname)
    if contactgroups:
        host_spec["contact_groups"] = ",".join(contactgroups)
        cfg.contactgroups_to_define.update(contactgroups)

    if hostname not in config_cache.hosts_config.clusters:
        # Parents for non-clusters

        # Get parents explicitly defined for host/folder via extra_host_conf["parents"]. Only honor
        # the ruleset "parents" in case no explicit parents are set
        if not attrs.get("parents", []):
            parents_list = config_cache.parents(hostname)
            if parents_list:
                host_spec["parents"] = ",".join(parents_list)

    elif hostname in config_cache.hosts_config.clusters:
        # Special handling of clusters
        host_spec["parents"] = ",".join(nodes)

    # Custom configuration last -> user may override all other values
    # TODO: Find a generic mechanism for CMC and Nagios
    for key, value in config_cache.extra_host_attributes(hostname).items():
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


def create_nagios_servicedefs(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    host_attrs: ObjectAttributes,
    stored_passwords: Mapping[str, str],
    license_counter: Counter,
    ip_address_of: config.IPLookup,
) -> dict[ServiceName, Labels]:
    check_mk_labels = config_cache.ruleset_matcher.labels_of_service(
        hostname, "Check_MK", _NO_DISCOVERED_LABELS
    )
    check_mk_attrs = core_config.get_service_attributes(
        config_cache, hostname, "Check_MK", check_mk_labels, extra_icon=None
    )

    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services

    def do_omit_service(
        host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> bool:
        if config_cache.service_ignored(host_name, service_name, service_labels):
            return True
        if hostname != config_cache.effective_host(host_name, service_name, service_labels):
            return True
        return False

    def get_dependencies(hostname: HostName, servicedesc: ServiceName) -> str:
        result = ""
        for dep in config.service_depends_on(config_cache, hostname, servicedesc):
            result += format_nagios_object(
                "servicedependency",
                {
                    "use": config.service_dependency_template,
                    "host_name": hostname,
                    "service_description": dep,
                    "dependent_host_name": hostname,
                    "dependent_service_description": servicedesc,
                },
            )

        return result

    host_check_table = config_cache.check_table(hostname)
    have_at_least_one_service = False
    used_descriptions: dict[ServiceName, AbstractServiceID] = {}
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

        if service.description in used_descriptions:
            core_config.duplicate_service_warning(
                checktype="auto",
                description=service.description,
                host_name=hostname,
                first_occurrence=used_descriptions[service.description],
                second_occurrence=service.id(),
            )
            continue
        used_descriptions[service.description] = service.id()

        # Services Dependencies for autochecks
        cfg.write(get_dependencies(hostname, service.description))

        service_spec = {
            "use": config.passive_service_template_perf,
            "host_name": hostname,
            "service_description": service.description,
            "check_command": "check_mk-%s" % service.check_plugin_name,
        }

        plugin = get_check_plugin(service.check_plugin_name)
        passive_service_attributes = core_config.get_cmk_passive_service_attributes(
            config_cache,
            hostname,
            service.description,
            service.labels,
            check_mk_attrs,
            extra_icon=None
            if plugin is None
            else config_cache.make_extra_icon(plugin.check_ruleset_name, service.parameters),
        )

        service_labels[service.description] = service.labels

        service_spec.update(passive_service_attributes)

        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service.description, service.labels)
        )

        cfg.write(format_nagios_object("service", service_spec))
        license_counter["services"] += 1

        cfg.checknames_to_define.add(service.check_plugin_name)
        have_at_least_one_service = True

    # Active check for Check_MK
    if config_cache.checkmk_check_parameters(hostname).enabled:
        service_spec = {
            "use": config.active_service_template,
            "host_name": hostname,
            "service_description": "Check_MK",
        }
        service_spec.update(check_mk_attrs)
        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, "Check_MK", check_mk_labels)
        )
        cfg.write(format_nagios_object("service", service_spec))
        license_counter["services"] += 1

    # legacy checks via active_checks
    active_services = []
    for service_data in config_cache.active_check_services(
        hostname,
        host_attrs,
        ip_address_of,
        stored_passwords,
        password_store.core_password_store_path(LATEST_CONFIG),
    ):
        active_service_labels = config_cache.ruleset_matcher.labels_of_service(
            hostname, service_data.description, _NO_DISCOVERED_LABELS
        )
        if do_omit_service(hostname, service_data.description, active_service_labels):
            continue

        if (existing_plugin := used_descriptions.get(service_data.description)) is not None:
            core_config.duplicate_service_warning(
                checktype="active",
                description=service_data.description,
                host_name=hostname,
                first_occurrence=existing_plugin,
                second_occurrence=(f"active({service_data.plugin_name})", None),
            )
            continue

        used_descriptions[service_data.description] = (
            f"active({service_data.plugin_name})",
            service_data.description,
        )

        service_spec = {
            "use": "check_mk_perf,check_mk_default",
            "host_name": hostname,
            "service_description": service_data.description,
            "check_command": transform_active_service_command(cfg, service_data),
            "active_checks_enabled": str(1),
        }
        service_spec.update(
            core_config.get_service_attributes(
                config_cache,
                hostname,
                service_data.description,
                active_service_labels,
                extra_icon=None,
            )
        )
        service_spec.update(
            _extra_service_conf_of(
                cfg, config_cache, hostname, service_data.description, active_service_labels
            )
        )

        cfg.active_checks_to_define[service_data.plugin_name] = service_data.command[0]
        active_services.append(service_spec)

    active_checks_rules_exist = any(params for name, params in config_cache.active_checks(hostname))
    # Note: ^- This is not the same as `active_checks_present = bool(active_services)`
    # Services can be omitted, or rules can result in zero services (theoretically).
    # I am not sure if this is intentional.
    if active_checks_rules_exist:
        cfg.write("\n\n# Active checks\n")

        for service_spec in active_services:
            cfg.write(format_nagios_object("service", service_spec))
            license_counter["services"] += 1

            # write service dependencies for active checks
            cfg.write(get_dependencies(hostname, service_spec["service_description"]))

    # Legacy checks via custom_checks
    custchecks = config_cache.custom_checks(hostname)
    translations = config.get_service_translations(
        config_cache.ruleset_matcher,
        hostname,
    )
    if custchecks:
        cfg.write("\n\n# Custom checks\n")
        for entry in custchecks:
            # entries are dicts with the following keys:
            # "service_description"        Service name to use
            # "command_line"  (optional)   Unix command line for executing the check
            #                              If this is missing, we create a passive check
            # "command_name"  (optional)   Name of Monitoring command to define. If missing,
            #                              we use "check-mk-custom"
            description = config.get_final_service_description(
                entry["service_description"], translations
            )
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if not description:
                config_warnings.warn(
                    "Skipping invalid service with empty description on host %s" % hostname
                )
                continue

            if command_line:
                command_line = (
                    core_config.autodetect_plugin(command_line)
                    .replace("\\", "\\\\")
                    .replace("!", "\\!")
                )

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

            if description in used_descriptions:
                cn, _ = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one.
                if cn == "custom(%s)" % command_name:
                    continue

                core_config.duplicate_service_warning(
                    checktype="custom",
                    description=description,
                    host_name=hostname,
                    first_occurrence=used_descriptions[description],
                    second_occurrence=("custom(%s)" % command_name, description),
                )
                continue

            used_descriptions[description] = ("custom(%s)" % command_name, description)

            command = f"{command_name}!{command_line}"

            labels = config_cache.ruleset_matcher.labels_of_service(
                hostname, description, _NO_DISCOVERED_LABELS
            )

            service_spec = {
                "use": "check_mk_perf,check_mk_default",
                "host_name": hostname,
                "service_description": description,
                "check_command": _simulate_command(cfg, command),
                "active_checks_enabled": str(1 if (command_line and not freshness) else 0),
            }
            service_spec.update(freshness)
            service_spec.update(
                core_config.get_service_attributes(
                    config_cache, hostname, description, labels, extra_icon=None
                )
            )
            service_spec.update(
                _extra_service_conf_of(cfg, config_cache, hostname, description, labels)
            )
            cfg.write(format_nagios_object("service", service_spec))
            license_counter["services"] += 1

            # write service dependencies for custom checks
            cfg.write(get_dependencies(hostname, description))

    service_discovery_name = ConfigCache.service_discovery_name()

    # Inventory checks - if user has configured them.
    if not (disco_params := config_cache.discovery_check_parameters(hostname)).commandline_only:
        labels = config_cache.ruleset_matcher.labels_of_service(
            hostname, service_discovery_name, _NO_DISCOVERED_LABELS
        )
        service_spec = {
            "use": config.inventory_check_template,
            "host_name": hostname,
            "service_description": service_discovery_name,
        }

        service_spec.update(
            core_config.get_service_attributes(
                config_cache, hostname, service_discovery_name, labels, extra_icon=None
            )
        )

        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service_discovery_name, labels)
        )

        service_spec.update(
            {
                "check_interval": str(disco_params.check_interval),
                "retry_interval": str(disco_params.check_interval),
            }
        )

        cfg.write(format_nagios_object("service", service_spec))
        license_counter["services"] += 1

        if have_at_least_one_service:
            cfg.write(
                format_nagios_object(
                    "servicedependency",
                    {
                        "use": config.service_dependency_template,
                        "host_name": hostname,
                        "service_description": "Check_MK",
                        "dependent_host_name": hostname,
                        "dependent_service_description": service_discovery_name,
                    },
                )
            )

    # No check_mk service, no legacy service -> create PING service
    if not have_at_least_one_service and not active_checks_rules_exist and not custchecks:
        _add_ping_service(
            cfg,
            config_cache,
            hostname,
            "PING",
            config_cache.ruleset_matcher.labels_of_service(hostname, "PING", _NO_DISCOVERED_LABELS),
            host_attrs["address"],
            config_cache.default_address_family(hostname),
            host_attrs.get("_NODEIPS"),
            license_counter,
        )

    if ConfigCache.ip_stack_config(hostname) is IPStackConfig.DUAL_STACK:
        if config_cache.default_address_family(hostname) is socket.AF_INET6:
            if "PING IPv4" not in used_descriptions:
                _add_ping_service(
                    cfg,
                    config_cache,
                    hostname,
                    "PING IPv4",
                    config_cache.ruleset_matcher.labels_of_service(
                        hostname, "PING IPv4", _NO_DISCOVERED_LABELS
                    ),
                    host_attrs["address"],
                    socket.AF_INET,
                    host_attrs.get("_NODEIPS_4"),
                    license_counter,
                )
        elif "PING IPv6" not in used_descriptions:
            _add_ping_service(
                cfg,
                config_cache,
                hostname,
                "PING IPv6",
                config_cache.ruleset_matcher.labels_of_service(
                    hostname, "PING IPv6", _NO_DISCOVERED_LABELS
                ),
                host_attrs["address"],
                socket.AF_INET6,
                host_attrs.get("_NODEIPS_6"),
                license_counter,
            )

    return service_labels


def _add_ping_service(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    service_labels: Labels,
    ipaddress: HostAddress,
    family: socket.AddressFamily,
    node_ips: str | None,
    licensing_counter: Counter,
) -> None:
    arguments = core_config.check_icmp_arguments_of(config_cache, host_name, family=family)

    ping_command = "check-mk-ping"
    if host_name in config_cache.hosts_config.clusters:
        assert node_ips is not None
        arguments += " -m 1 " + node_ips
    else:
        arguments += " " + ipaddress

    service_spec = {
        "use": config.pingonly_template,
        "host_name": host_name,
        "service_description": service_name,
        "check_command": f"{ping_command}!{arguments}",
    }
    service_spec.update(
        core_config.get_service_attributes(
            config_cache, host_name, service_name, service_labels, extra_icon=None
        )
    )
    service_spec.update(
        _extra_service_conf_of(cfg, config_cache, host_name, service_name, service_labels)
    )
    cfg.write(format_nagios_object("service", service_spec))
    licensing_counter["services"] += 1


def format_nagios_object(object_type: str, object_spec: ObjectSpec) -> str:
    cfg = ["define %s {" % object_type]
    for key, val in sorted(object_spec.items(), key=lambda x: x[0]):
        # Use a base16 encoding for names and values of tags, labels and label
        # sources to work around the syntactic restrictions in Nagios' object
        # configuration files.
        if key[0] == "_":  # quick pre-check: custom variable?
            for prefix in ("__TAG_", "__LABEL_", "__LABELSOURCE_"):
                if key.startswith(prefix):
                    key = prefix + _b16encode(key[len(prefix) :])
                    val = _b16encode(val)
        cfg.append("  %-29s %s" % (key, val))
    cfg.append("}")

    return "\n".join(cfg) + "\n\n"


def _b16encode(b: str) -> str:
    return (base64.b16encode(b.encode())).decode()


def _simulate_command(cfg: NagiosConfig, command: CoreCommand) -> CoreCommand:
    if config.simulation_mode:
        cfg.custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"
    return command


def _create_nagios_config_hostgroups(cfg: NagiosConfig) -> None:
    if config.define_hostgroups:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Host groups (controlled by define_hostgroups)\n")
        cfg.write("# ------------------------------------------------------------\n")
        for hg in sorted(cfg.hostgroups_to_define):
            cfg.write(
                format_nagios_object(
                    "hostgroup",
                    {
                        "hostgroup_name": hg,
                        "alias": config.define_hostgroups.get(hg, hg),
                    },
                )
            )

    # No creation of host groups but we need to define default host group
    elif config.default_host_group in cfg.hostgroups_to_define:
        cfg.write(
            format_nagios_object(
                "hostgroup",
                {
                    "hostgroup_name": config.default_host_group,
                    "alias": "Check_MK default hostgroup",
                },
            )
        )


def _create_nagios_config_servicegroups(cfg: NagiosConfig) -> None:
    if not config.define_servicegroups:
        return
    cfg.write("\n# ------------------------------------------------------------\n")
    cfg.write("# Service groups (controlled by define_servicegroups)\n")
    cfg.write("# ------------------------------------------------------------\n")
    for sg in sorted(cfg.servicegroups_to_define):
        cfg.write(
            format_nagios_object(
                "servicegroup",
                {
                    "servicegroup_name": sg,
                    "alias": config.define_servicegroups.get(sg, sg),
                },
            )
        )


def _create_nagios_config_contactgroups(cfg: NagiosConfig) -> None:
    if not cfg.contactgroups_to_define:
        return
    cfg.write("\n# ------------------------------------------------------------\n")
    cfg.write("# Contact groups (controlled by define_contactgroups)\n")
    cfg.write("# ------------------------------------------------------------\n\n")
    for name in sorted(cfg.contactgroups_to_define):
        contactgroup_spec = {
            "contactgroup_name": name,
            "alias": config.define_contactgroups.get(name, name),
        }
        if members := config.contactgroup_members.get(name):
            contactgroup_spec["members"] = ",".join(members)
        cfg.write(format_nagios_object("contactgroup", contactgroup_spec))


def create_nagios_config_commands(cfg: NagiosConfig) -> None:
    if config.generate_dummy_commands:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Dummy check commands and active check commands\n")
        cfg.write("# ------------------------------------------------------------\n\n")
        for checkname in cfg.checknames_to_define:
            cfg.write(
                format_nagios_object(
                    "command",
                    {
                        "command_name": "check_mk-%s" % checkname,
                        "command_line": config.dummy_check_commandline,
                    },
                )
            )

    # active_checks
    for acttype, detected_executable in cfg.active_checks_to_define.items():
        cfg.write(
            format_nagios_object(
                "command",
                {
                    "command_name": f"check_mk_active-{acttype}",
                    "command_line": f"{detected_executable} $ARG1$",
                },
            )
        )

    # custom_checks
    for command_name in cfg.custom_commands_to_define:
        cfg.write(
            format_nagios_object(
                "command",
                {
                    "command_name": command_name,
                    "command_line": "$ARG1$",
                },
            )
        )

    # custom host checks
    for command_name, command_line in cfg.hostcheck_commands_to_define:
        cfg.write(
            format_nagios_object(
                "command",
                {
                    "command_name": command_name,
                    "command_line": command_line,
                },
            )
        )


def _create_nagios_config_timeperiods(cfg: NagiosConfig) -> None:
    if len(config.timeperiods) > 0:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Timeperiod definitions (controlled by variable 'timeperiods')\n")
        cfg.write("# ------------------------------------------------------------\n\n")
        tpnames = sorted(config.timeperiods)
        for name in tpnames:
            tp = config.timeperiods[name]
            timeperiod_spec = {
                "timeperiod_name": name,
            }

            if "alias" in tp:
                alias = tp["alias"]
                assert isinstance(alias, str)
                timeperiod_spec["alias"] = alias

            for key, value in tp.items():
                if key not in ["alias", "exclude"]:
                    # TODO: We should *really* improve TimeperiodSpec: We have no way to use assert
                    # below to distinguish between a list of TimeperiodNames for "exclude" and the
                    # list of tuples for the time ranges.
                    times = ",".join(
                        (f"{fr}-{to}") for (fr, to) in cast(list[tuple[str, str]], value)
                    )
                    if times:
                        timeperiod_spec[key] = times

            if "exclude" in tp:
                timeperiod_spec["exclude"] = ",".join(tp["exclude"])

            cfg.write(format_nagios_object("timeperiod", timeperiod_spec))


def _create_nagios_config_contacts(cfg: NagiosConfig, hostnames: Sequence[HostName]) -> None:
    if config.contacts:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Contact definitions (controlled by variable 'contacts')\n")
        cfg.write("# ------------------------------------------------------------\n\n")
        for cname, contact in sorted(config.contacts.items()):
            # Create contact groups in nagios, even when they are empty. This is needed
            # for RBN to work correctly when using contactgroups as recipients which are
            # not assigned to any host
            cfg.contactgroups_to_define.update(contact.get("contactgroups", []))
            # If the contact is in no contact group or all of the contact groups
            # of the contact have neither hosts nor services assigned - in other
            # words if the contact is not assigned to any host or service, then
            # we do not create this contact in Nagios. It's useless and will produce
            # warnings.
            cgrs = [
                cgr
                for cgr in contact.get("contactgroups", [])
                if cgr in cfg.contactgroups_to_define
            ]
            if not cgrs:
                continue

            contact_spec: ObjectSpec = {
                "contact_name": cname,
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
                        "%s_notification_options" % what: ",".join(no),
                        "%s_notification_period" % what: contact.get("notification_period", "24X7"),
                        "%s_notification_commands" % what: contact.get(
                            "%s_notification_commands" % what, "check-mk-notify"
                        ),
                    }
                )

            # Add custom macros
            contact_spec.update({key: val for key, val in contact.items() if key.startswith("_")})

            contact_spec["contactgroups"] = ", ".join(cgrs)
            cfg.write(format_nagios_object("contact", contact_spec))

    if hostnames:
        cfg.contactgroups_to_define.add("check-mk-notify")
        cfg.write("# Needed for rule based notifications\n")
        cfg.write(
            format_nagios_object(
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
        )


def _quote_nagios_string(s: str) -> str:
    """Quote string for use in a nagios command execution.  Please note that also
    quoting for ! and backslash for Nagios itself takes place here."""
    return "'" + s.replace("\\", "\\\\").replace("'", "'\"'\"'").replace("!", "\\!") + "'"


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
        service_spec["contact_groups"] = ",".join(sercgr)
        cfg.contactgroups_to_define.update(sercgr)

    sergr = config_cache.servicegroups_of_service(host_name, service_name, service_labels)
    if sergr:
        service_spec["service_groups"] = ",".join(sergr)
        if config.define_servicegroups:
            cfg.servicegroups_to_define.update(sergr)

    return service_spec
