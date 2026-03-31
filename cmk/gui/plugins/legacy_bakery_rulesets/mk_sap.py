#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    ListOf,
    ListOfStrings,
    TextInput,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_sap() -> Alternative:
    return Alternative(
        title=_("SAP R/3 monitoring plug-in"),
        help=_(
            "This rule set will deploy the agent plug-in <tt>mk_sap</tt> for (locally) monitoring "
            "SAP R/3 instances. Note: you still need to manually deploy the SAP NetWeaver RFCSDK (nwrfcsdk) "
            "and the Python module sapnwrfc."
        ),
        default_value={
            "instances": [
                {
                    "ashost": "localhost",
                    "sysnr": "00",
                    "client": "100",
                    "user": "cmk-user",
                    "passwd": "thiswontworkanyway",
                    "trace": "3",
                    "lang": "EN",
                }
            ],
            "paths": [
                "SAP BI Monitors/BI Monitor",
                "SAP BI Monitors/BI Monitor/*/Oracle/Performance",
                "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*",
                "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/CPU_Utilization",
            ],
        },
        elements=[
            Dictionary(
                title=_("Deploy the SAP R/3 plug-in"),
                optional_keys=False,
                elements=[
                    (
                        "instances",
                        ListOf(
                            valuespec=Dictionary(
                                optional_keys=["host_prefix"],
                                elements=[
                                    (
                                        "ashost",
                                        TextInput(
                                            title=_("Host name"),
                                            default_value="localhost",
                                            allow_empty=False,
                                        ),
                                    ),
                                    (
                                        "sysnr",
                                        TextInput(
                                            title=_("System Number"),
                                            size=2,
                                            default_value="00",
                                            regex="^[0-9][0-9]$",
                                            regex_error=_("The system number is two digits"),
                                        ),
                                    ),
                                    (
                                        "client",
                                        TextInput(
                                            title=_("SAP-Client"),
                                            size=3,
                                            default_value="100",
                                            allow_empty=False,
                                        ),
                                    ),
                                    (
                                        "user",
                                        TextInput(
                                            title=_("User for login"),
                                            default_value="cmk-user",
                                            allow_empty=False,
                                        ),
                                    ),
                                    (
                                        "passwd",
                                        MigrateToIndividualOrStoredPassword(
                                            title=_("Password for login"),
                                            allow_empty=False,
                                        ),
                                    ),
                                    (
                                        "trace",
                                        TextInput(
                                            title=_("Trace level"),
                                            size=1,
                                            default_value="3",
                                            regex="^[1-9]$",
                                            regex_error=_("Allowed is 1 ... 9"),
                                        ),
                                    ),
                                    # ( 'loglevel': 'warn', ), # hard coded to "warn" currently. Found no docu about other levels
                                    (
                                        "lang",
                                        TextInput(
                                            title=_("Language"),
                                            size=2,
                                            default_value="EN",
                                            regex="^[A-Z][A-Z]$",
                                            regex_error=_(
                                                "Specify two upper case letters like <tt>EN</tt> or <tt>DE</tt>."
                                            ),
                                        ),
                                    ),
                                    (
                                        "host_prefix",
                                        TextInput(title=_("Prefix for piggyback host name")),
                                    ),
                                ],
                            ),
                            title=_("Instances to monitor"),
                            add_label=_("Add instance to monitor"),
                            movable=False,
                        ),
                    ),
                    (
                        "paths",
                        ListOfStrings(
                            title=_("CCMS paths to monitor"),
                            help=_(
                                "Specify the paths in CCMS that you want to monitor. Each entry must match the full path to one or"
                                " several monitor objects. We use Unix shell patterns during matching, so"
                                " you can use several chars as placeholders:<ul>"
                                "<li><tt>* </tt> matches everything</li>"
                                "<li><tt>?</tt> matches any single character</li>"
                                "<li><tt>[seq]</tt> matches any character in seq</li>"
                                "<li><tt>[!seq]</tt> matches any character not in seq</li>"
                                "</ul>"
                            ),
                            size=100,
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the SAP R/3 plug-in"),
                totext=_("disabled"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_sap"),
        valuespec=_valuespec_agent_config_mk_sap,
    )
)
