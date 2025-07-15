#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.private import StringAutocompleter
from cmk.rulesets.v1.form_specs import FormSpec, String


def recompose(form_spec: FormSpec[Any]) -> StringAutocompleter:
    if not isinstance(form_spec, String):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a String form spec, got {type(form_spec)}"
        )

    return StringAutocompleter(
        # FormSpec
        title=form_spec.title,
        help_text=form_spec.help_text,
        custom_validate=form_spec.custom_validate,
        label=form_spec.label,
        # String
        macro_support=form_spec.macro_support,
        field_size=form_spec.field_size,
        prefill=form_spec.prefill,
        migrate=form_spec.migrate,
    )
