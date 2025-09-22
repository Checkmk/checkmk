#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import Float, FormSpec, Percentage


# TODO: improve typing
def recompose(form_spec: FormSpec[Any]) -> FormSpec[Any]:
    if not isinstance(form_spec, Percentage):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a Percentage form spec, got {type(form_spec)}"
        )

    return Float(
        title=form_spec.title,
        help_text=form_spec.help_text,
        migrate=form_spec.migrate,
        custom_validate=form_spec.custom_validate,
        label=form_spec.label,
        prefill=form_spec.prefill,
        unit_symbol="%",
    )
