#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import TypeVar

from cmk.gui.form_specs.private import (
    StringAutocompleter,
)
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, InputHint
from cmk.shared_typing.vue_formspec_components import (
    Autocompleter,
    AutocompleterData,
    AutocompleterParams,
)

T = TypeVar("T")


def create_monitored_host_name(
    title: Title = Title("Host name"),
    help_text: Help | None = None,
    custom_validate: Sequence[Callable[[str], object]] | None = None,
    migrate: Callable[[object], str] | None = None,
    prefill: DefaultValue[str] | None = None,
) -> StringAutocompleter:
    return StringAutocompleter(
        title=title,
        help_text=help_text,
        custom_validate=custom_validate,
        migrate=migrate,
        autocompleter=Autocompleter(
            data=AutocompleterData(
                ident="monitored_hostname",
                params=AutocompleterParams(
                    show_independent_of_context=True, strict=True, escape_regex=False
                ),
            ),
        ),
        prefill=prefill or InputHint("(Select hostname)"),
    )
