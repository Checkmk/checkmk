#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_cisco_meraki_device_status_ps() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "state_not_powering",
                MonitoringState(
                    title=_('Monitoring state if power supply is not "powering"'),
                    default_value=1,
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_meraki_org_device_status_ps",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_cisco_meraki_device_status_ps,
        title=lambda: _("Cisco Meraki power supply"),
        item_spec=lambda: TextInput(title=_("The slot number")),
        match_type="dict",
    )
)
