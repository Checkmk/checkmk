#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Iterable, Sequence

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    # BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    Proxy,
    String,
    migrate_to_password,
    migrate_to_proxy,
    SingleChoice,
    SingleChoiceElement,
)

from cmk.rulesets.v1.form_specs.validators import ValidationError, NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic
from cmk_addons.plugins.meraki.lib.utils import (
    SEC_CACHE_APPLIANCE_PERFORMANCE,
    SEC_CACHE_APPLIANCE_UPLINKS_USAGE,
    SEC_CACHE_APPLIANCE_UPLINKS,
    SEC_CACHE_APPLIANCE_VPNS,
    SEC_CACHE_CELLULAR_UPLINKS,
    SEC_CACHE_DEVICE_INFO,
    SEC_CACHE_DEVICE_STATUSES,
    SEC_CACHE_DEVICE_UPLINKS_INFO,
    SEC_CACHE_LICENSES_OVERVIEW,
    SEC_CACHE_NETWORKS,
    SEC_CACHE_ORG_API_REQUESTS,
    SEC_CACHE_ORG_SWITCH_PORTS_STATUSES,
    SEC_CACHE_ORGANISATIONS,
    SEC_CACHE_SENSOR_READINGS,
    SEC_CACHE_SWITCH_PORTS_STATUSES,
    SEC_CACHE_WIRELESS_DEVICE_STATUS,
    SEC_CACHE_WIRELESS_ETHERNET_STATUSES,
)

SEC_NAME_APPLIANCE_UPLINKS = 'appliance_uplinks'
SEC_NAME_APPLIANCE_UPLINKS_USAGE = 'appliance_uplinks_usage'
SEC_NAME_APPLIANCE_VPNS = 'appliance_vpns'
SEC_NAME_APPLIANCE_PERFORMANCE = 'appliance_performance'
SEC_NAME_CELLULAR_UPLINKS = 'cellular_uplinks'
SEC_NAME_DEVICE_INFO = 'device_info'
SEC_NAME_DEVICE_STATUSES = 'device_status'
SEC_NAME_DEVICE_UPLINKS_INFO = 'device_uplinks_info'
SEC_NAME_LICENSES_OVERVIEW = 'licenses_overview'
SEC_NAME_NETWORKS = 'networks'
SEC_NAME_ORGANISATIONS = 'organisations'
SEC_NAME_ORG_API_REQUESTS = 'api_requests_by_organization'
SEC_NAME_SENSOR_READINGS = 'sensor_readings'
SEC_NAME_SWITCH_PORTS_STATUSES = 'switch_ports_statuses'
SEC_NAME_WIRELESS_DEVICE_STATUS = 'wireless_device_status'
SEC_NAME_WIRELESS_ETHERNET_STATUSES = 'wireless_ethernet_statuses'
SEC_NAME_ORG_SWITCH_PORTS_STATUSES = 'org_switch_ports_statuses'

SEC_TITLE_DEVICE_INFO = 'Device info (Organization)'
SEC_TITLE_NETWORKS = 'Network info (Organization)'
SEC_TITLE_ORGANISATIONS = 'Organization (Agent)'
SEC_TITLE_ORG_API_REQUESTS = 'API request (Organization)'
SEC_TITLE_APPLIANCE_UPLINKS = 'Appliances uplinks (Organization)'
SEC_TITLE_APPLIANCE_UPLINKS_USAGE = 'Appliances uplinks usage (Organization)'
SEC_TITLE_APPLIANCE_VPNS = 'Appliances VPNs (Organization)'
SEC_TITLE_APPLIANCE_PERFORMANCE = 'Appliances Utilization (Device)'
SEC_TITLE_CELLULAR_UPLINKS = 'Cellular devices uplinks (Organization)'
SEC_TITLE_DEVICE_STATUSES = 'Devices status (Organization)'
SEC_TITLE_DEVICE_UPLINKS_INFO = 'Devices uplink info (Organization)'
SEC_TITLE_LICENSES_OVERVIEW = 'Licenses overview (Organization)'
SEC_TITLE_SENSOR_READINGS = 'Sensors readings (Organization)'
SEC_TITLE_SWITCH_PORTS_STATUSES = 'Switch ports status (Device)'
SEC_TITLE_WIRELESS_ETHERNET_STATUSES = 'Wireless devices ethernet status (Organization)'
SEC_TITLE_WIRELESS_DEVICE_STATUS = 'Wireless devices SSIDs status (Device)'
SEC_TITLE_ORG_SWITCH_PORTS_STATUSES = 'Switch port status (Organization/Early Access)'


