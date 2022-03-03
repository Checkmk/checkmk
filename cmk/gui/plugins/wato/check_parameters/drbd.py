#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListOf,
    MonitoringState,
    TextInput,
    Tuple,
)


def _parameter_valuespec_drbd():
    return Dictionary(
        ignored_keys=[
            "roles_inventory",
            "diskstates_inventory",
        ],
        elements=[
            (
                "roles",
                Alternative(
                    title=_("Roles"),
                    elements=[
                        FixedValue(value=None, totext="", title=_("Do not monitor")),
                        ListOf(
                            Tuple(
                                orientation="horizontal",
                                elements=[
                                    DropdownChoice(
                                        title=_("DRBD shows up as"),
                                        default_value="running",
                                        choices=[
                                            ("primary_secondary", _("Primary / Secondary")),
                                            ("primary_primary", _("Primary / Primary")),
                                            ("secondary_primary", _("Secondary / Primary")),
                                            ("secondary_secondary", _("Secondary / Secondary")),
                                        ],
                                    ),
                                    MonitoringState(
                                        title=_("Resulting state"),
                                    ),
                                ],
                                default_value=("ignore", 0),
                            ),
                            title=_("Set roles"),
                            add_label=_("Add role rule"),
                        ),
                    ],
                ),
            ),
            (
                "diskstates",
                Alternative(
                    title=_("Diskstates"),
                    elements=[
                        FixedValue(value=None, totext="", title=_("Do not monitor")),
                        ListOf(
                            Tuple(
                                elements=[
                                    DropdownChoice(
                                        title=_("Diskstate"),
                                        choices=[
                                            ("primary_Diskless", _("Primary - Diskless")),
                                            ("primary_Attaching", _("Primary - Attaching")),
                                            ("primary_Failed", _("Primary - Failed")),
                                            ("primary_Negotiating", _("Primary - Negotiating")),
                                            ("primary_Inconsistent", _("Primary - Inconsistent")),
                                            ("primary_Outdated", _("Primary - Outdated")),
                                            ("primary_DUnknown", _("Primary - DUnknown")),
                                            ("primary_Consistent", _("Primary - Consistent")),
                                            ("primary_UpToDate", _("Primary - UpToDate")),
                                            ("secondary_Diskless", _("Secondary - Diskless")),
                                            ("secondary_Attaching", _("Secondary - Attaching")),
                                            ("secondary_Failed", _("Secondary - Failed")),
                                            ("secondary_Negotiating", _("Secondary - Negotiating")),
                                            (
                                                "secondary_Inconsistent",
                                                _("Secondary - Inconsistent"),
                                            ),
                                            ("secondary_Outdated", _("Secondary - Outdated")),
                                            ("secondary_DUnknown", _("Secondary - DUnknown")),
                                            ("secondary_Consistent", _("Secondary - Consistent")),
                                            ("secondary_UpToDate", _("Secondary - UpToDate")),
                                        ],
                                    ),
                                    MonitoringState(title=_("Resulting state")),
                                ],
                                orientation="horizontal",
                            ),
                            title=_("Set diskstates"),
                            add_label=_("Add diskstate rule"),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="drbd",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("DRBD device")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_drbd,
        title=lambda: _("DR:BD roles and diskstates"),
    )
)
