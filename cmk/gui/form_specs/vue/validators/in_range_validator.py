#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.i18n import _

import cmk.rulesets.v1.form_specs.validators as formspec_validators


def build(
    validator: formspec_validators.NumberInRange,
) -> list[shared_type_defs.Validator]:
    value_from, value_to = validator.range
    assert not isinstance(value_from, float)
    assert not isinstance(value_to, float)
    min_validator = formspec_validators.NumberInRange(min_value=validator.range[0])
    max_validator = formspec_validators.NumberInRange(max_value=validator.range[1])
    return [
        shared_type_defs.NumberInRange(
            min_value=None,
            max_value=value_to,
            error_message=max_validator.error_msg.localize(_),
        ),
        shared_type_defs.NumberInRange(
            min_value=value_from,
            max_value=None,
            error_message=min_validator.error_msg.localize(_),
        ),
    ]
