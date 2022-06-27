#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import FilesystemElements, vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Checkbox, FixedValue, TextInput


def _parameter_valuespec_netapp_luns():
    return vs_filesystem(
        elements=[
            FilesystemElements.levels,
            FilesystemElements.size_trend,
        ],
        extra_elements=[
            (
                "ignore_levels",
                FixedValue(
                    title=_("Ignore used space (this option disables any other options)"),
                    help=_(
                        "Some luns, e.g. jfs formatted, tend to report incorrect used space values"
                    ),
                    totext=_("Ignore used space"),
                    value=True,
                ),
            ),
            (
                "read_only",
                Checkbox(
                    title=_("LUN is read-only"),
                    help=_(
                        "Display a warning if a LUN is not read-only. Without "
                        "this setting a warning will be displayed if a LUN is "
                        "read-only."
                    ),
                    label=_("Enable"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_luns",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("LUN name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_luns,
        title=lambda: _("NetApp LUNs"),
    )
)
