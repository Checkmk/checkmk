#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for support of Nagios (and compatible) cores"""

import base64
import os
import py_compile
import socket
import sys
from io import StringIO
from pathlib import Path
from typing import Any, cast, Dict, IO, Iterable, List, Optional, Set, Tuple, Union

import cmk.utils.config_path
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.check_utils import section_name_of
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    ContactgroupName,
    HostAddress,
    HostgroupName,
    HostName,
    HostsToUpdate,
    InventoryPluginName,
    Item,
    ServicegroupName,
    ServiceName,
    TimeperiodName,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
import cmk.base.plugin_contexts as plugin_contexts
import cmk.base.sources as sources
import cmk.base.utils
from cmk.base.check_utils import ServiceID
from cmk.base.config import ConfigCache, HostConfig, ObjectAttributes
from cmk.base.core_config import CoreCommand, CoreCommandName

ObjectSpec = Dict[str, Any]

ActiveServiceID = Tuple[str, Item]  # TODO: I hope the str someday (tm) becomes "CheckPluginName",
CustomServiceID = Tuple[str, Item]  # #     at which point these will be the same as "ServiceID"
AbstractServiceID = Union[ActiveServiceID, CustomServiceID, ServiceID]

CHECK_INFO_BY_MIGRATED_NAME = {
    k: config.check_info[v] for k, v in config.legacy_check_plugin_names.items()
}


class NagiosCore(core_config.MonitoringCore):
    @classmethod
    def name(cls) -> str:
        return "nagios"

    def create_config(
        self,
        config_path: VersionedConfigPath,
        config_cache: ConfigCache,
        hosts_to_update: HostsToUpdate = None,
    ) -> None:
        self._create_core_config()
        self._precompile_hostchecks(config_path)

    def _create_core_config(self) -> None:
        """Tries to create a new Checkmk object configuration file for the Nagios core

        During create_config() exceptions may be raised which are caused by configuration issues.
        Don't produce a half written object file. Simply throw away everything and keep the old file.

        The user can then start the site with the old configuration and fix the configuration issue
        while the monitoring is running.
        """
        config_buffer = StringIO()
        create_config(config_buffer, hostnames=None)

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
    def __init__(self, outfile: IO[str], hostnames: Optional[List[HostName]]) -> None:
        super().__init__()
        self._outfile = outfile
        self.hostnames = hostnames

        self.hostgroups_to_define: Set[HostgroupName] = set()
        self.servicegroups_to_define: Set[ServicegroupName] = set()
        self.contactgroups_to_define: Set[ContactgroupName] = set()
        self.checknames_to_define: Set[CheckPluginName] = set()
        self.active_checks_to_define: Set[CheckPluginNameStr] = set()
        self.custom_commands_to_define: Set[CoreCommandName] = set()
        self.hostcheck_commands_to_define: List[Tuple[CoreCommand, str]] = []

    def write(self, x: str) -> None:
        # TODO: Something seems to be mixed up in our call sites...
        self._outfile.write(x)


def create_config(outfile: IO[str], hostnames: Optional[List[HostName]]) -> None:
    if config.host_notification_periods != []:
        core_config.warning(
            "host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead."
        )

    if config.service_notification_periods != []:
        core_config.warning(
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
        hostnames = list(config_cache.all_active_hosts())

    cfg = NagiosConfig(outfile, hostnames)

    _output_conf_header(cfg)

    for hostname in sorted(hostnames):
        _create_nagios_config_host(cfg, config_cache, hostname)

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
    cfg: NagiosConfig, config_cache: ConfigCache, hostname: HostName
) -> None:
    cfg.write("\n# ----------------------------------------------------\n")
    cfg.write("# %s\n" % hostname)
    cfg.write("# ----------------------------------------------------\n")
    host_attrs = core_config.get_host_attributes(hostname, config_cache)
    if config.generate_hostconf:
        host_spec = _create_nagios_host_spec(cfg, config_cache, hostname, host_attrs)
        cfg.write(_format_nagios_object("host", host_spec))
    _create_nagios_servicedefs(cfg, config_cache, hostname, host_attrs)


