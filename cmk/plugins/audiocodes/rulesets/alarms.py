#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_audiocores_alarms() -> Dictionary:
    return Dictionary(
        elements={
            "severity_state_mapping": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Map severity levels to alarm states"),
                    elements={
                        "cleared": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Cleared"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "indeterminate": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Indeterminate"),
                                prefill=DefaultValue(ServiceState.UNKNOWN),
                            ),
                        ),
                        "warning": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Warning"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "minor": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Minor"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "major": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Major"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                        ),
                        "critical": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Critical"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_audiocodes_alarms = CheckParameters(
    name="audiocodes_alarms",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_audiocores_alarms,
    title=Title("AudioCodes Alarms"),
    condition=HostCondition(),
)
