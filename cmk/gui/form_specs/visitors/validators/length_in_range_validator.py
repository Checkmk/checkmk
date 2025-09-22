#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import cmk.rulesets.v1.form_specs.validators as formspec_validators
from cmk.gui.i18n import _
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def build(
    validator: formspec_validators.LengthInRange,
) -> list[shared_type_defs.Validator]:
    value_from, value_to = validator.range
    assert not isinstance(value_from, float)
    assert not isinstance(value_to, float)
    return [
        shared_type_defs.LengthInRange(
            min_value=value_from,
            max_value=value_to,
            error_message=validator.error_msg.localize(_),
        )
    ]
