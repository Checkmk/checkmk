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
    RulespecGroupCheckParametersEnvironment,
)


def _item_spec_hp_msa_psu_voltage():
    return TextAscii(title=_("Power Supply name"), help=_("The identifier of the power supply."))


def _parameter_valuespec_hp_msa_psu_voltage():
    return Dictionary(
        help=_("Here you can configure the 3.3V and 12V voltage levels for each power supply."),
        elements=[
            ("levels_33v_lower",
             Tuple(
                 title=_("3.3 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                     Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                 ],
             )),
            ("levels_33v_upper",
             Tuple(
                 title=_("3.3 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                     Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                 ],
             )),
            ("levels_5v_lower",
             Tuple(
                 title=_("5 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                     Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                 ],
             )),
            ("levels_5v_upper",
             Tuple(
                 title=_("5 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                     Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                 ],
             )),
            ("levels_12v_lower",
             Tuple(
                 title=_("12 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=11.9),
                     Float(title=_("critical if below or equal"), unit="V", default_value=11.8),
                 ],
             )),
            ("levels_12v_upper",
             Tuple(
                 title=_("12 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=12.1),
                     Float(title=_("critical if above or equal"), unit="V", default_value=12.2),
                 ],
             ))
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hp_msa_psu_voltage",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_hp_msa_psu_voltage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hp_msa_psu_voltage,
        title=lambda: _("HP MSA Power Supply Voltage Levels"),
    ))
