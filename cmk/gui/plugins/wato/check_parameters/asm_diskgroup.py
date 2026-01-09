#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.check_parameters.filesystem_utils_form_spec import fs_filesystem
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_spec_asm_diskgroup() -> Dictionary:
    return fs_filesystem(
        extra_elements={
            "req_mir_free": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Handling for required mirror space"),
                    label=Label("Regard required mirror space as free space"),
                    help_text=Help(
                        "ASM calculates the free space depending on free_mb or required mirror "
                        "free space. Enable this option to set the check against required "
                        "mirror free space. This only works for normal or high redundancy Disk Groups."
                    ),
                ),
            ),
        }
    )


rule_spec_asm_diskgroup = CheckParameters(
    name="asm_diskgroup",
    title=Title("ASM Disk Group (used space and growth)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_asm_diskgroup,
    condition=HostAndItemCondition(item_title=Title("ASM Disk Group")),
)
