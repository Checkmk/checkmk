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
    DropdownChoice,
    Float,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_ddn_s2a_wait():
    return DropdownChoice(title=_(u"Host or Disk"),
                          choices=[
                              ("Disk", _(u"Disk")),
                              ("Host", _(u"Host")),
                          ])


def _parameter_valuespec_ddn_s2a_wait():
    return Dictionary(elements=[
        ("read_avg",
         Tuple(
             title=_(u"Read wait average"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("read_min",
         Tuple(
             title=_(u"Read wait minimum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("read_max",
         Tuple(
             title=_(u"Read wait maximum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("write_avg",
         Tuple(
             title=_(u"Write wait average"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("write_min",
         Tuple(
             title=_(u"Write wait minimum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("write_max",
         Tuple(
             title=_(u"Write wait maximum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ddn_s2a_wait",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ddn_s2a_wait,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ddn_s2a_wait,
        title=lambda: _("Read/write wait for DDN S2A devices"),
    ))
