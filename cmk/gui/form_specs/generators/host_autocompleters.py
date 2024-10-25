#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypeVar

from cmk.gui.form_specs.private import StringAutocompleter
from cmk.gui.form_specs.vue.shared_type_defs import Autocompleter

from cmk.rulesets.v1 import Help, Title

T = TypeVar("T")


def create_config_host_autocompleter(
    title: Title = Title("Host"),
    help_text: Help | None = None,
) -> StringAutocompleter:
    # Note: this autocompleter does not support params -> empty dict
    return StringAutocompleter(
        title=title,
        help_text=help_text,
        autocompleter=Autocompleter(
            fetch_method="ajax_vs_autocomplete",
            data={"ident": "config_hostname", "params": {}},
        ),
    )
