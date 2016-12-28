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

import cmk.tty as tty

import cmk_base.utils
import cmk_base.config as config
import cmk_base.core_config as core_config
import cmk_base.console as console
import cmk_base.rulesets as rulesets
import cmk_base.agent_data as agent_data
import cmk_base.ip_lookup as ip_lookup
import cmk_base.check_table as check_table

def dump_host(hostname):
    console.output("\n")
    if config.is_cluster(hostname):
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(config.nodes_of(hostname))) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    console.output("%s%s%s%-78s %s\n" %
        (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ipaddress = _ip_address_for_dump_host(hostname)

    addresses = ""
    if not config.is_ipv4v6_host(hostname):
        addresses = ipaddress
    else:
        ipv6_primary = config.is_ipv6_primary(hostname)
        try:
            if ipv6_primary:
                secondary = _ip_address_for_dump_host(hostname, 4)
            else:
                secondary = _ip_address_for_dump_host(hostname, 6)
        except:
            secondary = "X.X.X.X"

        addresses = "%s, %s" % (ipaddress, secondary)
        if ipv6_primary:
            addresses += " (Primary: IPv6)"
        else:
            addresses += " (Primary: IPv4)"

    console.output(tty.yellow + "Addresses:              " + tty.normal + addresses + "\n")

    tags = config.tags_of_host(hostname)
    console.output(tty.yellow + "Tags:                   " + tty.normal + ", ".join(tags) + "\n")
    if config.is_cluster(hostname):
        parents_list = config.nodes_of(hostname)
    else:
        parents_list = config.parents_of(hostname)
    if len(parents_list) > 0:
        console.output(tty.yellow + "Parents:                " + tty.normal + ", ".join(parents_list) + "\n")
    console.output(tty.yellow + "Host groups:            " + tty.normal + cmk_base.utils.make_utf8(", ".join(config.hostgroups_of(hostname))) + "\n")
    console.output(tty.yellow + "Contact groups:         " + tty.normal + cmk_base.utils.make_utf8(", ".join(config.contactgroups_of(hostname))) + "\n")

    agenttypes = []
    if config.is_tcp_host(hostname):
        dapg = agent_data.get_datasource_program(hostname, ipaddress)
        if dapg:
            agenttypes.append("Datasource program: %s" % dapg)
        else:
            agenttypes.append("TCP (port: %d)" % config.agent_port_of(hostname))

    if config.is_snmp_host(hostname):
        if config.is_usewalk_host(hostname):
            agenttypes.append("SNMP (use stored walk)")
        else:
            if config.is_inline_snmp_host(hostname):
                inline = "yes"
            else:
                inline = "no"

            credentials = config.snmp_credentials_of(hostname)
            if type(credentials) in [ str, unicode ]:
                cred = "community: \'%s\'" % credentials
            else:
                cred = "credentials: '%s'" % ", ".join(credentials)

            if config.is_snmpv3_host(hostname) or config.is_bulkwalk_host(hostname):
                bulk = "yes"
            else:
                bulk = "no"

            portinfo = config.snmp_port_of(hostname)
            if portinfo == None:
                portinfo = 'default'

            agenttypes.append("SNMP (%s, bulk walk: %s, port: %s, inline: %s)" %
                (cred, bulk, portinfo, inline))

    if config.is_ping_host(hostname):
        agenttypes.append('PING only')

    console.output(tty.yellow + "Type of agent:          " + tty.normal + '\n                        '.join(agenttypes) + "\n")

    console.output(tty.yellow + "Services:" + tty.normal + "\n")
    check_items = check_table.get_sorted_check_table(hostname)

    headers = ["checktype", "item",    "params", "description", "groups"]
    colors =  [ tty.normal,  tty.blue, tty.normal, tty.green, tty.normal ]
    if config.service_dependencies != []:
        headers.append("depends on")
        colors.append(tty.magenta)

    tty.print_table(headers, colors, [ [
        checktype,
        cmk_base.utils.make_utf8(item),
        params,
        cmk_base.utils.make_utf8(description),
        cmk_base.utils.make_utf8(",".join(rulesets.service_extra_conf(hostname, description, config.service_groups))),
        ",".join(deps)
        ]
                  for checktype, item, params, description, deps in check_items ], "  ")


def _ip_address_for_dump_host(hostname, family=None):
    if config.is_cluster(hostname):
        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname, family)
        except:
            ipaddress = ""
    else:
        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname, family)
        except:
            ipaddress = core_config.fallback_ip_for(hostname, family)
    return ipaddress
