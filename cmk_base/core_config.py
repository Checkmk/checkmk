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

import os
import sys

import cmk.debug
import cmk.paths
import cmk.tty as tty
import cmk.store as store
import cmk.password_store
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.checks as checks
import cmk_base.rulesets as rulesets
import cmk_base.ip_lookup as ip_lookup

_cmc_relfilename           = "config"
_ignore_ip_lookup_failures = False
_failed_ip_lookups         = []

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

g_configuration_warnings = []


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
def host_check_command(hostname, ip, is_clust, hostcheck_commands_to_define=None,
                                               custom_commands_to_define=None):
    # Check dedicated host check command
    values = rulesets.host_extra_conf(hostname, config.host_check_commands)
    if values:
        value = values[0]
    elif config.is_no_ip_host(hostname):
        value = "ok"
    elif config.monitoring_core == "cmc":
        value = "smart"
    else:
        value = "ping"

    if config.monitoring_core != "cmc" and value == "smart":
        value = "ping" # avoid problems when switching back to nagios core

    if value == "smart" and not is_clust:
        return "check-mk-host-smart"

    elif value in [ "ping", "smart" ]: # Cluster host
        ping_args = check_icmp_arguments_of(hostname)

        if is_clust and ip: # Do check cluster IP address if one is there
            return "check-mk-host-ping!%s" % ping_args
        elif ping_args and is_clust: # use check_icmp in cluster mode
            return "check-mk-host-ping-cluster!%s" % ping_args
        elif ping_args: # use special arguments
            return "check-mk-host-ping!%s" % ping_args
        else:
            return None

    elif value == "ok":
        return "check-mk-host-ok"

    elif value == "agent" or value[0] == "service":
        service = value == "agent" and "Check_MK" or value[1]

        if config.monitoring_core == "cmc":
            return "check-mk-host-service!" + service
        else:
            command = "check-mk-host-custom-%d" % (len(hostcheck_commands_to_define) + 1)
            hostcheck_commands_to_define.append((command,
               'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$' %
                    (hostname, service.replace('$HOSTNAME$', hostname),
                     hostname, service.replace('$HOSTNAME$', hostname))))
            return command

    elif value[0] == "tcp":
        return "check-mk-host-tcp!" + str(value[1])

    elif value[0] == "custom":
        try:
            custom_commands_to_define.add("check-mk-custom")
        except:
            pass # not needed and not available with CMC
        return "check-mk-custom!" + autodetect_plugin(value[1])

    raise MKGeneralException("Invalid value %r for host_check_command of host %s." % (
            value, hostname))


def autodetect_plugin(command_line):
    plugin_name = command_line.split()[0]
    if command_line[0] not in [ '$', '/' ]:
        try:
            for dir in [ "/local", "" ]:
                path = cmk.paths.omd_root + dir + "/lib/nagios/plugins/"
                if os.path.exists(path + plugin_name):
                    command_line = path + command_line
                    break
        except:
            pass
    return command_line


def icons_and_actions_of(what, hostname, svcdesc = None, checkname = None, params = None):
    if what == 'host':
        return list(set(rulesets.host_extra_conf(hostname, config.host_icons_and_actions)))
    else:
        actions = set(rulesets.service_extra_conf(hostname, svcdesc, config.service_icons_and_actions))

        # Some WATO rules might register icons on their own
        if checkname:
            checkgroup = checks.check_info[checkname]["group"]
            if checkgroup in [ 'ps', 'services' ] and type(params) == dict:
                icon = params.get('icon')
                if icon:
                    actions.add(icon)

        return list(actions)


def check_icmp_arguments_of(hostname, add_defaults=True, family=None):
    values = rulesets.host_extra_conf(hostname, config.ping_levels)
    levels = {}
    for value in values[::-1]: # make first rules have precedence
        levels.update(value)
    if not add_defaults and not levels:
        return ""

    if family == None:
        family = config.is_ipv6_primary(hostname) and 6 or 4

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

def set_cmc_relfilename(name):
    global _cmc_relfilename
    _cmc_relfilename = name


# TODO: Move to modes?
def do_create_config(with_agents=True):
    console.output("Generating configuration for core (type %s)..." %
                                                config.monitoring_core)
    create_core_config()
    console.output(tty.ok + "\n")

    if with_agents and cmk_base.utils.has_feature("cee.agent_bakery"):
       import cmk_base.cee.agent_bakery as agent_bakery
       agent_bakery.bake_on_restart()


