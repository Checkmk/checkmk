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
    ListOf,
    MonitoringState,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _phase_elements():
    return [
        ("voltage",
         Tuple(
             title=_("Voltage"),
             elements=[
                 Integer(title=_("warning if below"), unit=u"V", default_value=210),
                 Integer(title=_("critical if below"), unit=u"V", default_value=200),
             ],
         )),
        ("power",
         Tuple(
             title=_("Power"),
             elements=[
                 Integer(title=_("warning at"), unit=u"W", default_value=1000),
                 Integer(title=_("critical at"), unit=u"W", default_value=1200),
             ],
         )),
        ("appower",
         Tuple(
             title=_("Apparent Power"),
             elements=[
                 Integer(title=_("warning at"), unit=u"VA", default_value=1100),
                 Integer(title=_("critical at"), unit=u"VA", default_value=1300),
             ],
         )),
        ("current",
         Tuple(
             title=_("Current"),
             elements=[
                 Integer(title=_("warning at"), unit=u"A", default_value=5),
                 Integer(title=_("critical at"), unit=u"A", default_value=10),
             ],
         )),
        ("frequency",
         Tuple(
             title=_("Frequency"),
             elements=[
                 Integer(title=_("warning if below"), unit=u"Hz", default_value=45),
                 Integer(title=_("critical if below"), unit=u"Hz", default_value=40),
                 Integer(title=_("warning if above"), unit=u"Hz", default_value=55),
                 Integer(title=_("critical if above"), unit=u"Hz", default_value=60),
             ],
         )),
        ("differential_current_ac",
         Tuple(
             title=_("Differential current AC"),
             elements=[
                 Float(title=_("warning at"), unit=u"mA", default_value=3.5),
                 Float(title=_("critical at"), unit=u"mA", default_value=30),
             ],
         )),
        ("differential_current_dc",
         Tuple(
             title=_("Differential current DC"),
             elements=[
                 Float(title=_("warning at"), unit=u"mA", default_value=70),
                 Float(title=_("critical at"), unit=u"mA", default_value=100),
             ],
         )),
    ]


@rulespec_registry.register
class RulespecCheckgroupParametersElInphase(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "el_inphase"

    @property
    def title(self):
        return _("Parameters for input phases of UPSs and PDUs")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_(
                "This rule allows you to specify levels for the voltage, current, power "
                "and apparent power of your device. The levels will only be applied if the device "
                "actually supplies values for these parameters."),
            elements=_phase_elements() + [
                ("map_device_states",
                 ListOf(
                     Tuple(elements=[TextAscii(size=10), MonitoringState()]),
                     title=_("Map device state"),
                     help=_("Here you can enter either device state number (eg. from SNMP devices) "
                            "or exact device state name and the related monitoring state."),
                 )),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Input Name"),
                         help=_("The name of the input, e.g. <tt>Phase 1</tt>"))


@rulespec_registry.register
class RulespecCheckgroupParametersUpsOutphase(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "ups_outphase"

    @property
    def title(self):
        return _("Parameters for output phases of UPSs and PDUs")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_(
                "This rule allows you to specify levels for the voltage, current, load, power "
                "and apparent power of your device. The levels will only be applied if the device "
                "actually supplies values for these parameters."),
            elements=_phase_elements() + [
                ("load",
                 Tuple(title=_("Load"),
                       elements=[
                           Integer(title=_("warning at"), unit=u"%", default_value=80),
                           Integer(title=_("critical at"), unit=u"%", default_value=90),
                       ])),
                ("map_device_states",
                 ListOf(
                     Tuple(elements=[TextAscii(size=10), MonitoringState()]),
                     title=_("Map device state"),
                     help=_("Here you can enter either device state number (eg. from SNMP devices) "
                            "or exact device state name and the related monitoring state."),
                 )),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Output Name"),
                         help=_("The name of the output, e.g. <tt>Phase 1</tt>/<tt>PDU 1</tt>"))
