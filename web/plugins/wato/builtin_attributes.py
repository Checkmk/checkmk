#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

declare_host_attribute(TextAttribute("alias", _("Alias"), 
                       _("A comment or description of this host"),
                       "", mandatory=False), show_in_table = True, show_in_folder = False)

declare_host_attribute(IPAddressAttribute("ipaddress", _("IP Address"), 
                       _("IP Address of the host. Leave emtpy to use automatic "
                         "hostname lookup. Enter a hostname to use dynamic resoluting "
                         "during the actual monitoring."), mandatory=True, dnslookup=True),
                         show_in_table=True, show_in_folder=True)


declare_host_attribute(EnumAttribute("dirty", _("Dirty"),
                       _("Modified since last &quot;Active Changes&quot;?"),
                       "No", [ ('no', _('No')), ('yes', _('Yes'))]),
                       show_in_table = False, show_in_folder = False, show_in_form = False)
