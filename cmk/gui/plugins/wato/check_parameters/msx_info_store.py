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
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersMsxInfoStore(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "msx_info_store"

    @property
    def title(self):
        return _("MS Exchange Information Store")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            title=_("Set Levels"),
            elements=[('store_latency',
                       Tuple(
                           title=_("Average latency for store requests"),
                           elements=[
                               Float(title=_("Warning at"), unit=_('ms'), default_value=40.0),
                               Float(title=_("Critical at"), unit=_('ms'), default_value=50.0)
                           ],
                       )),
                      ('clienttype_latency',
                       Tuple(
                           title=_("Average latency for client type requests"),
                           elements=[
                               Float(title=_("Warning at"), unit=_('ms'), default_value=40.0),
                               Float(title=_("Critical at"), unit=_('ms'), default_value=50.0)
                           ],
                       )),
                      ('clienttype_requests',
                       Tuple(
                           title=_("Maximum number of client type requests per second"),
                           elements=[
                               Integer(title=_("Warning at"), unit=_('requests'), default_value=60),
                               Integer(title=_("Critical at"), unit=_('requests'), default_value=70)
                           ],
                       ))],
            optional_keys=[],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Store"),
            help=_("Specify the name of a store (This is either a mailbox or public folder)"))
