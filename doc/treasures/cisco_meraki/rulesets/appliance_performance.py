#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-06-23
# File  : cisco_meraki_org_appliance_performance.py (WATO)

# 2024-06-27: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_org_appliance_performance.py in to appliance_performance.py

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
    migrate_to_integer_simple_levels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            'levels_upper': DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(60, 80)),
                    migrate=migrate_to_integer_simple_levels,
                    help_text=Help(
                        'The device utilization data reported to the Meraki'
                        ' dashboard is based on a load average measured over a'
                        ' period of one minute. The load value is returned in'
                        ' numeric values ranging from 1 through 100. A lower'
                        ' value indicates a lower load, and a higher value'
                        ' indicates a more intense workload. Currently, the'
                        ' device utilization value is calculated based upon the'
                        ' CPU utilization of the MX as well as its traffic load.'
                        ' If an MX device is consistently over 50% utilization'
                        ' during normal operation, upgrading to a higher'
                        ' throughput model or reducing the per-device load'
                        ' through horizontal scaling should be considered. For'
                        ' more information see:'
                        ' https://documentation.meraki.com-MX-Monitoring?and?'
                        'Reporting-Device?Utiliyation'
                    ),
                )
            )
        },
    )


rule_spec_cisco_meraki_org_appliance_performance = CheckParameters(
    name="cisco_meraki_org_appliance_performance",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Appliance Utilization"),
    condition=HostCondition(),
)
