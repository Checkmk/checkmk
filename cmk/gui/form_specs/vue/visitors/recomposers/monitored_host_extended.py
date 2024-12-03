#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private import MonitoredHostExtended, StringAutocompleter
from cmk.gui.form_specs.vue.shared_type_defs import Autocompleter

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec


def recompose(form_spec: FormSpec[Any]) -> StringAutocompleter:
    if not isinstance(form_spec, MonitoredHostExtended):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a MonitoredHostExtended form spec, got {type(form_spec)}"
        )

    return StringAutocompleter(
        # FormSpec
        title=form_spec.title or Title("Host name"),
        help_text=form_spec.help_text,
        custom_validate=form_spec.custom_validate,
        migrate=form_spec.migrate,
        # StringAutocompleter
        autocompleter=Autocompleter(
            fetch_method="ajax_vs_autocomplete",
            data={
                "ident": "config_hostname",
                "params": {
                    "show_independent_of_context": True,
                    "strict": True,
                    "escape_regex": False,
                },
            },
        ),
        prefill=form_spec.prefill,
    )
