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
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _item_spec_ibm_svc_total_latency():
    return DropdownChoice(
        choices=[
            ("Drives", _("Total latency for all drives")),
            ("MDisks", _("Total latency for all MDisks")),
            ("VDisks", _("Total latency for all VDisks")),
        ],
        title=_("Disk/Drive type"),
        help=_("Please enter <tt>Drives</tt>, <tt>Mdisks</tt> or <tt>VDisks</tt> here."),
    )


def _parameter_valuespec_ibm_svc_total_latency():
    return Dictionary(
        elements=[
            (
                "read",
                Levels(
                    title=_("Read latency"),
                    unit=_("ms"),
                    default_value=None,
                    default_levels=(50.0, 100.0),
                ),
            ),
            (
                "write",
                Levels(
                    title=_("Write latency"),
                    unit=_("ms"),
                    default_value=None,
                    default_levels=(50.0, 100.0),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_svc_total_latency",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ibm_svc_total_latency,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_svc_total_latency,
        title=lambda: _("IBM SVC Total Disk Latency"),
    )
)
