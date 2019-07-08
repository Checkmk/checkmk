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
    Alternative,
    Dictionary,
    Filesize,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


@rulespec_registry.register
class RulespecCheckgroupParametersMemoryMultiitem(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersOperatingSystem

    @property
    def check_group_name(self):
        return "memory_multiitem"

    @property
    def title(self):
        return _("Main memory usage of devices with modules")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_(
                "The memory levels for one specific module of this host. This is relevant for hosts that have "
                "several distinct memory areas, e.g. pluggable cards"),
            elements=[
                ("levels",
                 Alternative(
                     title=_("Memory levels"),
                     elements=[
                         Tuple(
                             title=_("Specify levels in percentage of total RAM"),
                             elements=[
                                 Percentage(title=_("Warning at a memory usage of"),
                                            default_value=80.0,
                                            maxvalue=None),
                                 Percentage(title=_("Critical at a memory usage of"),
                                            default_value=90.0,
                                            maxvalue=None)
                             ],
                         ),
                         Tuple(
                             title=_("Specify levels in absolute usage values"),
                             elements=[
                                 Filesize(title=_("Warning at")),
                                 Filesize(title=_("Critical at"))
                             ],
                         ),
                     ],
                 )),
            ],
            optional_keys=[],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Module name"), allow_empty=False)
