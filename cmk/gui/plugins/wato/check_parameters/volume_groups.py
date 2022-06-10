#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import (
    get_free_used_dynamic_valuespec,
    match_dual_level_type,
    transform_filesystem_free,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, TextInput, Transform


def _parameter_valuespec_volume_groups():
    return Dictionary(
        elements=[
            (
                "levels",
                Alternative(
                    title=_("Levels for volume group"),
                    show_alternative_title=True,
                    default_value=(80.0, 90.0),
                    match=match_dual_level_type,
                    elements=[
                        get_free_used_dynamic_valuespec("used"),
                        Transform(
                            valuespec=get_free_used_dynamic_valuespec(
                                "free", default_value=(20.0, 10.0)
                            ),
                            title=_("Levels for volume group free space"),
                            forth=transform_filesystem_free,
                            back=transform_filesystem_free,
                        ),
                    ],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="volume_groups",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Volume Group"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_volume_groups,
        title=lambda: _("Volume Groups (LVM)"),
    )
)
