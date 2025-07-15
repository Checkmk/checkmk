#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.private import MultipleChoiceExtended, MultipleChoiceExtendedLayout
from cmk.rulesets.v1.form_specs import FormSpec, MultipleChoice


def recompose(form_spec: FormSpec[Any]) -> MultipleChoiceExtended:
    if not isinstance(form_spec, MultipleChoice):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a MultipleChoice form spec, got {type(form_spec)}"
        )

    return MultipleChoiceExtended(
        # FormSpec
        title=form_spec.title,
        help_text=form_spec.help_text,
        custom_validate=form_spec.custom_validate,
        migrate=form_spec.migrate,
        # MultipleChoice
        elements=form_spec.elements,
        show_toggle_all=form_spec.show_toggle_all,
        prefill=form_spec.prefill,
        # AdaptiveMultipleChoice
        layout=MultipleChoiceExtendedLayout.auto,
    )
