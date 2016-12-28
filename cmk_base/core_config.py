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

import cmk.paths
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.checks as checks
import cmk_base.rulesets as rulesets

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

def active_check_service_description(hostname, act_info, params):
    return checks.sanitize_service_description(act_info["service_description"](params).replace('$HOSTNAME$', hostname))


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

