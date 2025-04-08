#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for support of Nagios (and compatible) cores"""

import base64
import itertools
import os
import py_compile
import socket
import sys
from collections import Counter
from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import Any, cast, IO, Literal

import cmk.utils.config_path
import cmk.utils.paths
from cmk.utils import config_warnings, password_store, store, tty
from cmk.utils.check_utils import section_name_of
from cmk.utils.config_path import LATEST_CONFIG, VersionedConfigPath
from cmk.utils.escaping import escape_command_args
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostAddress, HostName, Hosts
from cmk.utils.labels import Labels
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.servicename import MAX_SERVICE_NAME_LEN, ServiceName
from cmk.utils.store.host_storage import ContactgroupName
from cmk.utils.timeperiod import TimeperiodName

from cmk.checkengine.checking import CheckPluginName, CheckPluginNameStr
from cmk.checkengine.inventory import InventoryPluginName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
import cmk.base.server_side_calls as server_side_calls
import cmk.base.utils
from cmk.base.config import (
    ConfigCache,
    HostgroupName,
    ObjectAttributes,
    ServicegroupName,
)
from cmk.base.core_config import (
    AbstractServiceID,
    CollectedHostLabels,
    CoreCommand,
    CoreCommandName,
    get_labels_from_attributes,
    write_notify_host_file,
)
from cmk.base.ip_lookup import AddressFamily

from cmk.discover_plugins import PluginLocation

ObjectSpec = dict[str, Any]


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
        licensing_handler: LicensingHandler,
        passwords: Mapping[str, str],
        hosts_to_update: set[HostName] | None = None,
    ) -> None:
        self._create_core_config(config_path, licensing_handler, passwords)
        self._precompile_hostchecks(config_path)

    def _create_core_config(
        self,
        config_path: VersionedConfigPath,
        licensing_handler: LicensingHandler,
        passwords: Mapping[str, str],
    ) -> None:
        """Tries to create a new Checkmk object configuration file for the Nagios core

        During create_config() exceptions may be raised which are caused by configuration issues.
        Don't produce a half written object file. Simply throw away everything and keep the old file.

        The user can then start the site with the old configuration and fix the configuration issue
        while the monitoring is running.
        """

        config_buffer = StringIO()
        create_config(
            config_buffer,
            config_path,
            hostnames=None,
            licensing_handler=licensing_handler,
            passwords=passwords,
        )

        store.save_text_to_file(cmk.utils.paths.nagios_objects_file, config_buffer.getvalue())

    def _precompile_hostchecks(self, config_path: VersionedConfigPath) -> None:
        out.output("Precompiling host checks...")
        _precompile_hostchecks(config_path)
        out.output(tty.ok + "\n")


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
    def __init__(self, outfile: IO[str], hostnames: list[HostName] | None) -> None:
        super().__init__()
        self._outfile = outfile
        self.hostnames = hostnames

        self.hostgroups_to_define: set[HostgroupName] = set()
        self.servicegroups_to_define: set[ServicegroupName] = set()
        self.contactgroups_to_define: set[ContactgroupName] = set()
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
    hostnames: list[HostName] | None,
    licensing_handler: LicensingHandler,
    passwords: Mapping[str, str],
) -> None:
    if config.host_notification_periods:
        config_warnings.warn(
            "host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead."
        )

    if config.service_notification_periods:
        config_warnings.warn(
            "service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead."
        )

    # Map service_period to _SERVICE_PERIOD. This field does not exist in Nagios.
    # The CMC has this field natively.
    if "service_period" in config.extra_host_conf:
        config.extra_host_conf["_SERVICE_PERIOD"] = config.extra_host_conf["service_period"]
        del config.extra_host_conf["service_period"]
    if "service_period" in config.extra_service_conf:
        config.extra_service_conf["_SERVICE_PERIOD"] = config.extra_service_conf["service_period"]
        del config.extra_service_conf["service_period"]

    config_cache = config.get_config_cache()

    if hostnames is None:
        hosts_config = config_cache.hosts_config
        hostnames = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )
    else:
        hostnames = sorted(hostnames)

    cfg = NagiosConfig(outfile, hostnames)

    _output_conf_header(cfg)

    licensing_counter = Counter("services")
    all_host_labels: dict[HostName, CollectedHostLabels] = {}
    for hostname in hostnames:
        all_host_labels[hostname] = _create_nagios_config_host(
            cfg, config_cache, hostname, passwords, licensing_counter
        )

    _validate_licensing(config_cache.hosts_config, licensing_handler, licensing_counter)

    write_notify_host_file(config_path, all_host_labels)

    _create_nagios_config_contacts(cfg, hostnames)
    _create_nagios_config_hostgroups(cfg)
    _create_nagios_config_servicegroups(cfg)
    _create_nagios_config_contactgroups(cfg)
    _create_nagios_config_commands(cfg)
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
) -> CollectedHostLabels:
    cfg.write("\n# ----------------------------------------------------\n")
    cfg.write("# %s\n" % hostname)
    cfg.write("# ----------------------------------------------------\n")

    host_attrs = config_cache.get_host_attributes(hostname)
    if config.generate_hostconf:
        host_spec = _create_nagios_host_spec(cfg, config_cache, hostname, host_attrs)
        cfg.write(_format_nagios_object("host", host_spec))

    return CollectedHostLabels(
        host_labels=get_labels_from_attributes(list(host_attrs.items())),
        service_labels=_create_nagios_servicedefs(
            cfg, config_cache, hostname, host_attrs, stored_passwords, license_counter
        ),
    )


