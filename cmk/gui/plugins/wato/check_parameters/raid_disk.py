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
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput, Transform


def _item_spec_raid_disk():
    return TextInput(
        title=_("Number or ID of the disk"),
        help=_(
            "How the disks are named depends on the type of hardware being "
            "used. Please look at already discovered checks for examples."
        ),
    )


def _parameter_valuespec_raid_disk():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "expected_state",
                    TextInput(
                        title=_("Expected state"),
                        help=_(
                            "State the disk is expected to be in. Typical good states "
                            "are online, host spare, OK and the like. The exact way of how "
                            "to specify a state depends on the check and hard type being used. "
                            "Please take examples from discovered checks for reference."
                        ),
                    ),
                ),
                (
                    "use_device_states",
                    DropdownChoice(
                        title=_("Use device states and overwrite expected status"),
                        choices=[
                            (False, _("Ignore")),
                            (True, _("Use device states")),
                        ],
                        default_value=True,
                    ),
                ),
            ],
        ),
        forth=lambda x: isinstance(x, str) and {"expected_state": x} or x,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="raid_disk",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_raid_disk,
        parameter_valuespec=_parameter_valuespec_raid_disk,
        title=lambda: _("RAID: state of a single disk"),
    )
)
