#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict

from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import (
    Dictionary,
    Float,
    Integer,
    ListOf,
    MonitoringState,
    TextAscii,
    Transform,
    Tuple,
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


def _item_spec_el_inphase():
    return TextAscii(title=_("Input Name"), help=_("The name of the input, e.g. <tt>Phase 1</tt>"))


def _parameter_valuespec_el_inphase():
    return Dictionary(
        help=_("This rule allows you to specify levels for the voltage, current, power "
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


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="el_inphase",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_el_inphase,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_el_inphase,
        title=lambda: _("Parameters for input phases of UPSs and PDUs"),
    ))


def _item_spec_ups_outphase():
    return TextAscii(title=_("Output Name"),
                     help=_("The name of the output, e.g. <tt>Phase 1</tt>/<tt>PDU 1</tt>"))


def _transform_parameter_valuespec_ups_outphase(params: Dict[str, Any]) -> Dict[str, Any]:
    changed_keys = {"load": "output_load"}
    return {changed_keys.get(k, k): v for k, v in params.items()}


def _parameter_valuespec_ups_outphase() -> Transform:
    return Transform(
        Dictionary(
            help=_(
                "This rule allows you to specify levels for the voltage, current, load, power "
                "and apparent power of your device. The levels will only be applied if the device "
                "actually supplies values for these parameters."),
            elements=_phase_elements() + [
                ("output_load",
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
        ),
        forth=_transform_parameter_valuespec_ups_outphase,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ups_outphase",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_ups_outphase,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ups_outphase,
        title=lambda: _("Parameters for output phases of UPSs and PDUs"),
    ))
