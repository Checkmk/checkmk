#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput


def _item_spec_prism_host_disks():
    return TextInput(
        title=_("Nutanix Disk name"),
        help=_("Name of the Nutanix disk"),
    )


def _parameter_valuespec_prism_host_disks():
    return Dictionary(
        elements=[
            (
                "mounted",
                DropdownChoice(
                    title=_("Disk mount state"),
                    choices=[
                        (True, _("Mounted")),
                        (False, _("Unmounted")),
                    ],
                    default_value=True,
                ),
            )
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_host_disks",
        group=RulespecGroupCheckParametersVirtualization,
        item_spec=_item_spec_prism_host_disks,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_host_disks,
        title=lambda: _("Nutanix Host Disk State"),
    )
)
