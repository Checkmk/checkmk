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
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.check_parameters.utils import filesystem_elements


@rulespec_registry.register
class RulespecCheckgroupParametersIbmSvcMdiskgrp(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "ibm_svc_mdiskgrp"

    @property
    def title(self):
        return _("IBM SVC Pool Capacity")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=filesystem_elements + [
                ("provisioning_levels",
                 Tuple(
                     title=_("Provisioning Levels"),
                     help=_("A provisioning of over 100% means over provisioning."),
                     elements=[
                         Percentage(title=_("Warning at a provisioning of"),
                                    default_value=110.0,
                                    maxvalue=None),
                         Percentage(title=_("Critical at a provisioning of"),
                                    default_value=120.0,
                                    maxvalue=None),
                     ],
                 )),
            ],
            hidden_keys=["flex_levels"],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Name of the pool"), allow_empty=False)
