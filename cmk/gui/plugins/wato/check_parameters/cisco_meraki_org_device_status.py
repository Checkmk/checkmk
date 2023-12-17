#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, MonitoringState, Tuple


def _parameter_valuespec_cisco_meraki_device_status() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "last_reported_upper_levels",
                Tuple(
                    title=_("Max time for last reported"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "status_map",
                Dictionary(
                    title=_("Map device status to monitoring state"),
                    elements=[
                        (
                            "online",
                            MonitoringState(
                                title=_('Monitoring state for device state "online"'),
                                default_value=0,
                            ),
                        ),
                        (
                            "alerting",
                            MonitoringState(
                                title=_('Monitoring state for device state "alerting"'),
                                default_value=2,
                            ),
                        ),
                        (
                            "offline",
                            MonitoringState(
                                title=_('Monitoring state for device state "offline"'),
                                default_value=1,
                            ),
                        ),
                        (
                            "dormant",
                            MonitoringState(
                                title=_('Monitoring state for device state "dormant"'),
                                default_value=1,
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cisco_meraki_org_device_status",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_cisco_meraki_device_status,
        title=lambda: _("Cisco Meraki Device status"),
        match_type="dict",
    )
)
