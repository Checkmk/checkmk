#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.rulesets.internal.form_specs import Autocompleter, FetchMethod
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def to_vue_autocompleter(autocompleter: Autocompleter) -> shared_type_defs.Autocompleter:
    params = autocompleter.data.params
    return shared_type_defs.Autocompleter(
        data=shared_type_defs.AutocompleterData(
            ident=autocompleter.data.ident,
            params=shared_type_defs.AutocompleterParams(
                show_independent_of_context=params.show_independent_of_context,
                strict=params.strict,
                escape_regex=params.escape_regex,
                literal_search=params.literal_search,
                world=params.world,
                object_type=params.object_type,
                context=params.context,
                input_hint=params.input_hint,
            ),
        ),
        fetch_method=_to_vue_fetch_method(autocompleter.fetch_method),
    )


def _to_vue_fetch_method(fetch_method: FetchMethod) -> shared_type_defs.FetchMethod:
    match fetch_method:
        case FetchMethod.ajax_vs_autocomplete:
            return shared_type_defs.FetchMethod.ajax_vs_autocomplete
        case FetchMethod.rest_autocomplete:
            return shared_type_defs.FetchMethod.rest_autocomplete
        case _:
            assert_never(fetch_method)