def create_core_config():
    initialize_warnings()

    _verify_non_duplicate_hosts()
    _verify_non_deprecated_checkgroups()
    _create_config()
    cmk.password_store.save(config.stored_passwords)

    return get_configuration_warnings()


def _create_config():
    if config.monitoring_core == "cmc":
        import cmk_base.cee.core_cmc as core_cmc
        core_cmc.create_config(_cmc_relfilename)
    else:
        import cmk_base.core_nagios as core_nagios
        core_nagios.create_config(cmk.paths.nagios_objects_file)


# Verify that the user has no deprecated check groups configured.
def _verify_non_deprecated_checkgroups():
    groups = checks.checks_by_checkgroup()

    for checkgroup in config.checkgroup_parameters.keys():
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
        warning(
              "The following host names have duplicates: %s. "
              "This might lead to invalid/incomplete monitoring for these hosts." % ", ".join(duplicates))


def precompile():
    if config.monitoring_core == "cmc":
        import cmk_base.cee.core_cmc as core_cmc
        core_cmc.do_pack_config()
    else:
        import cmk_base.core_nagios as core_nagios
        core_nagios.do_precompile_hostchecks()


def do_update(with_precompile):
    try:
        do_create_config(with_agents=with_precompile)
        if with_precompile:
            precompile()

    except Exception, e:
        console.error("Configuration Error: %s\n" % e)
        if cmk.debug.enabled():
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
    if type(args) in [ str, unicode ]:
        return args

    elif type(args) == list:
        passwords, formated = [], []
        for arg in args:
            arg_type = type(arg)

            if arg_type in [ int, float ]:
                formated.append("%s" % arg)

            elif arg_type in [ str, unicode ]:
                formated.append(cmk_base.utils.quote_shell_string(arg))

            elif arg_type == tuple and len(arg) == 3:
                pw_ident, preformated_arg = arg[1:]
                try:
                    password = config.stored_passwords[pw_ident]["password"]
                except KeyError:
                    warning("The stored password \"%s\" used by service \"%s\" on host "
                                        "\"%s\" does not exist (anymore)." %
                                            (pw_ident, description, hostname))
                    password = "%%%"

                pw_start_index = str(preformated_arg.index("%s"))
                formated.append(cmk_base.utils.quote_shell_string(preformated_arg % ("*" * len(password))))
                passwords.append((str(len(formated)), pw_start_index, pw_ident))

            else:
                raise MKGeneralException("Invalid argument for command line: %s" % arg)

        if passwords:
            formated = [ "--pwstore=%s" % ",".join([ "@".join(p) for p in passwords ]) ] + formated

        return " ".join(formated)

    else:
        raise MKGeneralException("The check argument function needs to return either a list of arguments or a "
                                 "string of the concatenated arguments (Host: %s, Service: %s)." % (hostname, description))


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

def get_host_attributes(hostname, tags):
    attrs = _extra_host_attributes(hostname)

    attrs["_TAGS"] = " ".join(tags)

    if "alias" not in attrs:
        attrs["alias"] = config.alias_of(hostname, hostname)

    # Now lookup configured IP addresses
    if config.is_ipv4_host(hostname):
        attrs["_ADDRESS_4"] = ip_address_of(hostname, 4)
        if attrs["_ADDRESS_4"] == None:
            attrs["_ADDRESS_4"] = ""
    else:
        attrs["_ADDRESS_4"] = ""

    if config.is_ipv6_host(hostname):
        attrs["_ADDRESS_6"] = ip_address_of(hostname, 6)
        if attrs["_ADDRESS_6"] == None:
            attrs["_ADDRESS_6"] = ""
    else:
        attrs["_ADDRESS_6"] = ""

    ipv6_primary = config.is_ipv6_primary(hostname)
    if ipv6_primary:
        attrs["address"] = attrs["_ADDRESS_6"]
        attrs["_ADDRESS_FAMILY"] = "6"
    else:
        attrs["address"] = attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "4"

    add_ipv4addrs, add_ipv6addrs = config.get_additional_ipaddresses_of(hostname)
    if add_ipv4addrs:
        attrs["_ADDRESSES_4"] = " ".join(add_ipv4addrs)
    if add_ipv6addrs:
        attrs["_ADDRESSES_6"] = " ".join(add_ipv6addrs)

    # Add the optional WATO folder path
    path = config.host_paths.get(hostname)
    if path:
        attrs["_FILENAME"] = path

    # Add custom user icons and actions
    actions = icons_and_actions_of("host", hostname)
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)

    if cmk.is_managed_edition():
        attrs["_CUSTOMER"] = config.current_customer # pylint: disable=no-member

    return attrs


