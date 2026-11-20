#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import (
    Label,
    Title,
)
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import (
    DiscoveryParameters,
    Topic,
)


def _parameter_form_mssql_jobs_discovery() -> Dictionary:
    return Dictionary(
        title=Title("MSSQL Jobs Discovery"),
        elements={
            "discover_schedule_disabled": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Discover jobs with disabled Scheduler"),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
        },
    )


rule_spec_mssql_jobs_discovery = DiscoveryParameters(
    name="mssql_jobs_discovery",
    title=Title("MSSQL Jobs Discovery"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_mssql_jobs_discovery,
)
