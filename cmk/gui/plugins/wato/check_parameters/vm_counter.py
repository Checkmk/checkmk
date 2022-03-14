#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import DropdownChoice


def _item_spec_vm_counter():
    return DropdownChoice(
        title=_("kernel counter"),
        choices=[
            ("Context Switches", _("Context Switches")),
            ("Process Creations", _("Process Creations")),
            ("Major Page Faults", _("Major Page Faults")),
        ],
    )


def _parameter_valuespec_vm_counter():
    return Levels(
        help=_(
            "This ruleset applies to several similar checks measing various kernel "
            "events like context switches, process creations and major page faults. "
            "Please create separate rules for each type of kernel counter you "
            "want to set levels for."
        ),
        unit=_("events per second"),
        default_levels=(1000, 5000),
        default_difference=(500.0, 1000.0),
        default_value=None,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="vm_counter",
        group=RulespecGroupCheckParametersOperatingSystem,
        is_deprecated=True,
        item_spec=_item_spec_vm_counter,
        parameter_valuespec=_parameter_valuespec_vm_counter,
        title=lambda: _("Number of kernel events per second"),
    )
)
