#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsOS
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DictionaryElements,
    DropdownChoice,
    Password,
    TextInput,
    Transform,
)


def _special_agents_ipmi_sensors_vs_ipmi_common_elements() -> DictionaryElements:
    return [
        (
            "username",
            TextInput(
                title=_("Username"),
                allow_empty=False,
            ),
        ),
        (
            "password",
            Password(
                title=_("Password"),
                allow_empty=False,
            ),
        ),
    ]


def _special_agents_ipmi_sensors_transform_ipmi_sensors(params):
    # Note that the key privilege_lvl was once a common element with free text as input and now it
    # is tool-specific and a dropdown menu. However, we do not need a transform for this. Either
    # the user anyway entered a valid choice or the special agent crashed. There is no good way of
    # transforming an invalid choice to a valid choice. Instead, the user has to fix this manually
    # by editing the rule.
    if isinstance(params, dict):
        return ("freeipmi", params)
    return params


def _special_agents_ipmi_sensors_vs_freeipmi() -> Dictionary:
    return Dictionary(
        elements=[
            *_special_agents_ipmi_sensors_vs_ipmi_common_elements(),
            (
                "privilege_lvl",
                DropdownChoice(
                    title=_("Privilege Level"),
                    choices=[
                        ("user", "USER"),
                        ("operator", "OPERATOR"),
                        ("admin", "ADMIN"),
                    ],
                    default_value="operator",
                ),
            ),
            (
                "ipmi_driver",
                TextInput(
                    title=_("IPMI driver"),
                ),
            ),
            (
                "driver_type",
                TextInput(
                    title=_("IPMI driver type"),
                    help=_("Driver type to use instead of doing an auto selection"),
                ),
            ),
            (
                "BMC_key",
                TextInput(
                    title=_("BMC key"),
                    help=_(
                        "K_g BMC key to use when authenticating with the remote host for IPMI 2.0"
                    ),
                ),
            ),
            (
                "quiet_cache",
                Checkbox(
                    title=_("Quiet cache"),
                    label=_("Enable"),
                    help=("Do not output information about cache creation/deletion"),
                ),
            ),
            (
                "sdr_cache_recreate",
                Checkbox(
                    title=_("SDR cache recreate"),
                    label=_("Enable"),
                    help=_("Automatically recreate the sensor data repository (SDR) cache"),
                ),
            ),
            (
                "interpret_oem_data",
                Checkbox(
                    title=_("OEM data interpretation"),
                    label=_("Enable"),
                    help=_("Attempt to interpret OEM data"),
                ),
            ),
            (
                "output_sensor_state",
                Checkbox(
                    title=_("Sensor state"),
                    label=_("Enable"),
                    help=_("Output sensor state"),
                ),
            ),
            (
                "output_sensor_thresholds",
                Checkbox(
                    title=_("Sensor threshold"),
                    label=_("Enable"),
                    help=_("Output sensor thresholds"),
                ),
            ),
            (
                "ignore_not_available_sensors",
                Checkbox(
                    title=_("Suppress not available sensors"),
                    label=_("Enable"),
                    help=_("Ignore not-available (i.e. N/A) sensors in output"),
                ),
            ),
        ],
        optional_keys=[
            "ipmi_driver",
            "driver_type",
            "quiet_cache",
            "sdr_cache_recreate",
            "interpret_oem_data",
            "output_sensor_state",
            "output_sensor_thresholds",
            "ignore_not_available_sensors",
            "BMC_key",
        ],
    )


def _special_agents_ipmi_sensors_vs_ipmitool() -> Dictionary:
    return Dictionary(
        elements=[
            *_special_agents_ipmi_sensors_vs_ipmi_common_elements(),
            (
                "privilege_lvl",
                DropdownChoice(
                    title=_("Privilege Level"),
                    choices=[
                        ("callback", "CALLBACK"),
                        ("user", "USER"),
                        ("operator", "OPERATOR"),
                        ("administrator", "ADMINISTRATOR"),
                    ],
                    default_value="administrator",
                ),
            ),
            (
                "intf",
                DropdownChoice(
                    title=_("IPMI Interface"),
                    help=_(
                        "IPMI Interface to be used. If not specified, the default interface as set "
                        "at compile time will be used."
                    ),
                    choices=[
                        ("open", "open - Linux OpenIPMI Interface (default)"),
                        ("imb", "imb - Intel IMB Interface"),
                        ("lan", "lan - IPMI v1.5 LAN Interface"),
                        ("lanplus", "lanplus - IPMI v2.0 RMCP+ LAN Interface"),
                    ],
                ),
            ),
        ],
        optional_keys=[
            "intf",
        ],
    )


def _valuespec_special_agents_ipmi_sensors() -> Transform:
    return Transform(
        valuespec=CascadingDropdown(
            choices=[
                ("freeipmi", _("Use FreeIPMI"), _special_agents_ipmi_sensors_vs_freeipmi()),
                ("ipmitool", _("Use IPMItool"), _special_agents_ipmi_sensors_vs_ipmitool()),
            ],
            title=_("IPMI Sensors via Freeipmi or IPMItool"),
            help=_(
                "This rule selects the Agent IPMI Sensors instead of the normal Check_MK Agent "
                "which collects the data through the FreeIPMI resp. IPMItool command"
            ),
        ),
        forth=_special_agents_ipmi_sensors_transform_ipmi_sensors,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name="special_agents:ipmi_sensors",
        valuespec=_valuespec_special_agents_ipmi_sensors,
    )
)