class DuplicateInList:  # pylint: disable=too-few-public-methods
    """ Custom validator that ensures the validated list has no duplicate entries. """

    def __init__(
            self,
    ) -> None:
        pass

    @staticmethod
    def _get_default_errmsg(_duplicates: Sequence) -> Message:
        return Message(f'Duplicate element in list. Duplicate elements: {", ".join(_duplicates)}')

    def __call__(self, value: List[str] | None) -> None:
        if not isinstance(value, list):
            return
        _duplicates = [value[i] for i, x in enumerate(value) if value.count(x) > 1]
        _duplicates = list(set(_duplicates))
        if _duplicates:
            raise ValidationError(message=self._get_default_errmsg(_duplicates))


def _migrate_to_valid_ident(value: object) -> Sequence[str]:
    if not isinstance(value, Iterable):
        raise ValueError('Invalid value {value} for sections')

    # name_mapping = {
    #     'licenses-overview': 'licenses_overview',
    #     'device-statuses': 'device_statuses',
    #     'sensor-readings': 'sensor_readings',
    # }

    # return [name_mapping.get(s, s) for s in value]
    return [s.replace('-', '_') for s in value]


meraki_excluded_sections = [
    MultipleChoiceElement(name=SEC_NAME_ORG_API_REQUESTS, title=Title(SEC_TITLE_ORG_API_REQUESTS)),
    MultipleChoiceElement(name=SEC_NAME_APPLIANCE_UPLINKS, title=Title(SEC_TITLE_APPLIANCE_UPLINKS)),
    MultipleChoiceElement(name=SEC_NAME_APPLIANCE_UPLINKS_USAGE, title=Title(SEC_TITLE_APPLIANCE_UPLINKS_USAGE)),
    MultipleChoiceElement(name=SEC_NAME_APPLIANCE_VPNS, title=Title(SEC_TITLE_APPLIANCE_VPNS)),
    MultipleChoiceElement(name=SEC_NAME_APPLIANCE_PERFORMANCE, title=Title(SEC_TITLE_APPLIANCE_PERFORMANCE)),
    MultipleChoiceElement(name=SEC_NAME_CELLULAR_UPLINKS, title=Title(SEC_TITLE_CELLULAR_UPLINKS)),
    MultipleChoiceElement(name=SEC_NAME_DEVICE_STATUSES, title=Title(SEC_TITLE_DEVICE_STATUSES)),
    MultipleChoiceElement(name=SEC_NAME_DEVICE_UPLINKS_INFO, title=Title(SEC_TITLE_DEVICE_UPLINKS_INFO)),
    MultipleChoiceElement(name=SEC_NAME_LICENSES_OVERVIEW, title=Title(SEC_TITLE_LICENSES_OVERVIEW)),
    MultipleChoiceElement(name=SEC_NAME_SENSOR_READINGS, title=Title(SEC_TITLE_SENSOR_READINGS)),
    MultipleChoiceElement(name=SEC_NAME_SWITCH_PORTS_STATUSES, title=Title(SEC_TITLE_SWITCH_PORTS_STATUSES)),
    MultipleChoiceElement(name=SEC_NAME_WIRELESS_ETHERNET_STATUSES, title=Title(SEC_TITLE_WIRELESS_ETHERNET_STATUSES)),
    MultipleChoiceElement(name=SEC_NAME_WIRELESS_DEVICE_STATUS, title=Title(SEC_TITLE_WIRELESS_DEVICE_STATUS)),
    MultipleChoiceElement(name=SEC_NAME_ORG_SWITCH_PORTS_STATUSES, title=Title(SEC_TITLE_ORG_SWITCH_PORTS_STATUSES)),
]

