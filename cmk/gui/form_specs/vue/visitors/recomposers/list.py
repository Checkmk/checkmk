#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private.list_extended import ListExtended

from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec, List


def recompose(form_spec: FormSpec[Any]) -> ListExtended[Any]:
    if not isinstance(form_spec, List):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a List form spec, got {type(form_spec)}"
        )

    return ListExtended(
        title=form_spec.title,
        help_text=form_spec.help_text,
        custom_validate=form_spec.custom_validate,
        migrate=form_spec.migrate,
        element_template=form_spec.element_template,
        add_element_label=form_spec.add_element_label,
        remove_element_label=form_spec.remove_element_label,
        no_element_label=form_spec.no_element_label,
        editable_order=form_spec.editable_order,
        prefill=DefaultValue([]),
    )
