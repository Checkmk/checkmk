#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.i18n import _

import cmk.rulesets.v1.form_specs.validators as formspec_validators


def build(
    validator: formspec_validators.LengthInRange,
) -> list[VueComponents.Validator]:
    value_from, value_to = validator.range
    assert not isinstance(value_from, float)
    assert not isinstance(value_to, float)
    return [
        VueComponents.LengthInRange(
            min_value=value_from,
            max_value=value_to,
            error_message=validator.error_msg.localize(_),
        )
    ]