def _extra_host_attributes(hostname):
    attrs = {}
    for key, conflist in config.extra_host_conf.items():
        values = rulesets.host_extra_conf(hostname, conflist)
        if values:
            if key[0] == "_":
                key = key.upper()

            if values[0] != None:
                attrs[key] = values[0]
    return attrs


def get_cluster_attributes(hostname, nodes):
    sorted_nodes = sorted(nodes)

    attrs = {
        "_NODENAMES": " ".join(sorted_nodes),
    }
    node_ips_4 = []
    if config.is_ipv4_host(hostname):
        for h in sorted_nodes:
            addr = ip_address_of(h, 4)
            if addr != None:
                node_ips_4.append(addr)
            else:
                node_ips_4.append(fallback_ip_for(hostname, 4))

    node_ips_6 = []
    if config.is_ipv6_host(hostname):
        for h in sorted_nodes:
            addr = ip_address_of(h, 6)
            if addr != None:
                node_ips_6.append(addr)
            else:
                node_ips_6.append(fallback_ip_for(hostname, 6))

    if config.is_ipv6_primary(hostname):
        node_ips = node_ips_6
    else:
        node_ips = node_ips_4

    for suffix, val in [ ("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6) ]:
        attrs["_NODEIPS%s" % suffix] = " ".join(val)

    return attrs



def get_cluster_nodes_for_config(hostname):
    _verify_cluster_address_family(hostname)

    nodes = config.nodes_of(hostname)[:]
    for node in nodes:
        if node not in config.all_active_realhosts():
            warning("Node '%s' of cluster '%s' is not a monitored host in this site." %
                                                                                      (node, hostname))
            nodes.remove(node)
    return nodes


def _verify_cluster_address_family(hostname):
    cluster_host_family = config.is_ipv6_primary(hostname) and "IPv6" or "IPv4"

    address_families = [
        "%s: %s" % (hostname, cluster_host_family),
    ]

    address_family = cluster_host_family
    mixed = False
    for nodename in config.nodes_of(hostname):
        family = config.is_ipv6_primary(nodename) and "IPv6" or "IPv4"
        address_families.append("%s: %s" % (nodename, family))
        if address_family == None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        warning("Cluster '%s' has different primary address families: %s" %
                                    (hostname, ", ".join(address_families)))


def ip_address_of(hostname, family=None):
    try:
        return ip_lookup.lookup_ip_address(hostname, family)
    except Exception, e:
        if config.is_cluster(hostname):
            return ""
        else:
            _failed_ip_lookups.append(hostname)
            if not _ignore_ip_lookup_failures:
                warning("Cannot lookup IP address of '%s' (%s). "
                        "The host will not be monitored correctly." % (hostname, e))
            return fallback_ip_for(hostname, family)


def ignore_ip_lookup_failures():
    global _ignore_ip_lookup_failures
    _ignore_ip_lookup_failures = True


def failed_ip_lookups():
    return _failed_ip_lookups


def fallback_ip_for(hostname, family=None):
    if family == None:
        family = config.is_ipv6_primary(hostname) and 6 or 4

    if family == 4:
        return "0.0.0.0"
    else:
        return "::"


def get_host_macros_from_attributes(hostname, attrs):
    macros = {
        "$HOSTNAME$"     : hostname,
        "$HOSTADDRESS$"  : attrs['address'],
        "$HOSTALIAS$"    : attrs['alias'],
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
        if type(value) in (int, long, float):
            value = str(value) # e.g. in _EC_SL (service level)

        # TODO: Clean this up
        try:
            s = s.replace(key, value)
        except: # Might have failed due to binary UTF-8 encoding in value
            try:
                s = s.replace(key, value.decode("utf-8"))
            except:
                # If this does not help, do not replace
                if cmk.debug.enabled():
                    raise

    return s


