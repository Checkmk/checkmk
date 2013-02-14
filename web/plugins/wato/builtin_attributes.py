#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

declare_host_attribute(ContactGroupsAttribute(),
                       show_in_table = True,
                       show_in_folder = True)

declare_host_attribute(NagiosTextAttribute("alias", "alias", _("Alias"),
                       _("A comment or description of this host"),
                       "", mandatory=False),
                       show_in_table = True,
                       show_in_folder = False)

declare_host_attribute(TextAttribute("ipaddress", _("IP address"),
                       _("In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
                         "or DNS by your monitoring server, you can specify an explicit IP "
                         "address or a resolvable DNS name of the host here. <b>Note</b>: If you leave "
                         "this attribute empty, then DNS resolution will be done when you activate "
                         "the configuration. When you enter a DNS name here, the DNS resolution will "
                         "be done each time the host is checked. Use this only for hosts with "
                         "dynamic IP addresses."),
                         allow_empty = False),
                         show_in_table = True,
                         show_in_folder = False)

# Attribute for configuring parents
class ParentsAttribute(ValueSpecAttribute):
    def __init__(self):
        ValueSpecAttribute.__init__(self, "parents",
               ListOfStrings(
                   title = _("Parents"),
                   help = _("Parents are used to configure the reachability of hosts by the "
                      "monitoring server. A host is considered to be <b>unreachable</b> if all "
                      "of its parents are unreachable or down. Unreachable hosts will not be "
                      "actively monitored.<br><br><b>Clusters</b> automatically configure all "
                      "of their nodes as parents, but only if you do not configure parents "
                      "manually.<br><br>In a distributed setup make sure that the host and all "
                      "of its parents are monitored by the same site."),
                   orientation = "horizontal"))

    def to_nagios(self, value):
        if value:
            return ",".join(value)

    def nagios_name(self):
        return "parents"

    def paint(self, value, hostname):
        parts = [ '<a href="%s">%s</a>' % (
                   "wato.py?" + htmllib.urlencode_vars([("mode", "edithost"), ("host", hn)]), hn)
                  for hn in value ]
        return "", ", ".join(parts)


declare_host_attribute(ParentsAttribute(),
                       show_in_table = True,
                       show_in_folder = True)

def validate_host_parents(effective_host):
    for parentname in effective_host["parents"]:
        parent_folder = find_host(parentname)
        if not parent_folder:
            raise MKUserError(None, _("You defined the non-existing host '%s' as a parent.") % parentname)
        # In case of distributed wato check also if site of host and parent
        # are the same.
        if is_distributed():
            parent = effective_attributes(parent_folder[".hosts"][parentname], parent_folder)
            if effective_host["site"] !=  parent["site"]:
                raise MKUserError(None, _("The parent '%s' is monitored on site '%s' while the host itself "
                  "is monitored on site '%s'. Both must be monitored on the same site. Remember: The parent/child "
                  "relation is used to describe the reachability of hosts by one monitoring daemon.") %
                    (parentname, parent["site"], effective_host["site"]))

api.register_hook('validate-host', validate_host_parents)