def _form_special_agent_cisco_meraki() -> Dictionary:
    return Dictionary(
        title=Title('Cisco Meraki'),
        elements={
            'api_key': DictElement(
                parameter_form=Password(
                    title=Title('API Key'),
                    migrate=migrate_to_password
                ),
                required=True,
            ),
            'proxy': DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy
                )
            ),
            'no_cache': DictElement(
                parameter_form=FixedValue(  # BooleanChoice needs 2 clicks :-(
                    title=Title('Disable Cache'),
                    help_text=Help(
                        'Never use cached information. By default the agent will cache received '
                        'data to avoid API limits and speed up the data retrievel.'
                    ),
                    label=Label('API Cache is disabled'),
                    value=True,
                )
            ),
            'org_id_as_prefix': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Use Organisation-ID as host prefix'),
                    label=Label('The Organization-ID will be used as host name prefix'),
                    help_text=Help(
                        'The Organisation-ID will be used as prefix for the hostname (separated by a -). Use '
                        'this option together with a "Hostname translation for piggybacked hosts" to add a '
                        'organisation prefix to the hosts from the Cisco Meraki cloud to avoid conflicting '
                        'hostnames. You can also use this option along with the "Dynamic host management" to '
                        'sort the host in organisation specific folders.'
                    )
                )),
            'net_id_as_prefix': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Use Network-ID as host prefix'),
                    label=Label('The Network-ID will be used as host name prefix'),
                    help_text=Help(
                        'The Network-ID will be used as prefix for the hostname (separated by a -). Use '
                        'this option together with a "Hostname translation for piggybacked hosts" to add a '
                        'network prefix to the hosts from the Cisco Meraki cloud to avoid conflicting '
                        'hostnames. You can also use this option along with the "Dynamic host management" to '
                        'sort the host in location specific folders.'
                    )
                )),
            'meraki_region': DictElement(
                parameter_form=SingleChoice(
                    title=Title('Meraki region'),
                    help_text=Help(
                        'The Meraki API is available under different URLS for different regions of the world.\n'
                        'Default (most of the world): "https://api.meraki.com/api/v1"\n'
                        'Canada	"https://api.meraki.ca/api/v1"\n'
                        'China	"https://api.meraki.cn/api/v1"\n'
                        'India	"https://api.meraki.in/api/v1"\n'
                        'United States FedRAMP	"https://api.gov-meraki.com/api/v1"\n'
                        'For details see: "https://developer.cisco.com/meraki/api-v1/getting-started/#base-uri"\n'
                    ),
                    elements=[
                        SingleChoiceElement(name='default', title=Title('Default')),
                        SingleChoiceElement(name='canada', title=Title('Canada')),
                        SingleChoiceElement(name='china', title=Title('China')),
                        SingleChoiceElement(name='india', title=Title('India')),
                        SingleChoiceElement(name='us_gov', title=Title('United States FedRAMP')),
                    ],
                    prefill=DefaultValue('default'),
                )
            ),
            'excluded_sections': DictElement(
                    parameter_form=MultipleChoice(
                        title=Title('Exclude Sections'),
                        elements=meraki_excluded_sections,
                        prefill=DefaultValue([
                            SEC_NAME_APPLIANCE_PERFORMANCE,
                            SEC_NAME_SWITCH_PORTS_STATUSES,
                            SEC_NAME_WIRELESS_DEVICE_STATUS,
                            SEC_NAME_ORG_SWITCH_PORTS_STATUSES,
                        ]),
                        # migrate=_migrate_to_valid_ident,
                    ),
                    required=True,
                ),
            'orgs': DictElement(
                parameter_form=List(
                    element_template=String(macro_support=True), title=Title('Organizations'),
                    custom_validate=(DuplicateInList(),),
                ),
            ),
            'cache_per_section': DictElement(
                parameter_form=Dictionary(
                    title=Title('Set Cache time per section'),
                    elements={
                        sec_name: DictElement(
                            parameter_form=Integer(
                                title=Title(sec_title),
                                prefill=DefaultValue(sec_cache),
                                unit_symbol='minutes',
                                custom_validate=(NumberInRange(min_value=0),)
                            )
                        ) for sec_name, sec_title, sec_cache in [
                            (SEC_NAME_APPLIANCE_PERFORMANCE, SEC_TITLE_APPLIANCE_PERFORMANCE, SEC_CACHE_APPLIANCE_PERFORMANCE),
                            (SEC_NAME_APPLIANCE_UPLINKS_USAGE, SEC_TITLE_APPLIANCE_UPLINKS_USAGE, SEC_CACHE_APPLIANCE_UPLINKS_USAGE),
                            (SEC_NAME_APPLIANCE_UPLINKS, SEC_TITLE_APPLIANCE_UPLINKS, SEC_CACHE_APPLIANCE_UPLINKS),
                            (SEC_NAME_APPLIANCE_VPNS, SEC_TITLE_APPLIANCE_VPNS, SEC_CACHE_APPLIANCE_VPNS),
                            (SEC_NAME_CELLULAR_UPLINKS, SEC_TITLE_CELLULAR_UPLINKS, SEC_CACHE_CELLULAR_UPLINKS),
                            (SEC_NAME_DEVICE_INFO, SEC_TITLE_DEVICE_INFO, SEC_CACHE_DEVICE_INFO),
                            (SEC_NAME_DEVICE_STATUSES, SEC_TITLE_DEVICE_STATUSES, SEC_CACHE_DEVICE_STATUSES),
                            (SEC_NAME_DEVICE_UPLINKS_INFO, SEC_TITLE_DEVICE_UPLINKS_INFO, SEC_CACHE_DEVICE_UPLINKS_INFO),
                            (SEC_NAME_LICENSES_OVERVIEW, SEC_TITLE_LICENSES_OVERVIEW, SEC_CACHE_LICENSES_OVERVIEW),
                            (SEC_NAME_NETWORKS, SEC_TITLE_NETWORKS, SEC_CACHE_NETWORKS),
                            (SEC_NAME_ORG_API_REQUESTS, SEC_TITLE_ORG_API_REQUESTS, SEC_CACHE_ORG_API_REQUESTS),
                            (SEC_NAME_ORG_SWITCH_PORTS_STATUSES, SEC_TITLE_ORG_SWITCH_PORTS_STATUSES, SEC_CACHE_ORG_SWITCH_PORTS_STATUSES),
                            (SEC_NAME_ORGANISATIONS, SEC_TITLE_ORGANISATIONS, SEC_CACHE_ORGANISATIONS),
                            (SEC_NAME_SENSOR_READINGS, SEC_TITLE_SENSOR_READINGS, SEC_CACHE_SENSOR_READINGS),
                            (SEC_NAME_SWITCH_PORTS_STATUSES, SEC_TITLE_SWITCH_PORTS_STATUSES, SEC_CACHE_SWITCH_PORTS_STATUSES),
                            (SEC_NAME_WIRELESS_DEVICE_STATUS, SEC_TITLE_WIRELESS_DEVICE_STATUS, SEC_CACHE_WIRELESS_DEVICE_STATUS),
                            (SEC_NAME_WIRELESS_ETHERNET_STATUSES, SEC_TITLE_WIRELESS_ETHERNET_STATUSES, SEC_CACHE_WIRELESS_ETHERNET_STATUSES),
                        ]
                    }
                )
            ),
            'sections': DictElement(
                parameter_form=MultipleChoice(
                    title=Title('Sections'),
                    elements=[
                        MultipleChoiceElement(
                            name='licenses_overview', title=Title('Organization licenses overview')
                        ),
                        MultipleChoiceElement(
                            name='device_statuses', title=Title('Organization device statuses')
                        ),
                        MultipleChoiceElement(
                            name='sensor_readings', title=Title('Organization sensor readings')
                        ),
                    ],
                    # migrate=_migrate_to_valid_ident,
                ),
                render_only=True,
            ),
        },
        # prefill=DefaultValue('excluded_sections'),
    )


rule_spec_cisco_meraki = SpecialAgent(
    name='cisco_meraki',
    title=Title('Cisco Meraki'),
    topic=Topic.NETWORKING,
    parameter_form=_form_special_agent_cisco_meraki,
)
