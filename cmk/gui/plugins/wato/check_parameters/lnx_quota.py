#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Checkbox, Dictionary, TextInput


def _item_spec_lnx_quota():
    return TextInput(
        title=_("filesystem"),
        help=_("Name of filesystem with quotas enabled"),
    )


def _parameter_valuespec_lnx_quota():
    return Dictionary(
        optional_keys=False,
        elements=[
            (
                "user",
                Checkbox(
                    title=_("Monitor user quotas"),
                    label=_("Enable"),
                    default_value=True,
                ),
            ),
            (
                "group",
                Checkbox(
                    title=_("Monitor group quotas"),
                    label=_("Enable"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="lnx_quota",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_lnx_quota,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_lnx_quota,
        title=lambda: _("Linux quota check"),
    )
)
