#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for support of Nagios (and compatible) cores"""

import base64
import os
import sys
import py_compile
import tempfile
import errno
from typing import Tuple, Any, IO, Optional, List, Set, Dict

from six import ensure_binary, ensure_str

import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import (
    ServiceName,
    HostName,
    Item,
    HostAddress,
    HostgroupName,
    ServicegroupName,
    ContactgroupName,
)

import cmk.base.utils
import cmk.base.obsolete_output as out
import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.data_sources as data_sources
import cmk.base.check_api_utils as check_api_utils
from cmk.base.check_utils import (
    CheckPluginName,)
from cmk.base.config import (
    ConfigCache,
    HostConfig,
    ObjectAttributes,
)
from cmk.base.core_config import CoreCommand, CoreCommandName

ObjectSpec = Dict[str, Any]


class NagiosCore(core_config.MonitoringCore):
    def create_config(self):
        # type: () -> None
        """Tries to create a new Check_MK object configuration file for the Nagios core

        During create_config() exceptions may be raised which are caused by configuration issues.
        Don't produce a half written object file. Simply throw away everything and keep the old file.

        The user can then start the site with the old configuration and fix the configuration issue
        while the monitoring is running.
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    "w",
                    dir=os.path.dirname(cmk.utils.paths.nagios_objects_file),
                    prefix=".%s.new" % os.path.basename(cmk.utils.paths.nagios_objects_file),
                    delete=False) as tmp:
                tmp_path = tmp.name
                os.chmod(tmp.name, 0o660)
                create_config(tmp, hostnames=None)
                os.rename(tmp.name, cmk.utils.paths.nagios_objects_file)

        except Exception:
            # In case an exception happens cleanup the tempfile created for writing
            try:
                if tmp_path:
                    os.unlink(tmp_path)
            except IOError as e:
                if e.errno == errno.ENOENT:  # No such file or directory
                    pass
            raise

    def precompile(self):
        # type: () -> None
        out.output("Precompiling host checks...")
        precompile_hostchecks()
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
    def __init__(self, outfile, hostnames):
        # type: (IO[str], Optional[List[HostName]]) -> None
        super(NagiosConfig, self).__init__()
        self._outfile = outfile
        self.hostnames = hostnames

        self.hostgroups_to_define = set()  # type: Set[HostgroupName]
        self.servicegroups_to_define = set()  # type: Set[ServicegroupName]
        self.contactgroups_to_define = set()  # type: Set[ContactgroupName]
        self.checknames_to_define = set()  # type: Set[CheckPluginName]
        self.active_checks_to_define = set()  # type: Set[CheckPluginName]
        self.custom_commands_to_define = set()  # type: Set[CoreCommandName]
        self.hostcheck_commands_to_define = []  # type: List[Tuple[CoreCommand, str]]

    def write(self, x):
        # type: (str) -> None
        # TODO: Something seems to be mixed up in our call sites...
        self._outfile.write(ensure_str(x))


def create_config(outfile, hostnames):
    # type: (IO[str], Optional[List[HostName]]) -> None
    if config.host_notification_periods != []:
        core_config.warning(
            "host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead."
        )

    if config.service_notification_periods != []:
        core_config.warning(
            "service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead."
        )

    # Map service_period to _SERVICE_PERIOD. This field das not exist in Nagios.
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


def _output_conf_header(cfg):
    # type: (NagiosConfig) -> None
    cfg.write("""#
# Created by Check_MK. Do not edit.
#

