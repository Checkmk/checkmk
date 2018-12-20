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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "skype_edge", _("Skype for Business Edge"),
    Dictionary(elements=[
        ('authentication_failures',
         Dictionary(
             title=_("Authentication Failures"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Integer(title=_("Warning at"), unit=_("per second"), default_value=20),
                      Integer(title=_("Critical at"), unit=_("per second"), default_value=40),
                  ])),
             ],
             optional_keys=[])),
        ('allocate_requests_exceeding',
         Dictionary(
             title=_("Allocate Requests Exceeding Port Limit"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Integer(title=_("Warning at"), unit=_("per second"), default_value=20),
                      Integer(title=_("Critical at"), unit=_("per second"), default_value=40),
                  ])),
             ],
             optional_keys=[])),
        ('packets_dropped',
         Dictionary(
             title=_("Packets Dropped"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Integer(title=_("Warning at"), unit=_("per second"), default_value=200),
                      Integer(title=_("Critical at"), unit=_("per second"), default_value=400),
                  ])),
             ],
             optional_keys=[])),
    ]),
    TextAscii(
        title=_("Interface"),
        help=_("The name of the interface (Public/Private IPv4/IPv6 Network Interface)"),
    ), "dict")  # Rule for disovered process checks
