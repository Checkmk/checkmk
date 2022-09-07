#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
    TextInput,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Percentage


def _parameter_valuespec_nvidia_smi_gpu_util() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels",
                SimpleLevels(Percentage, title=_("GPU utilization"), default_levels=(80.0, 90.0)),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nvidia_smi_gpu_util",
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Nvidia GPU utilization")),
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_nvidia_smi_gpu_util,
        title=lambda: _("Nvidia GPU utilization"),
    )
)
