#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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

_STATE_MAP = {
    "state_1": (ServiceState.UNKNOWN, "unknown or unavailable"),
    "state_2": (ServiceState.OK, "OK, good, normally working"),
    "state_3": (ServiceState.WARN, "alarm, warning, marginally working (minor)"),
    "state_4": (ServiceState.CRIT, "alert, failed, not working (major)"),
    "state_5": (ServiceState.OK, "OK, online as an active primary"),
    "state_6": (ServiceState.WARN, "alarm, offline, not running (minor)"),
    "state_7": (ServiceState.CRIT, "off-line, not running"),
    "state_8": (ServiceState.OK, "entering state of ok, good, normally working"),
    "state_9": (ServiceState.WARN, "entering state of alarm, warning, marginally working"),
    "state_10": (ServiceState.CRIT, "entering state of alert, failed, not working"),
    "state_11": (ServiceState.OK, "entering state of ok, on-line as an active primary"),
    "state_12": (ServiceState.WARN, "entering state of off-line, not running"),
}


def _parameter_formspec_juniper_alarms() -> Dictionary:
    return Dictionary(
        elements={
            key: DictElement(
                parameter_form=ServiceState(
                    title=Title(value[1].title()),  # pylint: disable=localization-of-non-literal-string
                    prefill=DefaultValue(value[0]),
                )
            )
            for key, value in _STATE_MAP.items()
        }
    )


rule_spec_juniper_alarms = CheckParameters(
    name="juniper_alarms",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_formspec_juniper_alarms,
    title=Title("State of Juniper Alarms"),
    condition=HostCondition(),
)
