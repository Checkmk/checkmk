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
    Float,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_msx_database():
    return TextAscii(
        title=_("Database Name"),
        help=_("Specify database names that the rule should apply to"),
    )


def _parameter_valuespec_msx_database():
    return Dictionary(
        title=_("Set Levels"),
        elements=[
            ('read_attached_latency',
             Tuple(
                 title=_("I/O Database Reads (Attached) Average Latency"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('ms'), default_value=200.0),
                     Float(title=_("Critical at"), unit=_('ms'), default_value=250.0)
                 ],
             )),
            ('read_recovery_latency',
             Tuple(
                 title=_("I/O Database Reads (Recovery) Average Latency"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('ms'), default_value=150.0),
                     Float(title=_("Critical at"), unit=_('ms'), default_value=200.0)
                 ],
             )),
            ('write_latency',
             Tuple(
                 title=_("I/O Database Writes (Attached) Average Latency"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('ms'), default_value=40.0),
                     Float(title=_("Critical at"), unit=_('ms'), default_value=50.0)
                 ],
             )),
            ('log_latency',
             Tuple(
                 title=_("I/O Log Writes Average Latency"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('ms'), default_value=5.0),
                     Float(title=_("Critical at"), unit=_('ms'), default_value=10.0)
                 ],
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msx_database",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msx_database,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_database,
        title=lambda: _("MS Exchange Database"),
    ))
