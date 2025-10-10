#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
from cmk.gui.form_specs.generators.age import Age
from cmk.gui.form_specs.unstable.legacy_converter.generators import TupleLevels
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_spec_backup_timemachine():
    return Dictionary(
        elements={
            "age": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Maximum age of latest timemachine backup"),
                    elements=[Age(prefill=DefaultValue(86400)), Age(prefill=DefaultValue(172800))],
                ),
            )
        }
    )


rule_spec_backup_timemachine = CheckParameters(
    name="backup_timemachine",
    title=Title("Timemachine backup age"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_backup_timemachine,
    condition=HostCondition(),
)
