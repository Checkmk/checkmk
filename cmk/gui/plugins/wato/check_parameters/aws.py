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
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_ec2_cpu_credits',
    _("AWS/EC2 CPU Credits"),
    Dictionary(elements=[('balance_levels_lower',
                          Tuple(
                              title=_("Lower levels for CPU balance"),
                              elements=[
                                  Integer(title=_("Warning below")),
                                  Integer(title=_("Critical below")),
                              ]))]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_costs_and_usage',
    _("AWS Costs and Usage"),
    Dictionary(elements=[('levels_unblended',
                          Tuple(
                              title=_("Upper levels for unblended costs"),
                              elements=[
                                  Integer(title=_("Warning at")),
                                  Integer(title=_("Critical at")),
                              ]))]),
    None,
    match_type='dict',
)