""")


def _create_nagios_config_host(cfg, config_cache, hostname):
    # type: (NagiosConfig, ConfigCache, HostName) -> None
    cfg.write("\n# ----------------------------------------------------\n")
    cfg.write("# %s\n" % hostname)
    cfg.write("# ----------------------------------------------------\n")
    host_attrs = core_config.get_host_attributes(hostname, config_cache)
    if config.generate_hostconf:
        host_spec = _create_nagios_host_spec(cfg, config_cache, hostname, host_attrs)
        cfg.write(_format_nagios_object("host", host_spec))
    _create_nagios_servicedefs(cfg, config_cache, hostname, host_attrs)


def _create_nagios_host_spec(cfg, config_cache, hostname, attrs):
    # type: (NagiosConfig, ConfigCache, HostName, ObjectAttributes) -> ObjectSpec
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
        "address": ip if ip else core_config.fallback_ip_for(host_config),
        "alias": attrs["alias"],
    }

    # Add custom macros
    for key, value in attrs.items():
        if key[0] == '_':
            host_spec[key] = value

    def host_check_via_service_status(service):
        # type: (ServiceName) -> CoreCommand
        command = "check-mk-host-custom-%d" % (len(cfg.hostcheck_commands_to_define) + 1)
        cfg.hostcheck_commands_to_define.append(
            (command, 'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$' %
             (host_config.hostname, service.replace('$HOSTNAME$', host_config.hostname),
              host_config.hostname, service.replace('$HOSTNAME$', host_config.hostname))))
        return command

    def host_check_via_custom_check(command_name, command):
        # type: (CoreCommandName, CoreCommand) -> CoreCommand
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
        host_check_via_custom_check)
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
        if host_config.is_cluster and key == "parents":
            continue
        host_spec[key] = value

    return host_spec


def _create_nagios_servicedefs(cfg, config_cache, hostname, host_attrs):
    # type: (NagiosConfig, ConfigCache, HostName, ObjectAttributes) -> None
    import cmk.base.check_table as check_table  # pylint: disable=import-outside-toplevel

    host_config = config_cache.get_host_config(hostname)

    check_mk_attrs = core_config.get_service_attributes(hostname, "Check_MK", config_cache)

    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services

    def do_omit_service(hostname, description):
        # type: (HostName, ServiceName) -> bool
        if config.service_ignored(hostname, None, description):
            return True
        if hostname != config_cache.host_of_clustered_service(hostname, description):
            return True
        return False

    def get_dependencies(hostname, servicedesc):
        # type: (HostName, ServiceName) -> str
        result = ""
        for dep in config.service_depends_on(hostname, servicedesc):
            result += _format_nagios_object(
                "servicedependency", {
                    "use": config.service_dependency_template,
                    "host_name": hostname,
                    "service_description": dep,
                    "dependent_host_name": hostname,
                    "dependent_service_description": servicedesc,
                })

        return result

    services = check_table.get_check_table(hostname, remove_duplicates=True).values()
    have_at_least_one_service = False
    used_descriptions = {}  # type: Dict[ServiceName, Tuple[CheckPluginName, Item]]
    for service in sorted(services, key=lambda s: (s.check_plugin_name, s.item)):
        if service.check_plugin_name not in config.check_info:
            continue  # simply ignore missing checks

        if not service.description:
            core_config.warning(
                "Skipping invalid service with empty description (plugin: %s) on host %s" %
                (service.check_plugin_name, hostname))
            continue

        # Make sure, the service description is unique on this host
        if service.description in used_descriptions:
            cn, it = used_descriptions[service.description]
            # TODO: Remove "type: ignore" once we are on python3
            core_config.warning(
                "ERROR: Duplicate service description '%s' for host '%s'!\n"  # type: ignore[arg-type]
                " - 1st occurrance: checktype = %s, item = %r\n"
                " - 2nd occurrance: checktype = %s, item = %r\n" %
                (service.description, hostname, cn, it, service.check_plugin_name, service.item))
            continue

        used_descriptions[service.description] = (service.check_plugin_name, service.item)
        if config.check_info[service.check_plugin_name].get("has_perfdata", False):
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
            core_config.get_cmk_passive_service_attributes(config_cache, host_config, service,
                                                           check_mk_attrs))
        service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname,
                                                   service.description))

        cfg.write(_format_nagios_object("service", service_spec))

        cfg.checknames_to_define.add(service.check_plugin_name)
        have_at_least_one_service = True

    # Active check for check_mk
    if have_at_least_one_service:
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
            # Make hostname available as global variable in argument functions
            check_api_utils.set_hostname(hostname)

            has_perfdata = act_info.get('has_perfdata', False)
            description = config.active_check_service_description(hostname, acttype, params)

            if not description:
                core_config.warning(
                    "Skipping invalid service with empty description (active check: %s) on host %s"
                    % (acttype, hostname))
                continue

            if do_omit_service(hostname, description):
                continue

            # compute argument, and quote ! and \ for Nagios
            args = core_config.active_check_arguments(
                hostname, description,
                act_info["argument_function"](params)).replace("\\", "\\\\").replace("!", "\\!")

            if description in used_descriptions:
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                if cn == "active(%s)" % acttype:
                    continue

                # TODO: Remove "type: ignore" once we are on python3
                core_config.warning(
                    "ERROR: Duplicate service description (active check) '%s' for host '%s'!\n"  # type: ignore[arg-type]
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = active(%s), item = None\n" %
                    (description, hostname, cn, it, acttype))
                continue

            used_descriptions[description] = ("active(" + acttype + ")", description)

            template = "check_mk_perf," if has_perfdata else ""

            if host_attrs["address"] in ["0.0.0.0", "::"]:
                command_name = "check-mk-custom"
                command = command_name + "!echo \"CRIT - Failed to lookup IP address and no explicit IP address configured\" && exit 2"
                cfg.custom_commands_to_define.add(command_name)
            else:
                command = "check_mk_active-%s!%s" % (acttype, args)

            service_spec = {
                "use": "%scheck_mk_default" % template,
                "host_name": hostname,
                "service_description": description,
                "check_command": _simulate_command(cfg, command),
                "active_checks_enabled": str(1),
            }
            service_spec.update(
                core_config.get_service_attributes(hostname, description, config_cache))
            service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname, description))
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
            description = config.get_final_service_description(hostname,
                                                               entry["service_description"])
            has_perfdata = entry.get("has_perfdata", False)
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if not description:
                core_config.warning("Skipping invalid service with empty description on host %s" %
                                    hostname)
                continue

            if command_line:
                command_line = core_config.autodetect_plugin(command_line).replace("\\",
                                                                                   "\\\\").replace(
                                                                                       "!", "\\!")

            if "freshness" in entry:
                freshness = {
                    "check_freshness": 1,
                    "freshness_threshold": 60 * entry["freshness"]["interval"],
                }
                command_line = "echo %s && exit %d" % (_quote_nagios_string(
                    entry["freshness"]["output"]), entry["freshness"]["state"])
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
                # TODO: Remove "type: ignore" once we are on python3
                core_config.warning(
                    "ERROR: Duplicate service description (custom check) '%s' for host '%s'!\n"  # type: ignore[arg-type]
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = custom(%s), item = %r\n" %
                    (description, hostname, cn, it, command_name, description))
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
                core_config.get_service_attributes(hostname, description, config_cache))
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
            core_config.get_service_attributes(hostname, service_discovery_name, config_cache))

        service_spec.update(
            _extra_service_conf_of(cfg, config_cache, hostname, service_discovery_name))

        service_spec.update({
            "check_interval": params["check_interval"],
            "retry_interval": params["check_interval"],
        })

        cfg.write(_format_nagios_object("service", service_spec))

        if have_at_least_one_service:
            cfg.write(
                _format_nagios_object(
                    "servicedependency", {
                        "use": config.service_dependency_template,
                        "host_name": hostname,
                        "service_description": "Check_MK",
                        "dependent_host_name": hostname,
                        "dependent_service_description": service_discovery_name,
                    }))

    # No check_mk service, no legacy service -> create PING service
    if not have_at_least_one_service and not actchecks and not custchecks:
        _add_ping_service(cfg, config_cache, host_config,
                          host_attrs["address"], host_config.is_ipv6_primary and 6 or 4, "PING",
                          host_attrs.get("_NODEIPS"))

    if host_config.is_ipv4v6_host:
        if host_config.is_ipv6_primary:
            _add_ping_service(cfg, config_cache, host_config, host_attrs["_ADDRESS_4"], 4,
                              "PING IPv4", host_attrs.get("_NODEIPS_4"))
        else:
            _add_ping_service(cfg, config_cache, host_config, host_attrs["_ADDRESS_6"], 6,
                              "PING IPv6", host_attrs.get("_NODEIPS_6"))


def _add_ping_service(cfg, config_cache, host_config, ipaddress, family, descr, node_ips):
    # type: (NagiosConfig, ConfigCache, HostConfig, HostAddress, int, ServiceName, Optional[str]) -> None
    hostname = host_config.hostname
    arguments = core_config.check_icmp_arguments_of(config_cache, hostname, family=family)

    ping_command = 'check-mk-ping'
    if host_config.is_cluster:
        assert node_ips is not None
        arguments += ' -m 1 ' + node_ips
    else:
        arguments += ' ' + ipaddress

    service_spec = {
        "use": config.pingonly_template,
        "host_name": hostname,
        "service_description": descr,
        "check_command": "%s!%s" % (ping_command, arguments),
    }
    service_spec.update(core_config.get_service_attributes(hostname, descr, config_cache))
    service_spec.update(_extra_service_conf_of(cfg, config_cache, hostname, descr))
    cfg.write(_format_nagios_object("service", service_spec))


def _format_nagios_object(object_type, object_spec):
    # type: (str, ObjectSpec) -> str
    cfg = ["define %s {" % object_type]
    for key, val in sorted(object_spec.items(), key=lambda x: x[0]):
        # Use a base16 encoding for names and values of tags, labels and label
        # sources to work around the syntactic restrictions in Nagios' object
        # configuration files.
        if key[0] == "_":  # quick pre-check: custom variable?
            for prefix in ("__TAG_", "__LABEL_", "__LABELSOURCE_"):
                if key.startswith(prefix):
                    key = prefix + _b16encode(key[len(prefix):])
                    val = _b16encode(val)
        cfg.append("  %-29s %s" % (key, val))
    cfg.append("}")

    return "\n".join(cfg) + "\n\n"


def _b16encode(b):
    # type: (str) -> str
    return ensure_str(base64.b16encode(ensure_binary(b)))


def _simulate_command(cfg, command):
    # type: (NagiosConfig, CoreCommand) -> CoreCommand
    if config.simulation_mode:
        cfg.custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"
    return command


def _create_nagios_config_hostgroups(cfg):
    # type: (NagiosConfig) -> None
    if config.define_hostgroups:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Host groups (controlled by define_hostgroups)\n")
        cfg.write("# ------------------------------------------------------------\n")
        hgs = sorted(cfg.hostgroups_to_define)
        for hg in hgs:
            try:
                alias = config.define_hostgroups[hg]
            except KeyError:
                alias = hg

            cfg.write(_format_nagios_object("hostgroup", {
                "hostgroup_name": hg,
                "alias": alias,
            }))

    # No creation of host groups but we need to define
    # default host group
    elif config.default_host_group in cfg.hostgroups_to_define:
        cfg.write(
            _format_nagios_object("hostgroup", {
                "hostgroup_name": config.default_host_group,
                "alias": "Check_MK default hostgroup",
            }))


def _create_nagios_config_servicegroups(cfg):
    # type: (NagiosConfig) -> None
    if config.define_servicegroups:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Service groups (controlled by define_servicegroups)\n")
        cfg.write("# ------------------------------------------------------------\n")
        sgs = sorted(cfg.servicegroups_to_define)
        for sg in sgs:
            try:
                alias = config.define_servicegroups[sg]
            except KeyError:
                alias = sg

            cfg.write(
                _format_nagios_object("servicegroup", {
                    "servicegroup_name": sg,
                    "alias": alias,
                }))


def _create_nagios_config_contactgroups(cfg):
    # type: (NagiosConfig) -> None
    # TODO: According to our types, define_contactgroups can NEVER be False,
    # but to be sure (old user configs lying around???) we keep the test and
    # shut up mypy. :-/
    if config.define_contactgroups is False:  # type: ignore[comparison-overlap]
        return

    cgs = cfg.contactgroups_to_define
    if not cgs:
        return

    cfg.write("\n# ------------------------------------------------------------\n")
    cfg.write("# Contact groups (controlled by define_contactgroups)\n")
    cfg.write("# ------------------------------------------------------------\n\n")
    for name in sorted(cgs):
        if isinstance(config.define_contactgroups, dict):
            alias = config.define_contactgroups.get(name, name)
        else:
            alias = name

        contactgroup_spec = {
            "contactgroup_name": name,
            "alias": alias,
        }

        members = config.contactgroup_members.get(name)
        if members:
            contactgroup_spec["members"] = ",".join(members)

        cfg.write(_format_nagios_object("contactgroup", contactgroup_spec))


def _create_nagios_config_commands(cfg):
    # type: (NagiosConfig) -> None
    if config.generate_dummy_commands:
        cfg.write("\n# ------------------------------------------------------------\n")
        cfg.write("# Dummy check commands and active check commands\n")
        cfg.write("# ------------------------------------------------------------\n\n")
        for checkname in cfg.checknames_to_define:
            cfg.write(
                _format_nagios_object(
                    "command", {
                        "command_name": "check_mk-%s" % checkname,
                        "command_line": config.dummy_check_commandline,
                    }))

    # active_checks
    for acttype in cfg.active_checks_to_define:
        act_info = config.active_check_info[acttype]
        cfg.write(
            _format_nagios_object(
                "command", {
                    "command_name": "check_mk_active-%s" % acttype,
                    "command_line": core_config.autodetect_plugin(act_info["command_line"]),
                }))

    # custom_checks
    for command_name in cfg.custom_commands_to_define:
        cfg.write(
            _format_nagios_object("command", {
                "command_name": command_name,
                "command_line": "$ARG1$",
            }))

    # custom host checks
    for command_name, command_line in cfg.hostcheck_commands_to_define:
        cfg.write(
            _format_nagios_object("command", {
                "command_name": command_name,
                "command_line": command_line,
            }))


def _create_nagios_config_timeperiods(cfg):
    # type: (NagiosConfig) -> None
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
                timeperiod_spec["alias"] = tp["alias"]

            for key, value in tp.items():
                if key not in ["alias", "exclude"]:
                    times = ",".join([("%s-%s" % (fr, to)) for (fr, to) in value])
                    if times:
                        timeperiod_spec[key] = times

            if "exclude" in tp:
                timeperiod_spec["exclude"] = ",".join(tp["exclude"])

            cfg.write(_format_nagios_object("timeperiod", timeperiod_spec))


def _create_nagios_config_contacts(cfg, hostnames):
    # type: (NagiosConfig, List[HostName]) -> None
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
                cgr for cgr in contact.get("contactgroups", [])
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

                contact_spec.update({
                    "%s_notification_options" % what: ",".join(no),
                    "%s_notification_period" % what: contact.get("notification_period", "24X7"),
                    "%s_notification_commands" % what: contact.get(
                        "%s_notification_commands" % what, "check-mk-notify"),
                })

            # Add custom macros
            for macro in [m for m in contact if m.startswith('_')]:
                contact_spec[macro] = contact[macro]

            contact_spec["contactgroups"] = ", ".join(cgrs)
            cfg.write(_format_nagios_object("contact", contact_spec))

    if config.enable_rulebased_notifications and hostnames:
        cfg.contactgroups_to_define.add("check-mk-notify")
        cfg.write("# Needed for rule based notifications\n")
        cfg.write(
            _format_nagios_object(
                "contact", {
                    "contact_name": "check-mk-notify",
                    "alias": "Contact for rule based notifications",
                    "host_notification_options": "d,u,r,f,s",
                    "service_notification_options": "u,c,w,r,f,s",
                    "host_notification_period": "24X7",
                    "service_notification_period": "24X7",
                    "host_notification_commands": "check-mk-notify",
                    "service_notification_commands": "check-mk-notify",
                    "contactgroups": "check-mk-notify",
                }))


def _quote_nagios_string(s):
    # type: (str) -> str
    """Quote string for use in a nagios command execution.  Please note that also
    quoting for ! and backslash for Nagios itself takes place here."""
    return "'" + s.replace('\\', '\\\\').replace("'", "'\"'\"'").replace('!', '\\!') + "'"


def _extra_service_conf_of(cfg, config_cache, hostname, description):
    # type: (NagiosConfig, ConfigCache, HostName, ServiceName) -> ObjectSpec
    """Collect all extra configuration data for a service"""
    service_spec = {}  # type: ObjectSpec

    # Add contact groups to the config only if the user has defined them.
    # Otherwise inherit the contact groups from the host.
    # "check-mk-notify" is always returned for rulebased notifications and
    # the Nagios core and not defined by the user.
    sercgr = config_cache.contactgroups_of_service(hostname, description)
    if sercgr != ['check-mk-notify']:
        service_spec["contact_groups"] = ",".join(sercgr)
        cfg.contactgroups_to_define.update(sercgr)

    sergr = config_cache.servicegroups_of_service(hostname, description)
    if sergr:
        service_spec["service_groups"] = ",".join(sergr)
        if config.define_servicegroups:
            cfg.servicegroups_to_define.update(sergr)

    return service_spec


#.
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
#   | all saves substantial CPU resources as opposed to running Check_MK   |
#   | in adhoc mode (about 75%).                                           |
#   '----------------------------------------------------------------------'


def _find_check_plugins(checktype):
    # type: (CheckPluginName) -> List[str]
    """Find files to be included in precompile host check for a certain
    check (for example df or mem.used).

    In case of checks with a period (subchecks) we might have to include both "mem" and "mem.used".
    The subcheck *may* be implemented in a separate file."""
    if '.' in checktype:
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


def precompile_hostchecks():
    # type: () -> None
    console.verbose("Creating precompiled host check config...\n")
    config.PackedConfig().save()

    if not os.path.exists(cmk.utils.paths.precompiled_hostchecks_dir):
        os.makedirs(cmk.utils.paths.precompiled_hostchecks_dir)

    config_cache = config.get_config_cache()

    console.verbose("Precompiling host checks...\n")
    for host in config_cache.all_active_hosts():
        try:
            _precompile_hostcheck(config_cache, host)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error("Error precompiling checks for host %s: %s\n" % (host, e))
            sys.exit(5)


def _precompile_hostcheck(config_cache, hostname):
    # type: (ConfigCache, HostName) -> None
    host_config = config_cache.get_host_config(hostname)

    console.verbose("%s%s%-16s%s:", tty.bold, tty.blue, hostname, tty.normal, stream=sys.stderr)

    check_api_utils.set_hostname(hostname)

    compiled_filename = cmk.utils.paths.precompiled_hostchecks_dir + "/" + hostname
    source_filename = compiled_filename + ".py"
    for fname in [compiled_filename, source_filename]:
        try:
            os.remove(fname)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    needed_check_plugin_names = _get_needed_check_plugin_names(host_config)
    if not needed_check_plugin_names:
        console.verbose("(no Check_MK checks)\n")
        return

    output = open(source_filename + ".new", "w")
    output.write("#!/usr/bin/env python3\n")
    output.write("# encoding: utf-8\n\n")

    output.write("import logging\n")
    output.write("import sys\n\n")

    output.write("if not sys.executable.startswith('/omd'):\n")
    output.write("    sys.stdout.write(\"ERROR: Only executable with sites python\\n\")\n")
    output.write("    sys.exit(2)\n\n")

    # Remove precompiled directory from sys.path. Leaving it in the path
    # makes problems when host names (name of precompiled files) are equal
    # to python module names like "random"
    output.write("sys.path.pop(0)\n")

    output.write("import cmk.utils.log\n")
    output.write("import cmk.utils.debug\n")
    output.write("from cmk.utils.exceptions import MKTerminate\n")
    output.write("\n")
    output.write("import cmk.base.utils\n")
    output.write("import cmk.base.config as config\n")
    output.write("from cmk.utils.log import console\n")
    output.write("import cmk.base.checking as checking\n")
    output.write("import cmk.base.check_api as check_api\n")
    output.write("import cmk.base.ip_lookup as ip_lookup\n")

    # Self-compile: replace symlink with precompiled python-code, if
    # we are run for the first time
    if config.delay_precompile:
        output.write("""
