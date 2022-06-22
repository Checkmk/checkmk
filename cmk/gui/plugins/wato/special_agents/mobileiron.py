#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    Integer,
    ListOf,
    ListOfStrings,
    NetworkPort,
    RegExp,
    TextInput,
)


def _valuespec_special_agents_mobileiron():

    return Dictionary(
        help=_(
            "Requests data from Mobileiron API and outputs a piggyback host per returned device."
        ),
        elements=[
            ("username", TextInput(title=_("Username"), allow_empty=False)),
            ("password", IndividualOrStoredPassword(title=_("Password"), allow_empty=False)),
            (
                "port",
                NetworkPort(
                    title=_("Port"),
                    default_value=443,
                    help=_("The port that is used for the API call."),
                ),
            ),
            (
                "no-cert-check",
                FixedValue(
                    True,
                    title=_("Disable SSL certificate validation"),
                    totext=_("SSL certificate validation is disabled"),
                ),
            ),
            (
                "partition",
                ListOfStrings(
                    allow_empty=False,
                    title=_("Retrieve information about the following partitions"),
                ),
            ),
            (
                "proxy_details",
                Dictionary(
                    title=_("Use proxy for MobileIron API connection"),
                    elements=[
                        ("proxy_host", TextInput(title=_("Proxy host"), allow_empty=True)),
                        ("proxy_port", Integer(title=_("Port"))),
                        (
                            "proxy_user",
                            TextInput(
                                title=_("Username"),
                                size=32,
                            ),
                        ),
                        ("proxy_password", IndividualOrStoredPassword(title=_("Password"))),
                    ],
                    optional_keys=["proxy_port", "proxy_user", "proxy_password"],
                ),
            ),
            (
                "key-fields",
                DropdownChoice(
                    title=_("Field(s) to use as a hostname key"),
                    choices=[
                        (("serialNumber",), "serialNumber"),
                        (("emailAddress",), "emailAddress"),
                        (("emailAddress", "serialNumber"), "emailAddress and serialNumber"),
                        (("deviceModel", "serialNumber"), "deviceModel and serialNumber"),
                        (("uid",), "uid"),
                        (("uid", "serialNumber"), "uid and serialNumber"),
                        (("guid",), "guid"),
                    ],
                    help=_("Compound fields will be joined with a '-' symbol."),
                    default_value=("deviceModel", "serialNumber"),
                ),
            ),
            (
                "android-regex",
                ListOf(
                    valuespec=RegExp(
                        mode=RegExp.infix, title=_("Pattern"), allow_empty=False, default_value=".*"
                    ),
                    title=_("Add android hostnames matching"),
                    add_label=_("Add new pattern"),
                    allow_empty=False,
                    default_value=[".*"],
                    help=_(
                        "You can specify a list of regex patterns for android hostnames. "
                        "Several patterns can be provided. "
                        "If hostname contains '@' it will be removed with all following characters. "
                        "And only then the regex matching will happen. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all hostnames are accepted"
                    ),
                ),
            ),
            (
                "ios-regex",
                ListOf(
                    valuespec=RegExp(
                        mode=RegExp.infix, title=_("Pattern"), allow_empty=False, default_value=".*"
                    ),
                    title=_("Add iOS hostnames matching"),
                    add_label=_("Add new pattern"),
                    allow_empty=False,
                    default_value=[".*"],
                    help=_(
                        "You can specify a list of regex patterns for iOS hostnames. "
                        "Several patterns can be provided. "
                        "If hostname contains '@' it will be removed with all following characters. "
                        "And only then the regex matching will happen. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all hostnames are accepted"
                    ),
                ),
            ),
            (
                "others-regex",
                ListOf(
                    valuespec=RegExp(
                        mode=RegExp.infix, title=_("Pattern"), allow_empty=False, default_value=".*"
                    ),
                    title=_("Add other (not android and not iOS) hostnames matching"),
                    add_label=_("Add new pattern"),
                    allow_empty=False,
                    default_value=[".*"],
                    help=_(
                        "You can specify a list of regex patterns for other hostnames "
                        "which are not android and not iOS. "
                        "Several patterns can be provided. "
                        "If hostname contains '@' it will be removed with all following characters. "
                        "And only then the regex matching will happen. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all hostnames are accepted"
                    ),
                ),
            ),
        ],
        optional_keys=["no-cert-check"],
        title=_("MobileIron API"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:mobileiron",
        valuespec=_valuespec_special_agents_mobileiron,
    )
)
