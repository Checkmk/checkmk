#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Sequence

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
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
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange, ValidationError
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_to_valid_ident(value: object) -> Sequence[str]:
    if not isinstance(value, list):
        raise ValueError(f"Expected a list of strings, got {value}")
    return [name.replace("-", "_") for name in value if isinstance(name, str)]


def _check_for_duplicates(value: Sequence[str]) -> None:
    if any(item for item, count in Counter(value).items() if count > 1):
        raise ValidationError(message=Message("Duplicated elements provided."))


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
                    help_text=Help(
                        "Select the sections that you want to include in the agent output."
                        "<p>"
                        "<b>Note:</b> some Meraki resources are marked as deprecated, which"
                        "means that they could be removed at some point in the future."
                        "</p>"
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="api_response_codes",
                            title=Title("API response codes"),
                        ),
                        MultipleChoiceElement(
                            name="appliance_performance",
                            title=Title("Appliance uplink performance"),
                        ),
                        MultipleChoiceElement(
                            name="appliance_uplinks", title=Title("Appliance uplink statuses")
                        ),
                        MultipleChoiceElement(
                            name="appliance_vpns", title=Title("Appliance uplink VPN statuses")
                        ),
                        MultipleChoiceElement(
                            name="device_statuses",
                            title=Title("Device statuses <b>[deprecated]</b>"),
                        ),
                        MultipleChoiceElement(
                            name="device_uplinks_info",
                            title=Title("Device uplinks"),
                        ),
                        MultipleChoiceElement(
                            name="licenses_overview", title=Title("Licenses overview")
                        ),
                        MultipleChoiceElement(
                            name="sensor_readings", title=Title("Sensor readings")
                        ),
                        MultipleChoiceElement(
                            name="switch_port_statuses", title=Title("Switch port statuses")
                        ),
                        MultipleChoiceElement(
                            name="wireless_device_statuses",
                            title=Title("Wireless device statuses"),
                        ),
                        MultipleChoiceElement(
                            name="wireless_ethernet_statuses",
                            title=Title("Wireless ethernet statuses"),
                        ),
                    ],
                    prefill=DefaultValue(
                        [
                            "api_response_codes",
                            "appliance_uplinks",
                            "appliance_vpns",
                            "device_statuses",
                            "device_uplinks_info",
                            "licenses_overview",
                            "sensor_readings",
                            "wireless_ethernet_statuses",
                        ]
                    ),
                    migrate=_migrate_to_valid_ident,
                )
            ),
            "orgs": DictElement(
                parameter_form=List(
                    element_template=String(macro_support=True),
                    title=Title("Organizations"),
                    help_text=Help("Specify which organizations to fetch data from."),
                    custom_validate=[_check_for_duplicates],
                )
            ),
            "org_id_as_prefix": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Use Organisation-ID as host prefix"),
                    label=Label("The Organization-ID will be used as host name prefix"),
                    help_text=Help(
                        "The Organisation-ID will be used as prefix for the hostname (separated by a -). Use "
                        'this option together with a "Hostname translation for piggybacked hosts" to add a '
                        "organisation prefix to the hosts from the Cisco Meraki cloud to avoid conflicting "
                        'hostnames. You can also use this option along with the "Dynamic host management" to '
                        "sort the host in organisation specific folders."
                    ),
                )
            ),
            "net_id_as_prefix": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Use Network-ID as host prefix"),
                    label=Label("The Network-ID will be used as host name prefix"),
                    help_text=Help(
                        "The Network-ID will be used as prefix for the hostname (separated by a -). Use "
                        'this option together with a "Hostname translation for piggybacked hosts" to add a '
                        "network prefix to the hosts from the Cisco Meraki cloud to avoid conflicting "
                        'hostnames. You can also use this option along with the "Dynamic host management" to '
                        "sort the host in location specific folders."
                    ),
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
            "timespan": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Timespan"),
                    label=Label("The interval for which the information will be fetched."),
                    displayed_magnitudes=(
                        TimeMagnitude.DAY,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                    ),
                    help_text=Help(
                        "<p>The minimum value is 15 minutes and the maximum value is 31 days.</p>"
                        "This applies to the following sections: "
                        "<ul>"
                        "<li>switch port statuses</li>"
                        "</ul>"
                    ),
                    prefill=DefaultValue(900),  # 15 minutes
                    custom_validate=[NumberInRange(min_value=900, max_value=2678400)],
                )
            ),
            "cache_per_section": DictElement(
                parameter_form=Dictionary(
                    title=Title("Cache per section"),
                    help_text=Help(
                        "By setting a higher value for a given resource, you reduce the amount of "
                        "requests sent to the Meraki API instance. If not changed, the predefined "
                        "default time to live (TTL) cache interval will be used."
                    ),
                    elements={
                        "appliance_uplinks": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Appliance uplink statuses"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),  # 1 hour
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "appliance_vpns": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Appliance uplink VPN statuses"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),  # 1 hour
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "devices": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Devices"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),  # 1 hour
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "device_statuses": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Device statuses"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),  # 1 hour
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "device_uplinks_info": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Device uplinks"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),  # 1 hour
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "licenses_overview": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Licenses overview"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(36000.0),  # 10 hours
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "networks": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Networks"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(36000.0),  # 10 hours
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "organizations": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Organizations"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(36000.0),  # 10 hours
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "wireless_device_statuses": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Wireless device statuses"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(1800.0),  # 30 minutes
                                custom_validate=[NumberInRange(min_value=0.0)],
                            )
                        ),
                        "wireless_ethernet_statuses": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Wireless ethernet statuses"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(1800.0),  # 30 minutes
                                custom_validate=[NumberInRange(min_value=0.0)],
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
    topic=Topic.NETWORKING,
    parameter_form=_form_special_agent_cisco_meraki,
)