def _create_nagios_host_spec(
    cfg: NagiosConfig, config_cache: ConfigCache, hostname: HostName, attrs: ObjectAttributes
) -> ObjectSpec:
    host_config = config_cache.get_host_config(hostname)

    ip = attrs["address"]

    if host_config.is_cluster:
        nodes = core_config.get_cluster_nodes_for_config(config_cache, host_config)
        attrs.update(core_config.get_cluster_attributes(config_cache, host_config, nodes))

    #   _
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    host_spec = {
        "host_name": hostname,
        "use": config.cluster_template if host_config.is_cluster else config.host_template,
        "address": ip if ip else ip_lookup.fallback_ip_for(host_config.default_address_family),
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
            {"$HOSTNAME$": host_config.hostname},
        )
        cfg.hostcheck_commands_to_define.append(
            (
                command,
                'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$'
                % (
                    host_config.hostname,
                    service_with_hostname,
                    host_config.hostname,
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
        config_cache,  #
        host_config,
        ip,
        host_config.is_cluster,
        "ping",
        host_check_via_service_status,
        host_check_via_custom_check,
    )
    if command:
        host_spec["check_command"] = command

    hostgroups = host_config.hostgroups
    if config.define_hostgroups or hostgroups == [config.default_host_group]:
        cfg.hostgroups_to_define.update(hostgroups)
    host_spec["hostgroups"] = ",".join(hostgroups)

    # Contact groups
    contactgroups = host_config.contactgroups
    if contactgroups:
        host_spec["contact_groups"] = ",".join(contactgroups)
        cfg.contactgroups_to_define.update(contactgroups)

    if not host_config.is_cluster:
        # Parents for non-clusters

        # Get parents explicitly defined for host/folder via extra_host_conf["parents"]. Only honor
        # the ruleset "parents" in case no explicit parents are set
        if not attrs.get("parents", []):
            parents_list = host_config.parents
            if parents_list:
                host_spec["parents"] = ",".join(parents_list)

    elif host_config.is_cluster:
        # Special handling of clusters
        host_spec["parents"] = ",".join(nodes)

    # Custom configuration last -> user may override all other values
    # TODO: Find a generic mechanism for CMC and Nagios
    for key, value in host_config.extra_host_attributes.items():
        if key == "cmk_agent_connection":
            continue
        if host_config.is_cluster and key == "parents":
            continue
        host_spec[key] = value

    return host_spec


def _create_nagios_servicedefs(
    cfg: NagiosConfig, config_cache: ConfigCache, hostname: HostName, host_attrs: ObjectAttributes
) -> None:
    from cmk.base.check_table import get_check_table  # pylint: disable=import-outside-toplevel

    host_config = config_cache.get_host_config(hostname)

    check_mk_attrs = core_config.get_service_attributes(hostname, "Check_MK", config_cache)

    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services

    def do_omit_service(hostname: HostName, description: ServiceName) -> bool:
        if config.service_ignored(hostname, None, description):
            return True
        if hostname != config_cache.host_of_clustered_service(hostname, description):
            return True
        return False

    def get_dependencies(hostname: HostName, servicedesc: ServiceName) -> str:
        result = ""
        for dep in config.service_depends_on(hostname, servicedesc):
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

    host_check_table = get_check_table(hostname)
    have_at_least_one_service = False
    used_descriptions: Dict[ServiceName, AbstractServiceID] = {}
    for service in sorted(host_check_table.values(), key=lambda s: s.sort_key()):

        if not service.description:
            core_config.warning(
                "Skipping invalid service with empty description (plugin: %s) on host %s"
                % (service.check_plugin_name, hostname)
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

        # TODO: CMK-1125
        # For now, for every check plugin developed against the new check API
        # we just assume that it may have metrics. The careful review of this
        # mechanism is subject of issue CMK-1125
        check_info_value = CHECK_INFO_BY_MIGRATED_NAME.get(
            service.check_plugin_name, {"has_perfdata": True}
        )
        if check_info_value.get("has_perfdata", False):
            template = config.passive_service_template_perf
        else:
            template = config.passive_service_template

        # Services Dependencies for autochecks
        cfg.write(get_dependencies(hostname, service.description))

        service_spec = {
            "use": template,
            "host_name": hostname,
            "service_description": service.description,
            "check_command": "check_mk-%s" % service.check_plugin_name,
        }

        service_spec.update(
            core_config.get_cmk_passive_service_attributes(
                config_cache, host_config, service, check_mk_attrs
            )
        )
        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service.description)
        )

        cfg.write(_format_nagios_object("service", service_spec))

        cfg.checknames_to_define.add(service.check_plugin_name)
        have_at_least_one_service = True

    # Active check for Check_MK
    if host_config.add_active_checkmk_check():
        service_spec = {
            "use": config.active_service_template,
            "host_name": hostname,
            "service_description": "Check_MK",
        }
        service_spec.update(check_mk_attrs)
        service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname, "Check_MK"))
        cfg.write(_format_nagios_object("service", service_spec))

    # legacy checks via active_checks
    actchecks = []
    for plugin_name, entries in host_config.active_checks:
        cfg.active_checks_to_define.add(plugin_name)
        act_info = config.active_check_info[plugin_name]
        for params in entries:
            actchecks.append((plugin_name, act_info, params))

    if actchecks:
        cfg.write("\n\n# Active checks\n")
        for acttype, act_info, params in actchecks:

            has_perfdata = act_info.get("has_perfdata", False)

            # Make hostname available as global variable in argument functions
            with plugin_contexts.current_host(hostname):
                for description, args in core_config.iter_active_check_services(
                    acttype, act_info, hostname, host_attrs, params
                ):

                    if not description:
                        core_config.warning(
                            f"Skipping invalid service with empty description (active check: {acttype}) on host {hostname}"
                        )
                        continue

                    if do_omit_service(hostname, description):
                        continue

                    # quote ! and \ for Nagios
                    escaped_args = args.replace("\\", "\\\\").replace("!", "\\!")

                    if description in used_descriptions:
                        cn, it = used_descriptions[description]
                        # If we have the same active check again with the same description,
                        # then we do not regard this as an error, but simply ignore the
                        # second one. That way one can override a check with other settings.
                        if cn == "active(%s)" % acttype:
                            continue

                        core_config.duplicate_service_warning(
                            checktype="active",
                            description=description,
                            host_name=hostname,
                            first_occurrence=(cn, it),
                            second_occurrence=("active(%s)" % acttype, None),
                        )
                        continue

                    # TODO: is this right? description on the right, not item?
                    used_descriptions[description] = ("active(" + acttype + ")", description)

                    template = "check_mk_perf," if has_perfdata else ""

                    if host_attrs["address"] in ["0.0.0.0", "::"]:
                        command_name = "check-mk-custom"
                        command = (
                            command_name
                            + '!echo "CRIT - Failed to lookup IP address and no explicit IP address configured" && exit 2'
                        )
                        cfg.custom_commands_to_define.add(command_name)
                    else:
                        command = "check_mk_active-%s!%s" % (acttype, escaped_args)

                    service_spec = {
                        "use": "%scheck_mk_default" % template,
                        "host_name": hostname,
                        "service_description": description,
                        "check_command": _simulate_command(cfg, command),
                        "active_checks_enabled": str(1),
                    }
                    service_spec.update(
                        core_config.get_service_attributes(hostname, description, config_cache)
                    )
                    service_spec.update(
                        _extra_service_conf_of(cfg, config_cache, hostname, description)
                    )
                    cfg.write(_format_nagios_object("service", service_spec))

                    # write service dependencies for active checks
                    cfg.write(get_dependencies(hostname, description))

    # Legacy checks via custom_checks
    custchecks = host_config.custom_checks
    if custchecks:
        cfg.write("\n\n# Custom checks\n")
        for entry in custchecks:
            # entries are dicts with the following keys:
            # "service_description"        Service description to use
            # "command_line"  (optional)   Unix command line for executing the check
            #                              If this is missing, we create a passive check
            # "command_name"  (optional)   Name of Monitoring command to define. If missing,
            #                              we use "check-mk-custom"
            # "has_perfdata"  (optional)   If present and True, we activate perf_data
            description = config.get_final_service_description(
                hostname, entry["service_description"]
            )
            has_perfdata = entry.get("has_perfdata", False)
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if not description:
                core_config.warning(
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
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one.
                if cn == "custom(%s)" % command_name:
                    continue

                core_config.duplicate_service_warning(
                    checktype="custom",
                    description=description,
                    host_name=hostname,
                    first_occurrence=(cn, it),
                    second_occurrence=("custom(%s)" % command_name, description),
                )
                continue

            used_descriptions[description] = ("custom(%s)" % command_name, description)

            template = "check_mk_perf," if has_perfdata else ""
            command = "%s!%s" % (command_name, command_line)

            service_spec = {
                "use": "%scheck_mk_default" % template,
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

            # write service dependencies for custom checks
            cfg.write(get_dependencies(hostname, description))

    service_discovery_name = config_cache.service_discovery_name()

    # Inventory checks - if user has configured them.
    params = host_config.discovery_check_parameters
    if host_config.add_service_discovery_check(params, service_discovery_name):
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
                "check_interval": params["check_interval"],
                "retry_interval": params["check_interval"],
            }
        )

        cfg.write(_format_nagios_object("service", service_spec))

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
            host_config,
            host_attrs["address"],
            host_config.is_ipv6_primary and 6 or 4,
            "PING",
            host_attrs.get("_NODEIPS"),
        )

    if host_config.is_ipv4v6_host:
        if host_config.is_ipv6_primary:
            _add_ping_service(
                cfg,
                config_cache,
                host_config,
                host_attrs["_ADDRESS_4"],
                4,
                "PING IPv4",
                host_attrs.get("_NODEIPS_4"),
            )
        else:
            _add_ping_service(
                cfg,
                config_cache,
                host_config,
                host_attrs["_ADDRESS_6"],
                6,
                "PING IPv6",
                host_attrs.get("_NODEIPS_6"),
            )