def _create_nagios_host_spec(  # pylint: disable=too-many-branches
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    attrs: ObjectAttributes,
) -> ObjectSpec:
    ip = attrs["address"]

    if hostname in config_cache.hosts_config.clusters:
        nodes = config_cache.get_cluster_nodes_for_config(hostname)
        attrs.update(config_cache.get_cluster_attributes(hostname, nodes))

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


def transform_active_service_command(
    cfg: NagiosConfig, service_data: server_side_calls.ActiveServiceData
) -> str:
    if config.simulation_mode:
        cfg.custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"

    if service_data.command == "check-mk-custom":
        cfg.custom_commands_to_define.add("check-mk-custom")
        return f"{service_data.command}!{service_data.command_line}"

    return service_data.command_display


def _create_nagios_servicedefs(  # pylint: disable=too-many-branches
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    host_attrs: ObjectAttributes,
    stored_passwords: Mapping[str, str],
    license_counter: Counter,
) -> dict[ServiceName, Labels]:
    check_mk_attrs = core_config.get_service_attributes(hostname, "Check_MK", config_cache)

    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services

    def do_omit_service(hostname: HostName, description: ServiceName) -> bool:
        if config_cache.service_ignored(hostname, description):
            return True
        if hostname != config_cache.effective_host(hostname, description):
            return True
        return False

    def get_dependencies(hostname: HostName, servicedesc: ServiceName) -> str:
        result = ""
        for dep in config.service_depends_on(config_cache, hostname, servicedesc):
            result += _format_nagios_object(
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

        passive_service_attributes = core_config.get_cmk_passive_service_attributes(
            config_cache, hostname, service, check_mk_attrs
        )

        service_labels[service.description] = {
            label.name: label.value for label in service.service_labels.values()
        } | dict(get_labels_from_attributes(list(passive_service_attributes.items())))

        service_spec.update(passive_service_attributes)

        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service.description)
        )

        cfg.write(_format_nagios_object("service", service_spec))
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
        service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname, "Check_MK"))
        cfg.write(_format_nagios_object("service", service_spec))
        license_counter["services"] += 1

    # legacy checks via active_checks
    active_services = []

    translations = config.get_service_translations(config_cache.ruleset_matcher, hostname)
    host_macros = ConfigCache.get_host_macros_from_attributes(hostname, host_attrs)
    resource_macros = config.get_resource_macros()
    macros = {**host_macros, **resource_macros}
    active_check_config = server_side_calls.ActiveCheck(
        server_side_calls.load_active_checks()[1],
        config.active_check_info,
        hostname,
        config.get_ssc_host_config(hostname, config_cache, macros),
        host_attrs,
        config.http_proxies,
        lambda x: config.get_final_service_description(x, translations),
        config.use_new_descriptions_for,
        stored_passwords,
        password_store.core_password_store_path(LATEST_CONFIG),
        escape_func=lambda a: escape_command_args(a.replace("\\", "\\\\")),
    )

    active_checks = config_cache.active_checks(hostname)
    actchecks = [name for name, params in active_checks if params]
    for service_data in active_check_config.get_active_service_data(active_checks):
        if do_omit_service(hostname, service_data.description):
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

        service_attributes = core_config.get_service_attributes(
            hostname, service_data.description, config_cache
        )

        service_labels[service_data.description] = dict(
            get_labels_from_attributes(list(service_attributes.items()))
        )

        service_spec.update(service_attributes)

        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service_data.description)
        )

        cfg.active_checks_to_define[service_data.plugin_name] = service_data.detected_executable
        active_services.append(service_spec)

    if actchecks:
        cfg.write("\n\n# Active checks\n")

        for service_spec in active_services:
            cfg.write(_format_nagios_object("service", service_spec))
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
            # "service_description"        Service description to use
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
                command_line = escape_command_args(
                    core_config.autodetect_plugin(command_line).replace("\\", "\\\\")
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

            service_spec = {
                "use": "check_mk_perf,check_mk_default",
                "host_name": hostname,
                "service_description": description,
                "check_command": _simulate_command(cfg, command),
                "active_checks_enabled": str(1 if (command_line and not freshness) else 0),
            }
            service_spec.update(freshness)
            service_spec.update(
                core_config.get_service_attributes(hostname, description, config_cache)
            )
            service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname, description))
            cfg.write(_format_nagios_object("service", service_spec))
            license_counter["services"] += 1

            # write service dependencies for custom checks
            cfg.write(get_dependencies(hostname, description))

    service_discovery_name = ConfigCache.service_discovery_name()

    # Inventory checks - if user has configured them.
    if not (disco_params := config_cache.discovery_check_parameters(hostname)).commandline_only:
        service_spec = {
            "use": config.inventory_check_template,
            "host_name": hostname,
            "service_description": service_discovery_name,
        }
        service_spec.update(
            core_config.get_service_attributes(hostname, service_discovery_name, config_cache)
        )

        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service_discovery_name)
        )

        service_spec.update(
            {
                "check_interval": str(disco_params.check_interval),
                "retry_interval": str(disco_params.check_interval),
            }
        )

        cfg.write(_format_nagios_object("service", service_spec))
        license_counter["services"] += 1

        if have_at_least_one_service:
            cfg.write(
                _format_nagios_object(
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
    if not have_at_least_one_service and not actchecks and not custchecks:
        _add_ping_service(
            cfg,
            config_cache,
            hostname,
            host_attrs["address"],
            config_cache.default_address_family(hostname),
            "PING",
            host_attrs.get("_NODEIPS"),
            license_counter,
        )

    if ConfigCache.address_family(hostname) is AddressFamily.DUAL_STACK:
        if config_cache.default_address_family(hostname) is socket.AF_INET6:
            if "PING IPv4" not in used_descriptions:
                _add_ping_service(
                    cfg,
                    config_cache,
                    hostname,
                    host_attrs["_ADDRESS_4"],
                    socket.AF_INET,
                    "PING IPv4",
                    host_attrs.get("_NODEIPS_4"),
                    license_counter,
                )
        else:
            if "PING IPv6" not in used_descriptions:
                _add_ping_service(
                    cfg,
                    config_cache,
                    hostname,
                    host_attrs["_ADDRESS_6"],
                    socket.AF_INET6,
                    "PING IPv6",
                    host_attrs.get("_NODEIPS_6"),
                    license_counter,
                )

    return service_labels


def _add_ping_service(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    host_name: HostName,
    ipaddress: HostAddress,
    family: socket.AddressFamily,
    descr: ServiceName,
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
        "service_description": descr,
        "check_command": f"{ping_command}!{arguments}",
    }
    service_spec.update(core_config.get_service_attributes(host_name, descr, config_cache))
    service_spec.update(_extra_service_conf_of(cfg, config_cache, host_name, descr))
    cfg.write(_format_nagios_object("service", service_spec))
    licensing_counter["services"] += 1


def _format_nagios_object(object_type: str, object_spec: ObjectSpec) -> str:
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
                _format_nagios_object(
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
            _format_nagios_object(
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
            _format_nagios_object(
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
        cfg.write(_format_nagios_object("contactgroup", contactgroup_spec))


def _create_nagios_config_commands(cfg: NagiosConfig) -> None:
    if config.generate_dummy_commands:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Dummy check commands and active check commands\n")
        cfg.write("# ------------------------------------------------------------\n\n")
        for checkname in cfg.checknames_to_define:
            cfg.write(
                _format_nagios_object(
                    "command",
                    {
                        "command_name": "check_mk-%s" % checkname,
                        "command_line": config.dummy_check_commandline,
                    },
                )
            )

    # active_checks
    for acttype, detected_executable in cfg.active_checks_to_define.items():
        command_line = (
            core_config.autodetect_plugin(act_info["command_line"])
            if (act_info := config.active_check_info.get(acttype)) is not None
            else f"{detected_executable} $ARG1$"
        )
        cfg.write(
            _format_nagios_object(
                "command",
                {
                    "command_name": f"check_mk_active-{acttype}",
                    "command_line": command_line,
                },
            )
        )

    # custom_checks
    for command_name in cfg.custom_commands_to_define:
        cfg.write(
            _format_nagios_object(
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
            _format_nagios_object(
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
                timeperiod_spec["exclude"] = ",".join(cast(list[TimeperiodName], tp["exclude"]))

            cfg.write(_format_nagios_object("timeperiod", timeperiod_spec))


def _create_nagios_config_contacts(cfg: NagiosConfig, hostnames: list[HostName]) -> None:
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
            cfg.write(_format_nagios_object("contact", contact_spec))

    if hostnames:
        cfg.contactgroups_to_define.add("check-mk-notify")
        cfg.write("# Needed for rule based notifications\n")
        cfg.write(
            _format_nagios_object(
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
    return "'" + escape_command_args(s.replace("\\", "\\\\").replace("'", "'\"'\"'")) + "'"


def _extra_service_conf_of(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    hostname: HostName,
    description: ServiceName,
) -> ObjectSpec:
    """Collect all extra configuration data for a service"""
    service_spec: ObjectSpec = {}

    # Add contact groups to the config only if the user has defined them.
    # Otherwise inherit the contact groups from the host.
    # "check-mk-notify" is always returned for rulebased notifications and
    # the Nagios core and not defined by the user.
    sercgr = config_cache.contactgroups_of_service(hostname, description)
    if sercgr != ["check-mk-notify"]:
        service_spec["contact_groups"] = ",".join(sercgr)
        cfg.contactgroups_to_define.update(sercgr)

    sergr = config_cache.servicegroups_of_service(hostname, description)
    if sergr:
        service_spec["service_groups"] = ",".join(sergr)
        if config.define_servicegroups:
            cfg.servicegroups_to_define.update(sergr)

    return service_spec


# .
#   .--Precompile----------------------------------------------------------.
#   |          ____                                     _ _                |
#   |         |  _ \ _ __ ___  ___ ___  _ __ ___  _ __ (_) | ___           |
#   |         | |_) | '__/ _ \/ __/ _ \| '_ ` _ \| '_ \| | |/ _ \          |
#   |         |  __/| | |  __/ (_| (_) | | | | | | |_) | | |  __/          |
#   |         |_|   |_|  \___|\___\___/|_| |_| |_| .__/|_|_|\___|          |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Precompiling creates on dedicated Python file per host, which just   |
#   | contains that code and information that is needed for executing all  |
#   | checks of that host. Also static data that cannot change during the  |
#   | normal monitoring process is being precomputed and hard coded. This  |
#   | all saves substantial CPU resources as opposed to running Checkmk    |
#   | in adhoc mode (about 75%).                                           |
#   '----------------------------------------------------------------------'


def _find_check_plugins(checktype: CheckPluginNameStr) -> set[str]:
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

        console.verbose(" ==> %s.\n", compiled_filename, stream=sys.stderr)


def _precompile_hostchecks(config_path: VersionedConfigPath) -> None:
    console.verbose("Creating precompiled host check config...\n")
    config_cache = config.get_config_cache()
    hosts_config = config_cache.hosts_config

    config.save_packed_config(config_path, config_cache)

    console.verbose("Precompiling host checks...\n")

    host_check_store = HostCheckStore()
    for hostname in {
        # Inconsistent with `create_config` above.
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    }:
        try:
            console.verbose(
                "%s%s%-16s%s:",
                tty.bold,
                tty.blue,
                hostname,
                tty.normal,
                stream=sys.stderr,
            )
            host_check = _dump_precompiled_hostcheck(
                config_cache,
                config_path,
                hostname,
            )

            host_check_store.write(config_path, hostname, host_check)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error(f"Error precompiling checks for host {hostname}: {e}\n")
            sys.exit(5)


def _dump_precompiled_hostcheck(  # pylint: disable=too-many-branches
    config_cache: ConfigCache,
    config_path: VersionedConfigPath,
    hostname: HostName,
    *,
    verify_site_python: bool = True,
) -> str:
    (
        needed_legacy_check_plugin_names,
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    ) = _get_needed_plugin_names(config_cache, hostname)

    if hostname in config_cache.hosts_config.clusters:
        nodes = config_cache.nodes_of(hostname)
        if nodes is None:
            raise TypeError()

        for node in nodes:
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

    output = StringIO()
    output.write("#!/usr/bin/env python3\n")
    output.write("# encoding: utf-8\n\n")

    output.write("import logging\n")
    output.write("import sys\n\n")

    if verify_site_python:
        output.write("if not sys.executable.startswith('/omd'):\n")
        output.write('    sys.stdout.write("ERROR: Only executable with sites python\\n")\n')
        output.write("    sys.exit(2)\n\n")

    # Self-compile: replace symlink with precompiled python-code, if
    # we are run for the first time
    if config.delay_precompile:
        output.write(
            """
import os
if os.path.islink(%(dst)r):
    import py_compile
    os.remove(%(dst)r)
    py_compile.compile(%(src)r, %(dst)r, %(dst)r, True)
    os.chmod(%(dst)r, 0o700)

"""
            % {
                "src": str(HostCheckStore.host_check_source_file_path(config_path, hostname)),
                "dst": str(HostCheckStore.host_check_file_path(config_path, hostname)),
            }
        )

    # Remove precompiled directory from sys.path. Leaving it in the path
    # makes problems when host names (name of precompiled files) are equal
    # to python module names like "random"
    output.write("sys.path.pop(0)\n")

    output.write("import cmk.utils.log\n")
    output.write("import cmk.utils.debug\n")
    output.write("from cmk.utils.exceptions import MKTerminate\n")
    output.write("from cmk.utils.config_path import LATEST_CONFIG\n")
    output.write("\n")
    output.write("import cmk.base.utils\n")
    output.write("import cmk.base.config as config\n")
    output.write("from cmk.discover_plugins import PluginLocation\n")
    output.write("import cmk.base.obsolete_output as out\n")
    output.write("from cmk.base.api.agent_based.register import register_plugin_by_type\n")
    output.write("import cmk.base.check_api as check_api\n")
    output.write("import cmk.base.ip_lookup as ip_lookup\n")  # is this still needed?
    output.write("from cmk.checkengine.submitters import get_submitter\n")
    output.write("\n")

    locations = _get_needed_agent_based_locations(
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    )
    for module in {l.module for l in locations}:
        output.write("import %s\n" % module)
        console.verbose(" %s%s%s", tty.green, module, tty.normal, stream=sys.stderr)
    for location in (l for l in locations if l.name is not None):
        output.write(f"register_plugin_by_type({location!r}, {location.module}.{location.name})\n")

    # Register default Checkmk signal handler
    output.write("cmk.base.utils.register_sigint_handler()\n")

    # initialize global variables
    output.write(
        """
# very simple commandline parsing: only -v (once or twice) and -d are supported

cmk.utils.log.setup_console_logging()
logger = logging.getLogger("cmk.base")

# TODO: This is not really good parsing, because it not cares about syntax like e.g. "-nv".
#       The later regular argument parsing is handling this correctly. Try to clean this up.
cmk.utils.log.logger.setLevel(cmk.utils.log.verbosity_to_log_level(len([ a for a in sys.argv if a in [ "-v", "--verbose"] ])))

if '-d' in sys.argv:
    cmk.utils.debug.enable()

"""
    )

    file_list = sorted(_get_legacy_check_file_names_to_load(needed_legacy_check_plugin_names))
    formatted_file_list = (
        "\n    %s,\n" % ",\n    ".join("%r" % n for n in file_list) if file_list else ""
    )
    output.write(
        "config.load_checks(check_api.get_check_api_context, [%s])\n" % formatted_file_list
    )

    for check_plugin_name in sorted(needed_legacy_check_plugin_names):
        console.verbose(" %s%s%s", tty.green, check_plugin_name, tty.normal, stream=sys.stderr)

    output.write("config.load_packed_config(LATEST_CONFIG)\n")

    # IP addresses
    (
        needed_ipaddresses,
        needed_ipv6addresses,
    ) = (
        {},
        {},
    )
    if hostname in config_cache.hosts_config.clusters:
        nodes = config_cache.nodes_of(hostname)
        if nodes is None:
            raise TypeError()

        for node in nodes:
            if AddressFamily.IPv4 in ConfigCache.address_family(node):
                needed_ipaddresses[node] = config.lookup_ip_address(
                    config_cache, node, family=socket.AF_INET
                )

            if AddressFamily.IPv6 in ConfigCache.address_family(node):
                needed_ipv6addresses[node] = config.lookup_ip_address(
                    config_cache, node, family=socket.AF_INET6
                )

        try:
            if AddressFamily.IPv4 in ConfigCache.address_family(hostname):
                needed_ipaddresses[hostname] = config.lookup_ip_address(
                    config_cache, hostname, family=socket.AF_INET
                )
        except Exception:
            pass

        try:
            if AddressFamily.IPv6 in ConfigCache.address_family(hostname):
                needed_ipv6addresses[hostname] = config.lookup_ip_address(
                    config_cache, hostname, family=socket.AF_INET6
                )
        except Exception:
            pass
    else:
        if AddressFamily.IPv4 in ConfigCache.address_family(hostname):
            needed_ipaddresses[hostname] = config.lookup_ip_address(
                config_cache, hostname, family=socket.AF_INET
            )

        if AddressFamily.IPv6 in ConfigCache.address_family(hostname):
            needed_ipv6addresses[hostname] = config.lookup_ip_address(
                config_cache, hostname, family=socket.AF_INET6
            )

    output.write("config.ipaddresses = %r\n\n" % needed_ipaddresses)
    output.write("config.ipv6addresses = %r\n\n" % needed_ipv6addresses)
    output.write("try:\n")
    output.write("    # mode_check is `mode --check hostname`\n")
    output.write("    from cmk.base.modes.check_mk import mode_check\n")
    output.write("    sys.exit(\n")
    output.write("        mode_check(\n")
    output.write("            get_submitter,\n")
    output.write("            {},\n")
    output.write(f"           [{hostname!r}],\n")
    output.write("            active_check_handler=lambda *args: None,\n")
    output.write("            keepalive=False,\n")
    output.write("            precompiled_host_check=True,\n")
    output.write("        )\n")
    output.write("    )\n")
    output.write("except MKTerminate:\n")
    output.write("    out.output('<Interrupted>\\n', stream=sys.stderr)\n")
    output.write("    sys.exit(1)\n")
    output.write("except SystemExit as e:\n")
    output.write("    sys.exit(e.code)\n")
    output.write("except Exception as e:\n")
    output.write("    import traceback, pprint\n")

    # status output message
    output.write(
        '    sys.stdout.write("UNKNOWN - Exception in precompiled check: %s (details in long output)\\n" % e)\n'
    )

    # generate traceback for long output
    output.write('    sys.stdout.write("Traceback: %s\\n" % traceback.format_exc())\n')

    output.write("\n")
    output.write("    sys.exit(3)\n")

    return output.getvalue()


def _get_needed_plugin_names(
    config_cache: ConfigCache, host_name: HostName
) -> tuple[set[CheckPluginNameStr], set[CheckPluginName], set[InventoryPluginName]]:
    ssc_api_special_agents = {p.name for p in server_side_calls.load_special_agents()[1].values()}
    needed_legacy_check_plugin_names = {
        name
        for name, _p in config_cache.special_agents(host_name)
        if name not in ssc_api_special_agents
    }

    # Collect the needed check plugin names using the host check table.
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


def _resolve_legacy_plugin_name(
    check_plugin_name: CheckPluginName,
) -> CheckPluginNameStr | None:
    legacy_name = config.legacy_check_plugin_names.get(check_plugin_name)
    if legacy_name:
        return legacy_name

    if not check_plugin_name.is_management_name():
        return None

    # See if me must include a legacy plugin from which we derived the given one:
    # A management plugin *could have been* created on the fly, from a 'regular' legacy
    # check plugin. In this case, we must load that.
    plugin = agent_based_register.get_check_plugin(check_plugin_name)
    if not plugin or plugin.location is not None:
        # it does *not* result from a legacy plugin, if module is not None
        return None

    # just try to get the legacy name of the 'regular' plugin:
    return config.legacy_check_plugin_names.get(check_plugin_name.create_basic_name())


def _get_legacy_check_file_names_to_load(
    needed_check_plugin_names: set[CheckPluginNameStr],
) -> set[str]:
    # check info table
    # We need to include all those plugins that are referenced in the hosts
    # check table.
    filenames: set[str] = set()

    for check_plugin_name in needed_check_plugin_names:
        # Now add check file(s) itself
        paths = _find_check_plugins(check_plugin_name)

        filenames |= paths

    return filenames


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
    new style plugin may have a dependency to a legacy check
    """
    required_legacy_check_sections = set()
    for section in agent_based_register.get_relevant_raw_sections(
        check_plugin_names=check_plugin_names,
        inventory_plugin_names=inventory_plugin_names,
    ).values():
        if section.location is None:
            required_legacy_check_sections.add(str(section.name))
    return required_legacy_check_sections
