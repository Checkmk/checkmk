#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import FilesystemElements, vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import TextInput


def _parameter_valuespec_persistent_volume_claims():
    return vs_filesystem(
        elements=[
            FilesystemElements.levels,
            FilesystemElements.magic_factor,
            FilesystemElements.size_trend,
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="kube_pvc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Persistent Volume Claim name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_persistent_volume_claims,
        title=lambda: _("Persistent Volume Claims"),
    )
)
