#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    migrate_to_password,
    migrate_to_proxy,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_to_valid_ident(value: object) -> Sequence[str]:
    if not isinstance(value, Iterable):
        raise ValueError("Invalid value {value} for sections")

    name_mapping = {
        "licenses-overview": "licenses_overview",
        "device-statuses": "device_statuses",
        "sensor-readings": "sensor_readings",
    }

    return [name_mapping.get(s, s) for s in value if isinstance(s, str)]


def _form_special_agent_cisco_meraki() -> Dictionary:
    return Dictionary(
        title=Title("Cisco Meraki"),
        elements={
            "api_key": DictElement(
                parameter_form=Password(title=Title("API key"), migrate=migrate_to_password),
                required=True,
            ),
            "proxy": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
            "region": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Meraki region"),
                    help_text=Help(
                        "<p>The Meraki API is available under different URLS for different regions of the world.</p>"
                        "<ul>"
                        '<li>Default (most of the world): "https://api.meraki.com/api/v1"</li>'
                        '<li>Canada	"https://api.meraki.ca/api/v1"</li>'
                        '<li>China	"https://api.meraki.cn/api/v1"</li>'
                        '<li>India	"https://api.meraki.in/api/v1"</li>'
                        '<li>United States FedRAMP	"https://api.gov-meraki.com/api/v1"</li>'
                        "</ul>"
                        '<p>For more details, see the <a href="https://developer.cisco.com/meraki/api-v1/getting-started/#base-uri">API Documentation</a>.</p>'
                    ),
                    elements=[
                        SingleChoiceElement(name="default", title=Title("Default")),
                        SingleChoiceElement(name="canada", title=Title("Canada")),
                        SingleChoiceElement(name="china", title=Title("China")),
                        SingleChoiceElement(name="india", title=Title("India")),
                        SingleChoiceElement(name="us_gov", title=Title("United States FedRAMP")),
                    ],
                    prefill=DefaultValue("default"),
                )
            ),
            "sections": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Sections"),
                    elements=[
                        MultipleChoiceElement(
                            name="licenses_overview", title=Title("Organization licenses overview")
                        ),
                        MultipleChoiceElement(
                            name="device_statuses", title=Title("Organization device statuses")
                        ),
                        MultipleChoiceElement(
                            name="sensor_readings", title=Title("Organization sensor readings")
                        ),
                    ],
                    migrate=_migrate_to_valid_ident,
                )
            ),
            "orgs": DictElement(
                parameter_form=List(
                    element_template=String(macro_support=True), title=Title("Organizations")
                )
            ),
            "no_cache": DictElement(
                parameter_form=FixedValue(
                    title=Title("Disable cache"),
                    help_text=Help("Always fetch data from Meraki API."),
                    label=Label("API cache is disabled."),
                    value=True,
                )
            ),
            "cache_per_section": DictElement(
                parameter_form=Dictionary(
                    title=Title("Cache per section"),
                    elements={
                        "devices": DictElement(
                            parameter_form=Integer(
                                title=Title("Devices"),
                                prefill=DefaultValue(60),
                                unit_symbol="minutes",
                                custom_validate=(NumberInRange(min_value=0),),
                            )
                        ),
                        "device_statuses": DictElement(
                            parameter_form=Integer(
                                title=Title("Device statuses"),
                                prefill=DefaultValue(60),
                                unit_symbol="minutes",
                                custom_validate=(NumberInRange(min_value=0),),
                            )
                        ),
                        "licenses_overview": DictElement(
                            parameter_form=Integer(
                                title=Title("Licenses overview"),
                                prefill=DefaultValue(600),
                                unit_symbol="minutes",
                                custom_validate=(NumberInRange(min_value=0),),
                            )
                        ),
                        "organizations": DictElement(
                            parameter_form=Integer(
                                title=Title("Organizations"),
                                prefill=DefaultValue(600),
                                unit_symbol="minutes",
                                custom_validate=(NumberInRange(min_value=0),),
                            )
                        ),
                        "sensor_readings": DictElement(
                            parameter_form=Integer(
                                title=Title("Sensor readings"),
                                prefill=DefaultValue(0),
                                unit_symbol="minutes",
                                custom_validate=(NumberInRange(min_value=0),),
                            )
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_cisco_meraki = SpecialAgent(
    name="cisco_meraki",
    title=Title("Cisco Meraki"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_special_agent_cisco_meraki,
)
