#!/usr/bin/env python3

from cmk.rulesets.v1 import (
    Title,
    Label,
)

from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    BooleanChoice,
    DefaultValue,
)

from cmk.rulesets.v1.rule_specs import (
    Topic,
    DiscoveryParameters,
)



def _parameter_form_mssql_jobs_discovery() -> Dictionary:
    return Dictionary(
        title=Title("MSSQL Jobs Discovery"),
        elements={
            "discover_schedule_disabled": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Discover jobs with disabled Scheduler"),
                    prefill=DefaultValue(True)
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
