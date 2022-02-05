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
from cmk.gui.valuespec import ListOfStrings, TextInput


def _parameter_valuespec_fs_mount_options():
    return ListOfStrings(
        title=_("Expected mount options"),
        help=_(
            "Specify all expected mount options here. If the list of "
            "actually found options differs from this list, the check will go "
            "warning or critical. Just the option <tt>commit</tt> is being "
            "ignored since it is modified by the power saving algorithms."
        ),
        valuespec=TextInput(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fs_mount_options",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Mount point"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_fs_mount_options,
        title=lambda: _("Filesystem mount options (Linux/UNIX)"),
    )
)
