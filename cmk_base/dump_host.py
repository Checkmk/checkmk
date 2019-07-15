#!/usr/bin/python
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

import time

import cmk.utils.tty as tty
import cmk.utils.render

import cmk_base.utils
import cmk_base.config as config
import cmk_base.core_config as core_config
import cmk_base.console as console
import cmk_base.data_sources as data_sources
import cmk_base.ip_lookup as ip_lookup
import cmk_base.check_table as check_table
import cmk_base.checking as checking


def dump_host(hostname):
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    console.output("\n")
    if host_config.is_cluster:
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(host_config.nodes)) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    console.output("%s%s%s%-78s %s\n" %
                   (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ipaddress = _ip_address_for_dump_host(host_config)

    addresses = ""
    if not host_config.is_ipv4v6_host:
        addresses = ipaddress
    else:
        try:
            if host_config.is_ipv6_primary:
                secondary = _ip_address_for_dump_host(host_config, 4)
            else:
                secondary = _ip_address_for_dump_host(host_config, 6)
        except:
            secondary = "X.X.X.X"

        addresses = "%s, %s" % (ipaddress, secondary)
        if host_config.is_ipv6_primary:
            addresses += " (Primary: IPv6)"
        else:
            addresses += " (Primary: IPv4)"

    console.output(tty.yellow + "Addresses:              " + tty.normal +
                   (addresses if addresses is not None else "No IP") + "\n")

    tag_template = tty.bold + "[" + tty.normal + "%s" + tty.bold + "]" + tty.normal
    tags = [(tag_template % ":".join(t)) for t in sorted(host_config.tag_groups.items())]
    console.output(tty.yellow + "Tags:                   " + tty.normal + ", ".join(tags) + "\n")
    # TODO: Clean this up once cluster parent handling has been moved to HostConfig
    if host_config.is_cluster:
        parents_list = host_config.nodes
    else:
        parents_list = host_config.parents
    if len(parents_list) > 0:
        console.output(tty.yellow + "Parents:                " + tty.normal +
                       ", ".join(parents_list) + "\n")
    console.output(tty.yellow + "Host groups:            " + tty.normal +
                   cmk_base.utils.make_utf8(", ".join(host_config.hostgroups)) + "\n")
    console.output(tty.yellow + "Contact groups:         " + tty.normal +
                   cmk_base.utils.make_utf8(", ".join(host_config.contactgroups)) + "\n")

    agenttypes = []
    sources = data_sources.DataSources(hostname, ipaddress)
    for source in sources.get_data_sources():
        agenttypes.append(source.describe())

    if host_config.is_ping_host:
        agenttypes.append('PING only')

    console.output(tty.yellow + "Agent mode:             " + tty.normal)
    console.output(sources.describe_data_sources() + "\n")

    console.output(tty.yellow + "Type of agent:          " + tty.normal)
    if len(agenttypes) == 1:
        console.output(agenttypes[0] + "\n")
    else:
        console.output("\n  ")
        console.output("\n  ".join(agenttypes) + "\n")

    console.output(tty.yellow + "Services:" + tty.normal + "\n")

    headers = ["checktype", "item", "params", "description", "groups"]
    colors = [tty.normal, tty.blue, tty.normal, tty.green, tty.normal]

    table_data = []
    for service in sorted(check_table.get_check_table(hostname).values(),
                          key=lambda s: s.description):
        table_data.append([
            service.check_plugin_name,
            cmk_base.utils.make_utf8(service.item),
            _evaluate_params(service.parameters),
            cmk_base.utils.make_utf8(service.description),
            cmk_base.utils.make_utf8(",".join(
                config_cache.servicegroups_of_service(hostname, service.description)))
        ])

    tty.print_table(headers, colors, table_data, "  ")


def _evaluate_params(params):
    if not isinstance(params, cmk_base.config.TimespecificParamList):
        return params

    current_params = checking.determine_check_params(params)
    return "Timespecific parameters at %s: %r" % (cmk.utils.render.date_and_time(
        time.time()), current_params)


def _ip_address_for_dump_host(host_config, family=None):
    if host_config.is_cluster:
        try:
            return ip_lookup.lookup_ip_address(host_config.hostname, family)
        except:
            return ""

    try:
        return ip_lookup.lookup_ip_address(host_config.hostname, family)
    except:
        return core_config.fallback_ip_for(host_config, family)
