#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Float,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    HostRulespec,
)


def transform_ipmi_inventory_rules(p):
    if not isinstance(p, dict):
        return p
    if p.get("summarize", True):
        return 'summarize'
    if p.get('ignored_sensors', []):
        return ('single', {'ignored_sensors': p["ignored_sensors"]})
    return ('single', {})


def _valuespec_inventory_ipmi_rules():
    return Transform(
        CascadingDropdown(
            title=_("Discovery of IPMI sensors"),
            orientation="vertical",
            choices=[
                ("summarize", _("Summary")),
                ("single", _("Single"),
                 Dictionary(elements=[
                     ("ignored_sensors",
                      ListOfStrings(
                          title=_("Ignore the following IPMI sensors"),
                          help=_("Names of IPMI sensors that should be ignored during discovery."
                                 "The pattern specified here must match exactly the beginning of "
                                 "the actual sensor name (case sensitive)."),
                          orientation="horizontal")),
                     ("ignored_sensorstates",
                      ListOfStrings(
                          title=_("Ignore the following IPMI sensor states"),
                          help=
                          _("IPMI sensors with these states that should be ignored during discovery."
                            "The pattern specified here must match exactly the beginning of "
                            "the actual sensor state (case sensitive)."),
                          orientation="horizontal",
                      )),
                 ]))
            ]),
        forth=transform_ipmi_inventory_rules,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="inventory_ipmi_rules",
        valuespec=_valuespec_inventory_ipmi_rules,
    ))


def _parameter_valuespec_ipmi():
    return Dictionary(
        elements=[
            ("sensor_states",
             ListOf(
                 Tuple(elements=[TextAscii(), MonitoringState()],),
                 title=_("Set states of IPMI sensor status texts"),
                 help=_("The pattern specified here must match exactly the beginning of "
                        "the sensor state (case sensitive)."),
             )),
            ("ignored_sensors",
             ListOfStrings(title=_("Ignore the following IPMI sensors (only summary)"),
                           help=_("Names of IPMI sensors that should be ignored when summarizing."
                                  "The pattern specified here must match exactly the beginning of "
                                  "the actual sensor name (case sensitive)."),
                           orientation="horizontal")),
            ("ignored_sensorstates",
             ListOfStrings(
                 title=_("Ignore the following IPMI sensor states (only summary)"),
                 help=_("IPMI sensors with these states that should be ignored when summarizing."
                        "The pattern specified here must match exactly the beginning of "
                        "the actual sensor state (case sensitive)."),
                 orientation="horizontal",
                 default_value=["nr", "ns"],
             )),
            ("numerical_sensor_levels",
             ListOf(Tuple(elements=[
                 TextAscii(title=_("Sensor name (only summary)"),
                           help=_(
                               "In summary mode you have to state the sensor name. "
                               "In single mode the sensor name comes from service description.")),
                 Dictionary(elements=[
                     ("lower", Tuple(
                         title=_("Lower levels"),
                         elements=[Float(), Float()],
                     )),
                     ("upper", Tuple(
                         title=_("Upper levels"),
                         elements=[Float(), Float()],
                     )),
                 ],),
             ],),
                    title=_("Set lower and upper levels for numerical sensors"))),
        ],
        ignored_keys=["ignored_sensors", "ignored_sensor_states"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ipmi",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextAscii(title=_("The sensor name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ipmi,
        title=lambda: _("IPMI sensors"),
    ))
