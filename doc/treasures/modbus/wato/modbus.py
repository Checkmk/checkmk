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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

# Put this file into share/check_mk/web/plugins/wato. It will create a rules
# for modbus checks and a rule in the configuration of the special agents.

register_check_parameters(
  subgroup_environment,
  "modbus_value",
  _("Modbus Performance Values"),
  Tuple(
     elements = [
         Integer(title = _("Warning if above")),
         Integer(title = _("Critical if above"))
        ]
  ),
  TextAscii( title = _("Value Name") ),
  None
)


register_rule(group,
    "special_agents:modbus",
    Tuple(
        title = _("Check Modbus devices"),
        help = _( "Configure the Server Address and the ids you want to query from the device"
                  "Please refer to the documentation of the device to find out which ids you want"),
        elements = [
           Integer( title = _("Port Number"), default_value=502 ),
           ListOf(
               Tuple(
                   elements = [
                     Integer( title=_("Counter ID") ),
                     DropdownChoice(
                       title = _("Number of words"),
                       choices = [
                          ( 1 , _("1 Word") ),
                          ( 2, _("2 Words") ),
                       ]
                     ),
                     DropdownChoice(
                       title = _("Value type"),
                       choices = [
                          ( "counter" , _("Its a counter value") ),
                          ( "gauge", _("Its a gauge value") ),
                       ]
                     ),
                     TextAscii( title = _("Counter Description")),
                   ]
               )
           )
        ]
    ),
    match = "first")


