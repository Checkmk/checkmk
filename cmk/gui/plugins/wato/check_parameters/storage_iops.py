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
    RulespecGroupCheckParametersStorage,
)


@rulespec_registry.register
class RulespecCheckgroupParametersStorageIops(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "storage_iops"

    @property
    def title(self):
        return _("I/O operations for DDN S2A devices")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("read",
             Tuple(
                 title=_(u"Read IO operations per second"),
                 elements=[
                     Float(title=_(u"Warning at"), unit="1/s"),
                     Float(title=_(u"Critical at"), unit="1/s"),
                 ],
             )),
            ("write",
             Tuple(
                 title=_(u"Write IO operations per second"),
                 elements=[
                     Float(title=_(u"Warning at"), unit="1/s"),
                     Float(title=_(u"Critical at"), unit="1/s"),
                 ],
             )),
            ("total",
             Tuple(
                 title=_(u"Total IO operations per second"),
                 elements=[
                     Float(title=_(u"Warning at"), unit="1/s"),
                     Float(title=_(u"Critical at"), unit="1/s"),
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_(u"Port index or 'Total'"))
