#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# enhancements by thl-cmk[at]outlook[dot]com, https://thl-cmk.hopto.org
# - changed remaining time (WATO) from Age (Days, Hours, Minutes, Seconds) to Days only
# - added WATO option for License state is not ok -> default to WARN
# - added discovery rule for ITEM variant (Org Name/Org ID - this is the default, Org Name, Org ID)

# 2023-11-18: moved discovery rule set to cisco_meraki_organisations for reuse with cisco_meraki_organisations_api
# 2024-06-28: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_org_licenses_overviewi.py in to licenses_overviewi.py
# 2025-04-07: added internal keys as render only (internal_item_name, item_variant, old_item_name)
#             INCOMPATIBLE: values for remaining_expiration_time will not correctly migrated -> set them new.

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
