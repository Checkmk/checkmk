#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

register_rulegroup("datasource_programs",
    _("Datasource Programs"),
    _("Specialized agents, e.g. check via SSH, ESX vSphere, SAP R/3"))
group = "datasource_programs"

register_rule(group,
    "special_agents:vsphere",
     Dictionary(
        title = _("Check state of VMWare ESX via vSphere"),
        help = _("(MISSING)"),
        elements = [
            ( "user",
              TextAscii(
                  title = _("vSphere User name"),
                  allow_empty = False,
              )
            ),
            ( "secret",
              TextAscii(
                  title = _("vSphere secret"),
                  allow_empty = False,
              )  
            ),
            ( "tcp_port",
              Integer(
                   title = _("TCP Port number"),
                   help = _("Port number for connecting to vSphere"),
                   default_value = 4711, 
                   minvalue = 1,
                   maxvalue = 65535,
              )  
            ),
            ( "infos",
              ListChoice(
                 title = _("Retrieve information about..."),
                 choices = [
                     ( "hostsystem",     _("Host Systems") ),
                     ( "virtualmachine", _("'Virtual Machines") ),
                 ],
                 default_value = [ "hostsystem", "virtualmachine" ],
                 allow_empty = False,
               )
             ),
        ],
        optional_keys = [ "tcp_port", ],
    ),
    match = 'first')


