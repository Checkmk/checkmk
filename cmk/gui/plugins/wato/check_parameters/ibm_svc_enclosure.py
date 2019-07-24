#!/usr/bin/env python
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
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


@rulespec_registry.register
class RulespecCheckgroupParametersIbmSvcEnclosure(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "ibm_svc_enclosure"

    @property
    def title(self):
        return _("IBM SVC Enclosure")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[("levels_lower_online_canisters",
                                     Alternative(
                                         title="Lower levels for online canisters",
                                         style="dropdown",
                                         elements=[
                                             FixedValue(
                                                 False,
                                                 title=_("All must be online"),
                                                 totext="",
                                             ),
                                             Tuple(
                                                 title=_("Specify levels"),
                                                 elements=[
                                                     Integer(title=_("Warning below"),
                                                             minvalue=-1,
                                                             unit=_("online canisters")),
                                                     Integer(title=_("Critical below"),
                                                             minvalue=-1,
                                                             unit=_("online canisters")),
                                                 ],
                                             ),
                                         ],
                                     ))],)

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Name of enclosure"),
            help=_("Name of the enclosure, e.g. Enclosure 1"),
        )
