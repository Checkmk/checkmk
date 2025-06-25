#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private import DictionaryExtended, TwoColumnDictionary

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.vue_formspec_components import DictionaryLayout


# TODO: improve typing
def recompose(form_spec: FormSpec[Any]) -> DictionaryExtended:
    if not isinstance(form_spec, TwoColumnDictionary):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a TwoColumnDictionary form spec, got {type(form_spec)}"
        )

    return DictionaryExtended(
        title=form_spec.title,
        help_text=form_spec.help_text,
        custom_validate=form_spec.custom_validate,
        migrate=form_spec.migrate,
        elements=form_spec.elements,
        no_elements_text=form_spec.no_elements_text,
        ignored_elements=form_spec.ignored_elements,
        _layout=DictionaryLayout.two_columns,
        default_checked=form_spec.default_checked,
    )
