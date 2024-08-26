#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private import validators as private_form_specs_validators
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.i18n import _


def build(
    validator: private_form_specs_validators.IsFloat,
) -> list[shared_type_defs.Validator]:
    return [
        shared_type_defs.IsFloat(
            error_message=validator.error_msg.localize(_),
        )
    ]
