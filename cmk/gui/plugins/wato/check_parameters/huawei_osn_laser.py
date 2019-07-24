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
    Tuple,
    Integer,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


@rulespec_registry.register
class RulespecCheckgroupParametersHuaweiOsnLaser(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "huawei_osn_laser"

    @property
    def title(self):
        return _("OSN Laser attenuation")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ('levels_low_in',
             Tuple(
                 title=_('Levels for laser input'),
                 default_value=(-160.0, -180.0),
                 elements=[
                     Integer(title=_("Warning below")),
                     Integer(title=_("Critical below")),
                 ],
             )),
            ('levels_low_out',
             Tuple(
                 title=_('Levels for laser output'),
                 default_value=(-160.0, -180.0),
                 elements=[
                     Integer(title=_("Warning below")),
                     Integer(title=_("Critical below")),
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Laser id"))
