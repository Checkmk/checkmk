#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.gui.valuespec import Dictionary, Float, Percentage


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


def _parameter_valuespec_nvidia_smi_en_de_coder_util() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "encoder_levels",
                SimpleLevels(
                    Percentage, title=_("Encoder utilization"), default_levels=(80.0, 90.0)
                ),
            ),
            (
                "decoder_levels",
                SimpleLevels(
                    Percentage, title=_("Decoder utilization"), default_levels=(80.0, 90.0)
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nvidia_smi_en_de_coder_util",
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Nvidia GPU En-/Decoder utilization")),
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_nvidia_smi_en_de_coder_util,
        title=lambda: _("Nvidia GPU En-/Decoder utilization"),
    )
)


def _parameter_valuespec_nvidia_smi_power() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels",
                SimpleLevels(
                    Float, title=_("Power consumption draw"), default_levels=(50.0, 60.0), unit="W"
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nvidia_smi_power",
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Nvidia GPU Power")),
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_nvidia_smi_power,
        title=lambda: _("Nvidia GPU Power"),
    )
)


def _parameter_valuespec_nvidia_smi_memory_util() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels_total",
                SimpleLevels(
                    Percentage, title=_("Total memory utilization"), default_levels=(80.0, 90.0)
                ),
            ),
            (
                "levels_bar1",
                SimpleLevels(
                    Percentage, title=_("BAR1 memory utilization"), default_levels=(80.0, 90.0)
                ),
            ),
            (
                "levels_fb",
                SimpleLevels(
                    Percentage, title=_("FB memory utilization"), default_levels=(80.0, 90.0)
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nvidia_smi_memory_util",
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Nvidia GPU Memory utilization")),
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_nvidia_smi_memory_util,
        title=lambda: _("Nvidia GPU Memory utilization"),
    )
)
