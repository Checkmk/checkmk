#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    MKUserError,
    RulespecGroupDatasourceProgramsApps,
)
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    HTTPProxyReference,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOf, ListOfStrings, RegExp, TextInput


def _validate_regex_choices(
    value: Mapping,
    varprefix: str,  # pylint: disable=unused-argument
) -> None:
    """At least one device type should be monitored."""

    if not any(regex in value for regex in ["android-regex", "ios-regex", "other-regex"]):
        raise MKUserError(
            "android-regex",
            _(
                "Please activate the monitoring of at least one device type: Android, iOS or other devices"
            ),
        )


def _valuespec_special_agents_mobileiron() -> Dictionary:
    return Dictionary(
        title=_("MobileIron API"),
        help=_(
            "Requests data from Mobileiron API and outputs a piggyback host per returned device."
        ),
        elements=[
            ("username", TextInput(title=_("Username"), allow_empty=False)),
            (
                "password",
                MigrateToIndividualOrStoredPassword(title=_("Password"), allow_empty=False),
            ),
            ("proxy", HTTPProxyReference()),
            (
                "partition",
                ListOfStrings(
                    allow_empty=False,
                    title=_("Retrieve information about the following partitions"),
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
                    title=_("Monitor Android devices"),
                    add_label=_("Add new pattern"),
                    allow_empty=False,
                    help=_(
                        "You can specify a list of regex patterns for android host names. "
                        "Several patterns can be provided. "
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
                    title=_("Monitor iOS devices"),
                    add_label=_("Add new pattern"),
                    allow_empty=False,
                    help=_(
                        "You can specify a list of regex patterns for iOS host names. "
                        "Several patterns can be provided. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all host names are accepted"
                    ),
                ),
            ),
            (
                "other-regex",
                ListOf(
                    valuespec=RegExp(
                        mode=RegExp.infix, title=_("Pattern"), allow_empty=False, default_value=".*"
                    ),
                    title=_("Monitor other than Android or iOS devices"),
                    add_label=_("Add new pattern"),
                    allow_empty=False,
                    help=_(
                        "You can specify a list of regex patterns for other host names "
                        "which are not android and not iOS. "
                        "Several patterns can be provided. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all host names are accepted"
                    ),
                ),
            ),
        ],
        optional_keys=[
            "port",
            "protocol",
            "no-cert-check",
            "proxy",
            "android-regex",
            "ios-regex",
            "other-regex",
        ],
        validate=_validate_regex_choices,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:mobileiron",
        valuespec=_valuespec_special_agents_mobileiron,
    )
)
