#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import FilesystemElements, vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Migrate, TextInput


def _migrate_valuespec_sansymphony_pool(params):
    """Migrate to Checkmk version 2.2"""
    if isinstance(params, tuple):
        return {
            "levels": (float(params[0]), float(params[1])),
        }
    return params


def _parameter_valuespec_sansymphony_pool():
    return Migrate(
        valuespec=vs_filesystem(
            elements=[
                FilesystemElements.levels_percent,
                FilesystemElements.magic_factor,
            ]
        ),
        migrate=_migrate_valuespec_sansymphony_pool,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sansymphony_pool",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the pool"),
        ),
        parameter_valuespec=_parameter_valuespec_sansymphony_pool,
        title=lambda: _("Sansymphony pool allocation"),
    )
)
