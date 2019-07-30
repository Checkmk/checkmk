#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
import numbers
import os
import sys
from typing import Text, Optional, Any, List, Dict  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.password_store
from cmk.utils.exceptions import MKGeneralException

import cmk_base.console as console
import cmk_base.config as config
import cmk_base.ip_lookup as ip_lookup
from cmk_base.check_utils import Service  # pylint: disable=unused-import


class MonitoringCore(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def create_config(self):
        pass

    @abc.abstractmethod
    def precompile(self):
        pass


_ignore_ip_lookup_failures = False
_failed_ip_lookups = []

#.
#   .--Warnings------------------------------------------------------------.
#   |            __        __               _                              |
#   |            \ \      / /_ _ _ __ _ __ (_)_ __   __ _ ___              |
#   |             \ \ /\ / / _` | '__| '_ \| | '_ \ / _` / __|             |
#   |              \ V  V / (_| | |  | | | | | | | | (_| \__ \             |
#   |               \_/\_/ \__,_|_|  |_| |_|_|_| |_|\__, |___/             |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Managing of warning messages occuring during configuration building  |
#   '----------------------------------------------------------------------'

g_configuration_warnings = []  # type: List[Any]


def initialize_warnings():
    global g_configuration_warnings
    g_configuration_warnings = []


def warning(text):
    g_configuration_warnings.append(text)
    console.warning("\n%s", text, stream=sys.stdout)


def get_configuration_warnings():
    num_warnings = len(g_configuration_warnings)

    if num_warnings > 10:
        warnings = g_configuration_warnings[:10] + \
                                  [ "%d further warnings have been omitted" % (num_warnings - 10) ]
    else:
        warnings = g_configuration_warnings

    return warnings


# TODO: Cleanup the hostcheck_commands_to_define, custom_commands_to_define thing
def host_check_command(config_cache,
                       host_config,
                       ip,
                       is_clust,
                       hostcheck_commands_to_define=None,
                       custom_commands_to_define=None):

    explicit_command = host_config.explicit_check_command
    if explicit_command is not None:
        value = explicit_command
    elif host_config.is_no_ip_host:
        value = "ok"
    elif config.monitoring_core == "cmc":
        value = "smart"
    else:
        value = "ping"

    if value == "smart" and not is_clust:
        return "check-mk-host-smart"

    if value in ["ping", "smart"]:  # Cluster host
        ping_args = check_icmp_arguments_of(config_cache, host_config.hostname)

        if is_clust and ip:  # Do check cluster IP address if one is there
            return "check-mk-host-ping!%s" % ping_args
        elif ping_args and is_clust:  # use check_icmp in cluster mode
            return "check-mk-host-ping-cluster!%s" % ping_args
        elif ping_args:  # use special arguments
            return "check-mk-host-ping!%s" % ping_args

        return None

    if value == "ok":
        return "check-mk-host-ok"

    if value == "agent" or value[0] == "service":
        service = "Check_MK" if value == "agent" else value[1]

        if config.monitoring_core == "cmc":
            return "check-mk-host-service!" + service

        command = "check-mk-host-custom-%d" % (len(hostcheck_commands_to_define) + 1)
        hostcheck_commands_to_define.append(
            (command, 'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$' %
             (host_config.hostname, service.replace('$HOSTNAME$', host_config.hostname),
              host_config.hostname, service.replace('$HOSTNAME$', host_config.hostname))))
        return command

    if value[0] == "tcp":
        return "check-mk-host-tcp!" + str(value[1])

    if value[0] == "custom":
        if custom_commands_to_define is not None:
            custom_commands_to_define.add("check-mk-custom")
        return "check-mk-custom!" + autodetect_plugin(value[1])

    raise MKGeneralException("Invalid value %r for host_check_command of host %s." %
                             (value, host_config.hostname))


def autodetect_plugin(command_line):
    plugin_name = command_line.split()[0]
    if command_line[0] not in ['$', '/']:
        for directory in ["/local", ""]:
            path = cmk.utils.paths.omd_root + directory + "/lib/nagios/plugins/"
            if os.path.exists(path + plugin_name):
                command_line = path + command_line
                break
    return command_line


def check_icmp_arguments_of(config_cache, hostname, add_defaults=True, family=None):
    host_config = config_cache.get_host_config(hostname)
    levels = host_config.ping_levels

    if not add_defaults and not levels:
        return ""

    if family is None:
        family = 6 if host_config.is_ipv6_primary else 4

    args = []

    if family == 6:
        args.append("-6")

    rta = 200, 500
    loss = 80, 100
    for key, value in levels.items():
        if key == "timeout":
            args.append("-t %d" % value)
        elif key == "packets":
            args.append("-n %d" % value)
        elif key == "rta":
            rta = value
        elif key == "loss":
            loss = value
    args.append("-w %.2f,%.2f%%" % (rta[0], loss[0]))
    args.append("-c %.2f,%.2f%%" % (rta[1], loss[1]))
    return " ".join(args)


#.
#   .--Core Config---------------------------------------------------------.
#   |          ____                  ____             __ _                 |
#   |         / ___|___  _ __ ___   / ___|___  _ __  / _(_) __ _           |
#   |        | |   / _ \| '__/ _ \ | |   / _ \| '_ \| |_| |/ _` |          |
#   |        | |__| (_) | | |  __/ | |__| (_) | | | |  _| | (_| |          |
#   |         \____\___/|_|  \___|  \____\___/|_| |_|_| |_|\__, |          |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   | Code for managing the core configuration creation.                   |
#   '----------------------------------------------------------------------'


# TODO: Move to modes?
def do_create_config(core, with_agents):
    console.output("Generating configuration for core (type %s)..." % config.monitoring_core)
    create_core_config(core)
    console.output(tty.ok + "\n")

    if with_agents:
        try:
            import cmk_base.cee.agent_bakery
            cmk_base.cee.agent_bakery.bake_on_restart()
        except ImportError:
            pass


def create_core_config(core):
    initialize_warnings()

    _verify_non_duplicate_hosts()
    _verify_non_deprecated_checkgroups()
    core.create_config()
    cmk.utils.password_store.save(config.stored_passwords)

    return get_configuration_warnings()


# Verify that the user has no deprecated check groups configured.
def _verify_non_deprecated_checkgroups():
    groups = config.checks_by_checkgroup()

    for checkgroup in config.checkgroup_parameters:
        if checkgroup not in groups:
            warning(
                "Found configured rules of deprecated check group \"%s\". These rules are not used "
                "by any check. Maybe this check group has been renamed during an update, "
                "in this case you will have to migrate your configuration to the new ruleset manually. "
                "Please check out the release notes of the involved versions. "
                "You may use the page \"Deprecated rules\" in WATO to view your rules and move them to "
                "the new rulesets." % checkgroup)


def _verify_non_duplicate_hosts():
    duplicates = config.duplicate_hosts()
    if duplicates:
        warning("The following host names have duplicates: %s. "
                "This might lead to invalid/incomplete monitoring for these hosts." %
                ", ".join(duplicates))


def do_update(core, with_precompile):
    try:
        do_create_config(core, with_agents=with_precompile)
        if with_precompile:
            core.precompile()

    except Exception as e:
        console.error("Configuration Error: %s\n" % e)
        if cmk.utils.debug.enabled():
            raise
        sys.exit(1)


#.
#   .--Active Checks-------------------------------------------------------.
#   |       _        _   _              ____ _               _             |
#   |      / \   ___| |_(_)_   _____   / ___| |__   ___  ___| | _____      |
#   |     / _ \ / __| __| \ \ / / _ \ | |   | '_ \ / _ \/ __| |/ / __|     |
#   |    / ___ \ (__| |_| |\ V /  __/ | |___| | | |  __/ (__|   <\__ \     |
#   |   /_/   \_\___|\__|_| \_/ \___|  \____|_| |_|\___|\___|_|\_\___/     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Active check specific functions                                      |
#   '----------------------------------------------------------------------'


def active_check_arguments(hostname, description, args):
    if not isinstance(args, (str, unicode, list)):
        raise MKGeneralException(
            "The check argument function needs to return either a list of arguments or a "
            "string of the concatenated arguments (Host: %s, Service: %s)." %
            (hostname, description))

    return config.prepare_check_command(args, hostname, description)


#.
#   .--ServiceAttrs.-------------------------------------------------------.
#   |     ____                  _             _   _   _                    |
#   |    / ___|  ___ _ ____   _(_) ___ ___   / \ | |_| |_ _ __ ___         |
#   |    \___ \ / _ \ '__\ \ / / |/ __/ _ \ / _ \| __| __| '__/ __|        |
#   |     ___) |  __/ |   \ V /| | (_|  __// ___ \ |_| |_| |  \__ \_       |
#   |    |____/ \___|_|    \_/ |_|\___\___/_/   \_\__|\__|_|  |___(_)      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Management of service attributes                                     |
#   '----------------------------------------------------------------------'


def get_cmk_passive_service_attributes(config_cache, host_config, service, check_mk_attrs):
    # type: (config.ConfigCache, config.HostConfig, Service, Dict) -> Dict
    attrs = get_service_attributes(host_config.hostname, service.description, config_cache,
                                   service.check_plugin_name, service.parameters)

    value = host_config.snmp_check_interval(config_cache.section_name_of(service.check_plugin_name))
    if value is not None:
        attrs["check_interval"] = value
    else:
        attrs["check_interval"] = check_mk_attrs["check_interval"]

    return attrs


def get_service_attributes(hostname, description, config_cache, checkname=None, params=None):
    attrs = _extra_service_attributes(hostname, description, config_cache, checkname, params)
    attrs.update(_get_tag_attributes(config_cache.tags_of_service(hostname, description), "TAG"))

    attrs.update(_get_tag_attributes(config_cache.labels_of_service(hostname, description),
                                     "LABEL"))
    attrs.update(
        _get_tag_attributes(config_cache.label_sources_of_service(hostname, description),
                            "LABELSOURCE"))
    return attrs


def _extra_service_attributes(hostname, description, config_cache, checkname, params):
    attrs = {}

    # Add service custom_variables. Name conflicts are prevented by the GUI, but just
    # to be sure, add them first. The other definitions will override the custom attributes.
    for varname, value in config_cache.custom_attributes_of_service(hostname,
                                                                    description).iteritems():
        attrs["_%s" % varname.upper()] = value

    attrs.update(config_cache.extra_attributes_of_service(hostname, description))

    # Add explicit custom_variables
    for varname, value in config_cache.get_explicit_service_custom_variables(
            hostname, description).iteritems():
        attrs["_%s" % varname.upper()] = value

    # Add custom user icons and actions
    actions = config_cache.icons_and_actions_of_service(hostname, description, checkname, params)
    if actions:
        attrs["_ACTIONS"] = ','.join(actions)
    return attrs


#.
#   .--HostAttributes------------------------------------------------------.
#   | _   _           _      _   _   _        _ _           _              |
#   || | | | ___  ___| |_   / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___   |
#   || |_| |/ _ \/ __| __| / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|  |
#   ||  _  | (_) \__ \ |_ / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \  |
#   ||_| |_|\___/|___/\__/_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Managing of host attributes                                          |
#   '----------------------------------------------------------------------'


def get_host_attributes(hostname, config_cache):
    host_config = config_cache.get_host_config(hostname)
    attrs = host_config.extra_host_attributes

    # Pre 1.6 legacy attribute. We have changed our whole code to use the
    # livestatus column "tags" which is populated by all attributes starting with
    # "__TAG_" instead. We may deprecate this is one day.
    attrs["_TAGS"] = " ".join(sorted(config_cache.get_host_config(hostname).tags))

    attrs.update(_get_tag_attributes(host_config.tag_groups, "TAG"))
    attrs.update(_get_tag_attributes(host_config.labels, "LABEL"))
    attrs.update(_get_tag_attributes(host_config.label_sources, "LABELSOURCE"))

    if "alias" not in attrs:
        attrs["alias"] = host_config.alias

    # Now lookup configured IP addresses
    if host_config.is_ipv4_host:
        attrs["_ADDRESS_4"] = _ip_address_of(host_config, 4)
        if attrs["_ADDRESS_4"] is None:
            attrs["_ADDRESS_4"] = ""
    else:
        attrs["_ADDRESS_4"] = ""

    if host_config.is_ipv6_host:
        attrs["_ADDRESS_6"] = _ip_address_of(host_config, 6)
        if attrs["_ADDRESS_6"] is None:
            attrs["_ADDRESS_6"] = ""
    else:
        attrs["_ADDRESS_6"] = ""

    ipv6_primary = host_config.is_ipv6_primary
    if ipv6_primary:
        attrs["address"] = attrs["_ADDRESS_6"]
        attrs["_ADDRESS_FAMILY"] = "6"
    else:
        attrs["address"] = attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "4"

    add_ipv4addrs, add_ipv6addrs = host_config.additional_ipaddresses
    if add_ipv4addrs:
        attrs["_ADDRESSES_4"] = " ".join(add_ipv4addrs)
        for nr, ipv4_address in enumerate(add_ipv4addrs):
            key = "_ADDRESS_4_%s" % (nr + 1)
            attrs[key] = ipv4_address

    if add_ipv6addrs:
        attrs["_ADDRESSES_6"] = " ".join(add_ipv6addrs)
        for nr, ipv6_address in enumerate(add_ipv6addrs):
            key = "_ADDRESS_6_%s" % (nr + 1)
            attrs[key] = ipv6_address

    # Add the optional WATO folder path
    path = config.host_paths.get(hostname)
    if path:
        attrs["_FILENAME"] = path

    # Add custom user icons and actions
    actions = host_config.icons_and_actions
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)

    if cmk.is_managed_edition():
        attrs["_CUSTOMER"] = config.current_customer  # pylint: disable=no-member

    return attrs


