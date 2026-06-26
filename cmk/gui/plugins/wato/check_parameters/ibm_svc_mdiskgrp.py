#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.check_parameters.filesystem_utils_form_spec import fs_filesystem
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_ibm_svc_mdiskgrp() -> Dictionary:
    return fs_filesystem(
        extra_elements={
            "provisioning_levels": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Provisioning levels"),
                    help_text=Help("A provisioning of over 100% means over provisioning."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((110.0, 120.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        }
    )


rule_spec_ibm_svc_mdiskgrp = CheckParameters(
    name="ibm_svc_mdiskgrp",
    title=Title("IBM SVC pool capacity"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_ibm_svc_mdiskgrp,
    condition=HostAndItemCondition(item_title=Title("Name of the pool")),
)
