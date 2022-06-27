#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _valuespec_active_checks_notify_count():
    return Tuple(
        title=_("Check notification number per contact"),
        help=_(
            "Check the number of sent notifications per contact using the plugin <tt>check_notify_count</tt> "
            "provided with Check_MK. This plugin counts the total number of notifications sent by the local "
            "monitoring core and creates graphs for each individual contact. You can configure thresholds "
            "on the number of notifications per contact in a defined time interval. "
            "This plugin queries livestatus to extract the notification related log entries from the "
            "log file of your monitoring core."
        ),
        elements=[
            TextInput(
                title=_("Service Description"),
                help=_("The name that will be used in the service description"),
                allow_empty=False,
            ),
            Integer(
                title=_("Interval to monitor"),
                label=_("notifications within last"),
                unit=_("minutes"),
                minvalue=1,
                default_value=60,
            ),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "num_per_contact",
                        Tuple(
                            title=_("Thresholds for Notifications per Contact"),
                            elements=[
                                Integer(title=_("Warning if above"), default_value=20),
                                Integer(title=_("Critical if above"), default_value=50),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:notify_count",
        valuespec=_valuespec_active_checks_notify_count,
    )
)
