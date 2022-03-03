#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Float,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextInput,
    Transform,
    Tuple,
)


def transform_ipmi_inventory_rules(p):
    # this rule once was a Dictionary, then it became a CascadingDropdown, now we are back to a
    # Dictionary
    if isinstance(p, dict):
        if "discovery_mode" in p:
            return p
        if p.get("summarize", True):
            return {
                "discovery_mode": (
                    "summarize",
                    {},
                ),
            }
        return {
            "discovery_mode": (
                "single",
                "ignored_sensors" in p and {"ignored_sensors": p["ignored_sensors"]} or {},
            ),
        }
    if p == "summarize":
        return {
            "discovery_mode": (
                "summarize",
                {},
            ),
        }
    return {
        "discovery_mode": p,
    }


def _valuespec_inventory_ipmi_rules_single() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "ignored_sensors",
                ListOfStrings(
                    title=_("Ignore the following IPMI sensors"),
                    help=_(
                        "Names of IPMI sensors that should be ignored during discovery. "
                        "The pattern specified here must match exactly the beginning of "
                        "the actual ensor name (case sensitive)."
                    ),
                    orientation="horizontal",
                ),
            ),
            (
                "ignored_sensorstates",
                ListOfStrings(
                    title=_("Ignore the following IPMI sensor states"),
                    help=_(
                        "IPMI sensors with these states that should be gnored during discovery. "
                        "The pattern specified here must match exactly the beginning of the actual "
                        "sensor state (case sensitive)."
                    ),
                    orientation="horizontal",
                ),
            ),
        ],
    )


def _valuespec_inventory_ipmi_rules() -> Transform:
    return Transform(
        Dictionary(
            title=_("IPMI sensor discovery"),
            elements=[
                (
                    "discovery_mode",
                    CascadingDropdown(
                        title=_("Discovery mode"),
                        orientation="vertical",
                        choices=[
                            (
                                "summarize",
                                _("Summary of all sensors"),
                                FixedValue(value={}, totext=""),
                            ),
                            (
                                "single",
                                _("One service per sensor"),
                                _valuespec_inventory_ipmi_rules_single(),
                            ),
                        ],
                        sorted=False,
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=transform_ipmi_inventory_rules,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="inventory_ipmi_rules",
        valuespec=_valuespec_inventory_ipmi_rules,
    )
)


def _parameter_valuespec_ipmi():
    return Dictionary(
        elements=[
            (
                "sensor_states",
                ListOf(
                    Tuple(
                        elements=[TextInput(), MonitoringState()],
                    ),
                    title=_("Set states of IPMI sensor status texts"),
                    help=_(
                        "The pattern specified here must match exactly the beginning of "
                        "the sensor state (case sensitive)."
                    ),
                ),
            ),
            (
                "ignored_sensors",
                ListOfStrings(
                    title=_("Ignore the following IPMI sensors (only summary)"),
                    help=_(
                        "Names of IPMI sensors that should be ignored when summarizing."
                        "The pattern specified here must match exactly the beginning of "
                        "the actual sensor name (case sensitive)."
                    ),
                    orientation="horizontal",
                ),
            ),
            (
                "ignored_sensorstates",
                ListOfStrings(
                    title=_("Ignore the following IPMI sensor states (only summary)"),
                    help=_(
                        "IPMI sensors with these states that should be ignored when summarizing."
                        "The pattern specified here must match exactly the beginning of "
                        "the actual sensor state (case sensitive)."
                    ),
                    orientation="horizontal",
                    default_value=["nr", "ns"],
                ),
            ),
            (
                "numerical_sensor_levels",
                ListOf(
                    Tuple(
                        elements=[
                            TextInput(
                                title=_("Sensor name"),
                                help=_(
                                    "Enter the name of the sensor. In single mode, this can be read off "
                                    "from the service descriptions of the services 'IPMI Sensor ...'."
                                ),
                            ),
                            Dictionary(
                                elements=[
                                    (
                                        "lower",
                                        Tuple(
                                            title=_("Lower levels"),
                                            elements=[
                                                Float(label=_("Warning at")),
                                                Float(label=_("Critical at")),
                                            ],
                                        ),
                                    ),
                                    (
                                        "upper",
                                        Tuple(
                                            title=_("Upper levels"),
                                            elements=[
                                                Float(label=_("Warning at")),
                                                Float(label=_("Critical at")),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    title=_("Set lower and upper levels for numerical sensors"),
                ),
            ),
        ],
        ignored_keys=["ignored_sensors", "ignored_sensor_states"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ipmi",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("The sensor name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ipmi,
        title=lambda: _("IPMI sensors"),
    )
)
