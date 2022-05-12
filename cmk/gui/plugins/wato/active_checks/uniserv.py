#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Integer, TextInput


def _valuespec_active_checks_uniserv():
    return Dictionary(
        title=_("Check uniserv service"),
        optional_keys=False,
        elements=[
            ("port", Integer(title=_("Port"))),
            (
                "service",
                TextInput(
                    title=_("Service Name"),
                    help=_(
                        "Enter the uniserve service name here (has nothing to do with service description)."
                    ),
                ),
            ),
            (
                "job",
                CascadingDropdown(
                    title=_("Mode of the Check"),
                    help=_(
                        "Choose, whether you just want to query the version number,"
                        " or if you want to check the response to an address query."
                    ),
                    choices=[
                        ("version", _("Check for Version")),
                        (
                            "address",
                            _("Check for an Address"),
                            Dictionary(
                                title=_("Address Check mode"),
                                optional_keys=False,
                                elements=[
                                    ("street", TextInput(title=_("Street name"))),
                                    ("street_no", Integer(title=_("Street number"))),
                                    ("city", TextInput(title=_("City name"))),
                                    (
                                        "search_regex",
                                        TextInput(
                                            title=_("Check City against Regex"),
                                            help=_(
                                                "The city name from the response will be checked against "
                                                "the regular expression specified here"
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        name="active_checks:uniserv",
        valuespec=_valuespec_active_checks_uniserv,
    )
)
