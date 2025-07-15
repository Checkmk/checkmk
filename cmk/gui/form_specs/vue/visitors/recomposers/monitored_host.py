#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.generators.monitored_host_name import create_monitored_host_name
from cmk.gui.form_specs.private import StringAutocompleter

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec, MonitoredHost


def recompose(form_spec: FormSpec[Any]) -> StringAutocompleter:
    if not isinstance(form_spec, MonitoredHost):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a MonitoredHost form spec, got {type(form_spec)}"
        )
    return create_monitored_host_name(
        form_spec.title or Title("Host name"),
        form_spec.help_text,
        form_spec.custom_validate,
        form_spec.migrate,
    )
