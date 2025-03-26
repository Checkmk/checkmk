#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import FilesystemElements, vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Float, Migrate, TextInput


def _item_spec_capacity() -> TextInput:
    return TextInput(
        title=_("Volume name"),
        help=_("To configure a rule for overall FlashArray capacity use 'Overall' as an item."),
    )


def _parameter_valuespec_capacity() -> Migrate:
    return vs_filesystem(
        elements=[
            FilesystemElements.levels_percent,
            FilesystemElements.magic_factor,
        ],
        extra_elements=[
            (
                "data_reduction",
                SimpleLevels(Float, title=_("Data reduction ratio lower limits")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="pure_storage_capacity",
        item_spec=_item_spec_capacity,
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_capacity,
        title=lambda: _("Pure Storage Capacity"),
    )
)
