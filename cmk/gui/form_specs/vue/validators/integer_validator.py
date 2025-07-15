#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private import validators as private_form_specs_validators
from cmk.gui.i18n import _
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def build(
    validator: private_form_specs_validators.IsInteger,
) -> list[shared_type_defs.Validator]:
    return [
        shared_type_defs.IsInteger(
            error_message=validator.error_msg.localize(_),
        )
    ]
