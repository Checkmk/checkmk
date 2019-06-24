#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
    Tuple,
    Float,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersKernelPage(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "kernel_page"

    @property
    def title(self):
        return _("Kernel Page")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            (
                "page_swap_in_levels_lower",
                Tuple(
                    title=_("Swap In Lower"),
                    elements=[
                        Float(title=_("Swap In warning below"), unit=_("bytes/sec")),
                        Float(title=_("Swap In critical below"), unit=_("bytes/sec")),
                    ]),
            ),
            (
                "page_swap_in_levels",
                Tuple(
                    title=_("Swap In Upper"),
                    elements=[
                        Float(title=_("Swap In warning at"), unit=_("bytes/sec")),
                        Float(title=_("Swap In critical at"), unit=_("bytes/sec")),
                    ]),
            ),
            (
                "page_swap_out_levels_lower",
                Tuple(
                    title=_("Swap Out Lower"),
                    elements=[
                        Float(title=_("Swap Out warning below"), unit=_("bytes/sec")),
                        Float(title=_("Swap Out critical below"), unit=_("bytes/sec")),
                    ]),
            ),
            (
                "page_swap_out_levels",
                Tuple(
                    title=_("Swap Out Upper"),
                    elements=[
                        Float(title=_("Swap Out warning at"), unit=_("bytes/sec")),
                        Float(title=_("Swap Ount critical at"), unit=_("bytes/sec")),
                    ]),
            ),
        ])
