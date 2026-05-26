#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _netapp_ontap_ntp_time() -> Dictionary:
    return Dictionary(
        elements={
            "offset": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("NTP time offset"),
                    help_text=Help(
                        "When the NTP offset reported by the selected peer was worse "
                        "(in either direction) than the specified parameters, "
                        "go into WARN or CRIT status."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.SECOND,
                            TimeMagnitude.MILLISECOND,
                        ],
                    ),
                    prefill_fixed_levels=DefaultValue((0.2, 0.5)),
                ),
            ),
        }
    )


rule_spec_netapp_ontap_time = CheckParameters(
    name="netapp_ontap_time",
    title=Title("NetApp NTP time offset"),
    topic=Topic.STORAGE,
    parameter_form=_netapp_ontap_ntp_time,
    condition=HostAndItemCondition(item_title=Title("Node")),
)