def _get_tag_attributes(collection, prefix):
    return {u"__%s_%s" % (prefix, k): unicode(v) for k, v in collection.iteritems()}


def get_cluster_attributes(config_cache, host_config, nodes):
    # type: (config.ConfigCache, config.HostConfig, List[str]) -> Dict
    sorted_nodes = sorted(nodes)

    attrs = {
        "_NODENAMES": " ".join(sorted_nodes),
    }
    node_ips_4 = []
    if host_config.is_ipv4_host:
        for h in sorted_nodes:
            node_config = config_cache.get_host_config(h)
            addr = _ip_address_of(node_config, 4)
            if addr is not None:
                node_ips_4.append(addr)
            else:
                node_ips_4.append(fallback_ip_for(node_config, 4))

    node_ips_6 = []
    if host_config.is_ipv6_host:
        for h in sorted_nodes:
            node_config = config_cache.get_host_config(h)
            addr = _ip_address_of(node_config, 6)
            if addr is not None:
                node_ips_6.append(addr)
            else:
                node_ips_6.append(fallback_ip_for(node_config, 6))

    node_ips = node_ips_6 if host_config.is_ipv6_primary else node_ips_4

    for suffix, val in [("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6)]:
        attrs["_NODEIPS%s" % suffix] = " ".join(val)

    return attrs


def get_cluster_nodes_for_config(config_cache, host_config):
    # type: (config.ConfigCache, config.HostConfig) -> List[str]
    _verify_cluster_address_family(config_cache, host_config)

    if host_config.nodes is None:
        return []

    nodes = host_config.nodes[:]
    for node in nodes:
        if node not in config_cache.all_active_realhosts():
            warning("Node '%s' of cluster '%s' is not a monitored host in this site." %
                    (node, host_config.hostname))
            nodes.remove(node)
    return nodes


def _verify_cluster_address_family(config_cache, host_config):
    # type: (config.ConfigCache, config.HostConfig) -> None
    cluster_host_family = "IPv6" if host_config.is_ipv6_primary else "IPv4"

    address_families = [
        "%s: %s" % (host_config.hostname, cluster_host_family),
    ]

    if host_config.nodes is None:
        return None

    address_family = cluster_host_family
    mixed = False
    for nodename in host_config.nodes:
        node_config = config_cache.get_host_config(nodename)
        family = "IPv6" if node_config.is_ipv6_primary else "IPv4"
        address_families.append("%s: %s" % (nodename, family))
        if address_family is None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        warning("Cluster '%s' has different primary address families: %s" %
                (host_config.hostname, ", ".join(address_families)))


def _ip_address_of(host_config, family=None):
    # type: (config.HostConfig, Optional[int]) -> Optional[str]
    try:
        return ip_lookup.lookup_ip_address(host_config.hostname, family)
    except Exception as e:
        if host_config.is_cluster:
            return ""

        _failed_ip_lookups.append(host_config.hostname)
        if not _ignore_ip_lookup_failures:
            warning("Cannot lookup IP address of '%s' (%s). "
                    "The host will not be monitored correctly." % (host_config.hostname, e))
        return fallback_ip_for(host_config.hostname, family)


def ignore_ip_lookup_failures():
    global _ignore_ip_lookup_failures
    _ignore_ip_lookup_failures = True


def failed_ip_lookups():
    return _failed_ip_lookups


def fallback_ip_for(host_config, family=None):
    if family is None:
        family = 6 if host_config.is_ipv6_primary else 4

    if family == 4:
        return "0.0.0.0"

    return "::"


def get_host_macros_from_attributes(hostname, attrs):
    macros = {
        "$HOSTNAME$": hostname,
        "$HOSTADDRESS$": attrs['address'],
        "$HOSTALIAS$": attrs['alias'],
    }

    # Add custom macros
    for macro_name, value in attrs.items():
        if macro_name[0] == '_':
            macros["$HOST" + macro_name + "$"] = value
            # Be compatible to nagios making $_HOST<VARNAME>$ out of the config _<VARNAME> configs
            macros["$_HOST" + macro_name[1:] + "$"] = value

    return macros


def replace_macros(s, macros):
    for key, value in macros.items():
        if isinstance(value, (numbers.Integral, float)):
            value = str(value)  # e.g. in _EC_SL (service level)

        # TODO: Clean this up
        try:
            s = s.replace(key, value)
        except Exception:  # Might have failed due to binary UTF-8 encoding in value
            try:
                s = s.replace(key, value.decode("utf-8"))
            except Exception:
                # If this does not help, do not replace
                if cmk.utils.debug.enabled():
                    raise

    return s
