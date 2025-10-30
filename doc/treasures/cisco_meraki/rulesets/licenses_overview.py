#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    ServiceState,
    SimpleLevels,
    LevelDirection,
    TimeSpan,
    TimeMagnitude,
    validators,
    migrate_to_float_simple_levels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_DAY = 60.0 * 60.0 * 24.0


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "remaining_expiration_time": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Remaining licenses expiration time"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((40 * _DAY, 20 * _DAY)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY],
                        custom_validate=(validators.NumberInRange(min_value=0),),
                    ),
                )),
            "state_license_not_ok": DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if License state is not OK'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
            'dont_show_alias_on_info': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Don\'t show alias on info line'),
                    label=Label(''),
                    # help_test=Help(
                    #     'The alias is the Organisation ID or the Organisation name, depending on the Item.\n'
                    #     'If the item is the Organisation ID, the alias is the Organisation name and vice versa.\n'
                    #     'Organisation ID and Organisation name will always show up in the service details.'
                    # )
                )),
            'internal_item_name': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovery internal item name')
                )),
            'item_variant': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovery item variant')
                )),
            'old_item_name': DictElement(
                render_only=True,
                parameter_form=String()
            )
        },
    )


rule_spec_cisco_meraki_org_licenses_overview = CheckParameters(
    name="cisco_meraki_org_licenses_overview",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Organisation Licenses Overview"),
    condition=HostAndItemCondition(item_title=Title('Organization')),
)
