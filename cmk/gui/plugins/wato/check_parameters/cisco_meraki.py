#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, TextInput, Tuple


def _parameter_valuespec_cisco_meraki_org_licenses_overview():
    return Dictionary(
        title=_("Cisco Meraki Organisation Licenses Overview"),
        optional_keys=True,
        elements=[
            (
                "remaining_expiration_time",
                Tuple(
                    title=_("Lower levels for remaining expiration time of licenses"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        title=lambda: _("Cisco Meraki Organisation Licenses Overview"),
        check_group_name="cisco_meraki_org_licenses_overview",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_cisco_meraki_org_licenses_overview,
        item_spec=lambda: TextInput(
            title=_("The organisation ID"),
        ),
        match_type="dict",
    )
)
