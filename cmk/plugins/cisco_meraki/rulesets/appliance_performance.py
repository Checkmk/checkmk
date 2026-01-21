#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Performance utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(60, 80)),
                    help_text=Help(
                        # xgettext: no-python-format
                        "The device utilization data reported to the Meraki "
                        "dashboard is based on a load average measured over a "
                        "period of one minute. The load value is returned in "
                        "numeric values ranging from 1 through 100. A lower "
                        "value indicates a lower load, and a higher value "
                        "indicates a more intense workload. Currently, the "
                        "device utilization value is calculated based upon the "
                        "CPU utilization of the MX as well as its traffic load. "
                        "If an MX device is consistently over 50% utilization "
                        "during normal operation, upgrading to a higher "
                        "throughput model or reducing the per-device load "
                        "through horizontal scaling should be considered."
                    ),
                )
            )
        },
    )


rule_spec_cisco_meraki_org_appliance_performance = CheckParameters(
    name="cisco_meraki_org_appliance_performance",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki appliance utilization"),
    condition=HostCondition(),
)