def _add_ping_service(
    cfg: NagiosConfig,
    config_cache: ConfigCache,
    host_config: HostConfig,
    ipaddress: HostAddress,
    family: int,
    descr: ServiceName,
    node_ips: Optional[str],
) -> None:
    hostname = host_config.hostname
    arguments = core_config.check_icmp_arguments_of(config_cache, hostname, family=family)

    ping_command = "check-mk-ping"
    if host_config.is_cluster:
        assert node_ips is not None
        arguments += " -m 1 " + node_ips
    else:
        arguments += " " + ipaddress

    service_spec = {
        "use": config.pingonly_template,
        "host_name": hostname,
        "service_description": descr,
        "check_command": "%s!%s" % (ping_command, arguments),
    }
    service_spec.update(core_config.get_service_attributes(hostname, descr, config_cache))
    service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname, descr))
    cfg.write(_format_nagios_object("service", service_spec))


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
    for acttype in cfg.active_checks_to_define:
        act_info = config.active_check_info[acttype]
        cfg.write(
            _format_nagios_object(
                "command",
                {
                    "command_name": "check_mk_active-%s" % acttype,
                    "command_line": core_config.autodetect_plugin(act_info["command_line"]),
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
                        ("%s-%s" % (fr, to)) for (fr, to) in cast(List[Tuple[str, str]], value)
                    )
                    if times:
                        timeperiod_spec[key] = times

            if "exclude" in tp:
                timeperiod_spec["exclude"] = ",".join(cast(List[TimeperiodName], tp["exclude"]))

            cfg.write(_format_nagios_object("timeperiod", timeperiod_spec))


def _create_nagios_config_contacts(cfg: NagiosConfig, hostnames: List[HostName]) -> None:
    if len(config.contacts) > 0:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Contact definitions (controlled by variable 'contacts')\n")
        cfg.write("# ------------------------------------------------------------\n\n")
        cnames = sorted(config.contacts)
        for cname in cnames:
            contact = config.contacts[cname]
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

            contact_spec = {
                "contact_name": cname,
            }

            if "alias" in contact:
                contact_spec["alias"] = contact["alias"]

            if "email" in contact:
                contact_spec["email"] = contact["email"]

            if "pager" in contact:
                contact_spec["pager"] = contact["pager"]

            if config.enable_rulebased_notifications:
                not_enabled = False
            else:
                not_enabled = contact.get("notifications_enabled", True)

            for what in ["host", "service"]:
                no = contact.get(what + "_notification_options", "")

                if not no or not not_enabled:
                    contact_spec["%s_notifications_enabled" % what] = 0
                    no = "n"

                contact_spec.update(
                    {
                        "%s_notification_options" % what: ",".join(no),
                        "%s_notification_period" % what: contact.get("notification_period", "24X7"),
                        "%s_notification_commands"
                        % what: contact.get("%s_notification_commands" % what, "check-mk-notify"),
                    }
                )

            # Add custom macros
            for macro in [m for m in contact if m.startswith("_")]:
                contact_spec[macro] = contact[macro]

            contact_spec["contactgroups"] = ", ".join(cgrs)
            cfg.write(_format_nagios_object("contact", contact_spec))

    if config.enable_rulebased_notifications and hostnames:
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
    return "'" + s.replace("\\", "\\\\").replace("'", "'\"'\"'").replace("!", "\\!") + "'"


def _extra_service_conf_of(
    cfg: NagiosConfig, config_cache: ConfigCache, hostname: HostName, description: ServiceName
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
#   | all saves substantial CPU resources as opposed to running Checkmk   |
#   | in adhoc mode (about 75%).                                           |
#   '----------------------------------------------------------------------'


def _find_check_plugins(checktype: CheckPluginNameStr) -> List[str]:
    """Find files to be included in precompile host check for a certain
    check (for example df or mem.used).

    In case of checks with a period (subchecks) we might have to include both "mem" and "mem.used".
    The subcheck *may* be implemented in a separate file."""
    if "." in checktype:
        candidates = [section_name_of(checktype), checktype]
    else:
        candidates = [checktype]

    paths = []
    for candidate in candidates:
        local_file_path = cmk.utils.paths.local_checks_dir / candidate
        if local_file_path.exists():
            paths.append(str(local_file_path))
            continue

        filename = cmk.utils.paths.checks_dir + "/" + candidate
        if os.path.exists(filename):
            paths.append(filename)

    return paths


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
            os.chmod(compiled_filename, 0o750)

        console.verbose(" ==> %s.\n", compiled_filename, stream=sys.stderr)


def _precompile_hostchecks(config_path: VersionedConfigPath) -> None:
    console.verbose("Creating precompiled host check config...\n")
    config_cache = config.get_config_cache()

    config.save_packed_config(config_path, config_cache)

    console.verbose("Precompiling host checks...\n")

    host_check_store = HostCheckStore()
    for hostname in config_cache.all_active_hosts():
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
            if host_check is None:
                console.verbose("(no Checkmk checks)\n")
                continue

            host_check_store.write(config_path, hostname, host_check)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error("Error precompiling checks for host %s: %s\n" % (hostname, e))
            sys.exit(5)


def _dump_precompiled_hostcheck(
    config_cache: ConfigCache,
    config_path: VersionedConfigPath,
    hostname: HostName,
    *,
    verify_site_python=True,
) -> Optional[str]:
    host_config = config_cache.get_host_config(hostname)

    (
        needed_legacy_check_plugin_names,
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    ) = _get_needed_plugin_names(host_config)

    if host_config.is_cluster:
        if host_config.nodes is None:
            raise TypeError()

        for node_config in (config_cache.get_host_config(node) for node in host_config.nodes):
            (
                node_needed_legacy_check_plugin_names,
                node_needed_agent_based_check_plugin_names,
                node_needed_agent_based_inventory_plugin_names,
            ) = _get_needed_plugin_names(node_config)
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
    os.chmod(%(dst)r, 0o755)

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
    output.write("from cmk.utils.log import console\n")
    output.write("import cmk.base.agent_based.checking as checking\n")
    output.write("import cmk.base.check_api as check_api\n")
    output.write("import cmk.base.ip_lookup as ip_lookup\n")  # is this still needed?
    output.write("\n")
    for module in _get_needed_agent_based_modules(
        needed_agent_based_check_plugin_names,
        needed_agent_based_inventory_plugin_names,
    ):
        full_mod_name = "cmk.base.plugins.agent_based.%s" % module
        output.write("import %s\n" % full_mod_name)
        console.verbose(" %s%s%s", tty.green, full_mod_name, tty.normal, stream=sys.stderr)

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
    needed_ipaddresses, needed_ipv6addresses, = (
        {},
        {},
    )
    if host_config.is_cluster:
        if host_config.nodes is None:
            raise TypeError()

        for node in host_config.nodes:
            node_config = config_cache.get_host_config(node)
            if node_config.is_ipv4_host:
                needed_ipaddresses[node] = config.lookup_ip_address(
                    node_config, family=socket.AF_INET
                )

            if node_config.is_ipv6_host:
                needed_ipv6addresses[node] = config.lookup_ip_address(
                    node_config, family=socket.AF_INET6
                )

        try:
            if host_config.is_ipv4_host:
                needed_ipaddresses[hostname] = config.lookup_ip_address(
                    host_config, family=socket.AF_INET
                )
        except Exception:
            pass

        try:
            if host_config.is_ipv6_host:
                needed_ipv6addresses[hostname] = config.lookup_ip_address(
                    host_config, family=socket.AF_INET6
                )
        except Exception:
            pass
    else:
        if host_config.is_ipv4_host:
            needed_ipaddresses[hostname] = config.lookup_ip_address(
                host_config, family=socket.AF_INET
            )

        if host_config.is_ipv6_host:
            needed_ipv6addresses[hostname] = config.lookup_ip_address(
                host_config, family=socket.AF_INET6
            )

    output.write("config.ipaddresses = %r\n\n" % needed_ipaddresses)
    output.write("config.ipv6addresses = %r\n\n" % needed_ipv6addresses)

    # perform actual check with a general exception handler
    output.write("try:\n")
    output.write("    sys.exit(checking.active_check_checking(%r, None))\n" % hostname)
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
    host_config: config.HostConfig,
) -> Tuple[Set[CheckPluginNameStr], Set[CheckPluginName], Set[InventoryPluginName]]:
    from cmk.base import check_table  # pylint: disable=import-outside-toplevel

    needed_legacy_check_plugin_names = {*_plugins_for_special_agents(host_config)}

    # Collect the needed check plugin names using the host check table.
    # Even auto-migrated checks must be on the list of needed *agent based* plugins:
    # In those cases, the module attribute will be `None`, so nothing will
    # be imported; BUT: we need it in the list, because it must be considered
    # when determining the needed *section* plugins.
    # This matters in cases where the section is migrated, but the check
    # plugins are not.
    needed_agent_based_check_plugin_names = check_table.get_check_table(
        host_config.hostname,
        filter_mode=check_table.FilterMode.INCLUDE_CLUSTERED,
        skip_ignored=False,
    ).needed_check_names()

    legacy_names = (_resolve_legacy_plugin_name(pn) for pn in needed_agent_based_check_plugin_names)
    needed_legacy_check_plugin_names.update(ln for ln in legacy_names if ln is not None)

    # Inventory plugins get passed parsed data these days.
    # Load the required sections, or inventory plugins will crash upon unparsed data.
    needed_agent_based_inventory_plugin_names: Set[InventoryPluginName] = set()
    if host_config.do_status_data_inventory:
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


def _plugins_for_special_agents(host_config: HostConfig) -> Iterable[CheckPluginNameStr]:
    """determine required special agent plugins

    In case the host is monitored as special agent, the check plugin for the special agent
    needs to be loaded
    """
    try:
        ipaddress = config.lookup_ip_address(host_config)
    except Exception:
        ipaddress = None

    yield from (
        s.special_agent_plugin_file_name
        for s in sources.make_sources(
            host_config,
            ipaddress,
        )
        if isinstance(s, sources.programs.SpecialAgentSource)
    )


def _resolve_legacy_plugin_name(check_plugin_name: CheckPluginName) -> Optional[CheckPluginNameStr]:
    legacy_name = config.legacy_check_plugin_names.get(check_plugin_name)
    if legacy_name:
        return legacy_name

    if not check_plugin_name.is_management_name():
        return None

    # See if me must include a legacy plugin from which we derived the given one:
    # A management plugin *could have been* created on the fly, from a 'regular' legacy
    # check plugin. In this case, we must load that.
    plugin = agent_based_register.get_check_plugin(check_plugin_name)
    if not plugin or plugin.module is not None:
        # it does *not* result from a legacy plugin, if module is not None
        return None

    # just try to get the legacy name of the 'regular' plugin:
    return config.legacy_check_plugin_names.get(check_plugin_name.create_basic_name())


def _get_legacy_check_file_names_to_load(
    needed_check_plugin_names: Set[CheckPluginNameStr],
) -> List[str]:
    # check info table
    # We need to include all those plugins that are referenced in the host's
    # check table.
    filenames: List[str] = []
    for check_plugin_name in needed_check_plugin_names:
        section_name = section_name_of(check_plugin_name)
        # Add library files needed by check (also look in local)
        for lib in set(config.check_includes.get(section_name, [])):
            local_path = cmk.utils.paths.local_checks_dir / lib
            if local_path.exists():
                to_add = str(local_path)
            else:
                to_add = cmk.utils.paths.checks_dir + "/" + lib

            if to_add not in filenames:
                filenames.append(to_add)

        # Now add check file(s) itself
        paths = _find_check_plugins(check_plugin_name)
        if not paths:
            raise MKGeneralException(
                "Cannot find check file %s needed for check type %s"
                % (section_name, check_plugin_name)
            )

        for path in paths:
            if path not in filenames:
                filenames.append(path)

    return filenames


def _get_needed_agent_based_modules(
    check_plugin_names: Set[CheckPluginName],
    inventory_plugin_names: Set[InventoryPluginName],
) -> List[str]:

    modules = {
        plugin.module
        for plugin in [agent_based_register.get_check_plugin(p) for p in check_plugin_names]
        if plugin is not None and plugin.module is not None
    }
    modules.update(
        (
            plugin.module
            for plugin in [
                agent_based_register.get_inventory_plugin(p) for p in inventory_plugin_names
            ]
            if plugin is not None and plugin.module is not None
        )
    )
    modules.update(
        (
            section.module
            for section in agent_based_register.get_relevant_raw_sections(
                check_plugin_names=check_plugin_names,
                inventory_plugin_names=inventory_plugin_names,
            ).values()
            if section.module is not None
        )
    )

    return sorted(modules)


def _get_required_legacy_check_sections(
    check_plugin_names: Set[CheckPluginName],
    inventory_plugin_names: Set[InventoryPluginName],
) -> Set[str]:
    """
    new style plugin may have a dependency to a legacy check
    """
    required_legacy_check_sections = set()
    for section in agent_based_register.get_relevant_raw_sections(
        check_plugin_names=check_plugin_names,
        inventory_plugin_names=inventory_plugin_names,
    ).values():
        if section.module is None:
            required_legacy_check_sections.add(str(section.name))
    return required_legacy_check_sections
