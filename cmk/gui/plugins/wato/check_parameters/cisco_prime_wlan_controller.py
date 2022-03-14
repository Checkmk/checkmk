#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Age, Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_wlan_controllers_clients():
    return Dictionary(
        elements=[
            (
                "clients",
                Tuple(
                    title=_("Maximum number of clients"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_prime_wlan_controller_clients",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("Clients")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_wlan_controllers_clients,
        title=lambda: _("Cisco Prime WLAN Controller Clients"),
    )
)


def _parameter_valuespec_wlan_controllers_access_points():
    return Dictionary(
        elements=[
            (
                "access_points",
                Tuple(
                    title=_("Maximum number of access points"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_prime_wlan_controller_access_points",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("Access points")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_wlan_controllers_access_points,
        title=lambda: _("Cisco Prime WLAN Controller Access Points"),
    )
)


def _parameter_valuespec_wlan_controllers_last_backup():
    return Dictionary(
        elements=[
            (
                "last_backup",
                Tuple(
                    title=_("Time since last backup"),
                    elements=[
                        Age(
                            title=_("Warning at"),
                            display=["days", "hours", "minutes"],
                            default_value=7 * 24 * 3600,
                        ),
                        Age(
                            title=_("Critical at"),
                            display=["days", "hours", "minutes"],
                            default_value=30 * 24 * 3600,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_prime_wlan_controller_last_backup",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("Last backup")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_wlan_controllers_last_backup,
        title=lambda: _("Cisco Prime WLAN Controller Last Backup"),
    )
)
