#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private.cascading_single_choice_extended import (
    CascadingSingleChoiceExtended,
)

from cmk.rulesets.v1.form_specs import CascadingSingleChoice, FormSpec
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout


def recompose(form_spec: FormSpec[Any]) -> CascadingSingleChoiceExtended:
    if not isinstance(form_spec, CascadingSingleChoice):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a SingleChoice form spec, got {type(form_spec)}"
        )

    return CascadingSingleChoiceExtended(
        # Base
        title=form_spec.title,
        help_text=form_spec.help_text,
        label=form_spec.label,
        migrate=form_spec.migrate,
        custom_validate=form_spec.custom_validate,
        prefill=form_spec.prefill,
        elements=form_spec.elements,
        # Extended
        layout=CascadingSingleChoiceLayout.vertical,
    )
