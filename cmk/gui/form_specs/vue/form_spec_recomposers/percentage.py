#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import Float, FormSpec, Percentage


def recompose(form_spec: FormSpec) -> Float:
    if not isinstance(form_spec, Percentage):
        raise MKGeneralException(
            f"Cannot decompose form spec. Expected a Percentage form spec, got {type(form_spec)}"
        )

    return Float(
        title=form_spec.title,
        help_text=form_spec.help_text,
        label=form_spec.label,
        prefill=form_spec.prefill,
        unit_symbol="%",
    )