import os
if os.path.islink(%(dst)r):
    import py_compile
    os.remove(%(dst)r)
    py_compile.compile(%(src)r, %(dst)r, %(dst)r, True)
    os.chmod(%(dst)r, 0755)

""" % {
            "src": source_filename,
            "dst": compiled_filename
        })

    # Register default Check_MK signal handler
    output.write("cmk.base.utils.register_sigint_handler()\n")

    # initialize global variables
    output.write("""
# very simple commandline parsing: only -v (once or twice) and -d are supported

cmk.utils.log.setup_console_logging()
logger = logging.getLogger("cmk.base")

# TODO: This is not really good parsing, because it not cares about syntax like e.g. "-nv".
#       The later regular argument parsing is handling this correctly. Try to clean this up.
cmk.utils.log.logger.setLevel(cmk.utils.log.verbosity_to_log_level(len([ a for a in sys.argv if a in [ "-v", "--verbose"] ])))

if '-d' in sys.argv:
    cmk.utils.debug.enable()

""")

    output.write("config.load_checks(check_api.get_check_api_context, %r)\n" %
                 _get_needed_check_file_names(needed_check_plugin_names))

    for check_plugin_name in sorted(needed_check_plugin_names):
        console.verbose(" %s%s%s", tty.green, check_plugin_name, tty.normal, stream=sys.stderr)

    output.write("config.load_packed_config()\n")

    # IP addresses
    needed_ipaddresses, needed_ipv6addresses, = {}, {}
    if host_config.is_cluster:
        if host_config.nodes is None:
            raise TypeError()

        for node in host_config.nodes:
            node_config = config_cache.get_host_config(node)
            if node_config.is_ipv4_host:
                needed_ipaddresses[node] = ip_lookup.lookup_ipv4_address(node)

            if node_config.is_ipv6_host:
                needed_ipv6addresses[node] = ip_lookup.lookup_ipv6_address(node)

        try:
            if host_config.is_ipv4_host:
                needed_ipaddresses[hostname] = ip_lookup.lookup_ipv4_address(hostname)
        except Exception:
            pass

        try:
            if host_config.is_ipv6_host:
                needed_ipv6addresses[hostname] = ip_lookup.lookup_ipv6_address(hostname)
        except Exception:
            pass
    else:
        if host_config.is_ipv4_host:
            needed_ipaddresses[hostname] = ip_lookup.lookup_ipv4_address(hostname)

        if host_config.is_ipv6_host:
            needed_ipv6addresses[hostname] = ip_lookup.lookup_ipv6_address(hostname)

    output.write("config.ipaddresses = %r\n\n" % needed_ipaddresses)
    output.write("config.ipv6addresses = %r\n\n" % needed_ipv6addresses)

    # perform actual check with a general exception handler
    output.write("try:\n")
    output.write("    sys.exit(checking.do_check(%r, None))\n" % hostname)
    output.write("except MKTerminate:\n")
    output.write("    out.output('<Interrupted>\\n', stream=sys.stderr)\n")
    output.write("    sys.exit(1)\n")
    output.write("except SystemExit as e:\n")
    output.write("    sys.exit(e.code)\n")
    output.write("except Exception as e:\n")
    output.write("    import traceback, pprint\n")

    # status output message
    output.write(
        "    sys.stdout.write(\"UNKNOWN - Exception in precompiled check: %s (details in long output)\\n\" % e)\n"
    )

    # generate traceback for long output
    output.write("    sys.stdout.write(\"Traceback: %s\\n\" % traceback.format_exc())\n")

    output.write("\n")
    output.write("    sys.exit(3)\n")
    output.close()

    # compile python (either now or delayed), but only if the source
    # code has not changed. The Python compilation is the most costly
    # operation here.
    if os.path.exists(source_filename):
        if open(source_filename).read() == open(source_filename + ".new").read():
            console.verbose(" (%s is unchanged)\n", source_filename, stream=sys.stderr)
            os.remove(source_filename + ".new")
            return
        console.verbose(" (new content)", stream=sys.stderr)

    os.rename(source_filename + ".new", source_filename)
    if not config.delay_precompile:
        py_compile.compile(source_filename, compiled_filename, compiled_filename, True)
        os.chmod(compiled_filename, 0o755)
    else:
        if os.path.exists(compiled_filename) or os.path.islink(compiled_filename):
            os.remove(compiled_filename)
        os.symlink(hostname + ".py", compiled_filename)

    console.verbose(" ==> %s.\n", compiled_filename, stream=sys.stderr)


def _get_needed_check_plugin_names(host_config):
    # type: (config.HostConfig) -> Set[CheckPluginName]
    import cmk.base.check_table as check_table  # pylint: disable=import-outside-toplevel
    needed_check_plugin_names = set([])

    # In case the host is monitored as special agent, the check plugin for the special agent needs
    # to be loaded
    sources = data_sources.DataSources(host_config.hostname, ipaddress=None)
    for source in sources.get_data_sources():
        if isinstance(source, data_sources.programs.SpecialAgentDataSource):
            needed_check_plugin_names.add(source.special_agent_plugin_file_name)

    # Collect the needed check plugin names using the host check table
    for check_plugin_name in check_table.get_needed_check_names(host_config.hostname,
                                                                filter_mode="include_clustered",
                                                                skip_ignored=False):
        if config.check_info[check_plugin_name].get("extra_sections"):
            for section_name in config.check_info[check_plugin_name]["extra_sections"]:
                if section_name in config.check_info:
                    needed_check_plugin_names.add(section_name)

        needed_check_plugin_names.add(check_plugin_name)

    # Also include the check plugins of the cluster nodes to be able to load
    # the autochecks of the nodes
    if host_config.is_cluster:
        nodes = host_config.nodes
        if nodes is None:
            raise MKGeneralException("Invalid cluster configuration")
        for node in nodes:
            needed_check_plugin_names.update(
                check_table.get_needed_check_names(node, skip_ignored=False))

    return needed_check_plugin_names


def _get_needed_check_file_names(needed_check_plugin_names):
    # type: (Set[CheckPluginName]) -> List[str]
    # check info table
    # We need to include all those plugins that are referenced in the host's
    # check table.
    filenames = []  # type: List[str]
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
            raise MKGeneralException("Cannot find check file %s needed for check type %s" %
                                     (section_name, check_plugin_name))

        for path in paths:
            if path not in filenames:
                filenames.append(path)

    return filenames
