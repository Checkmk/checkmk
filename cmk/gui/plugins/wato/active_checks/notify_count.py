#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput, Tuple
from cmk.gui.wato import RulespecGroupIntegrateOtherServices
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_active_checks_notify_count() -> Migrate[dict[str, Any]]:
    return Migrate(
        migrate=lambda p: (
            p if isinstance(p, dict) else {"description": p[0], "interval": p[1], **p[2]}
        ),
        valuespec=Dictionary(
            title=_("Check notification number per contact"),
            help=_(
                "Check the number of sent notifications per contact using the plug-in <tt>check_notify_count</tt> "
                "provided with Checkmk. This plug-in counts the total number of notifications sent by the local "
                "monitoring core and creates graphs for each individual contact. You can configure thresholds "
                "on the number of notifications per contact in a defined time interval. "
                "This plug-in queries Livestatus to extract the notification related log entries from the "
                "log file of your monitoring core."
            ),
            elements=[
                (
                    "description",
                    TextInput(
                        title=_("Service name"),
                        help=_("The name that will be used in the service name"),
                        allow_empty=False,
                    ),
                ),
                (
                    "interval",
                    Integer(
                        title=_("Interval to monitor"),
                        label=_("notifications within last"),
                        unit=_("minutes"),
                        minvalue=1,
                        default_value=60,
                    ),
                ),
                (
                    "num_per_contact",
                    Tuple(
                        title=_("Thresholds for notifications per contact"),
                        elements=[
                            Integer(title=_("Warning if above"), default_value=20),
                            Integer(title=_("Critical if above"), default_value=50),
                        ],
                    ),
                ),
            ],
            optional_keys=["num_per_contact"],
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name=RuleGroup.ActiveChecks("notify_count"),
        valuespec=_valuespec_active_checks_notify_count,
    )
)
