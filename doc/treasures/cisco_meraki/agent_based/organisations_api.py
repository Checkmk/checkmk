#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
    check_levels,
)
from cmk_addons.plugins.meraki.lib.utils import add_org_id_name_to_output, get_int, load_json


__orgaisations = [
    {'id': '610473',
     'name': 'Org Name',
     'url': 'https://12345.meraki.com/o/lt-Wka/manage/organization/overview',
     'api': {'enabled': True},
     'licensing': {'model': 'co-term'},
     'cloud': {'region': {'name': 'Europe'}},
     'management': {'details': []}},
]

__api_requests = [
    [
        {
            "counts": [
                {
                    "code": 200,
                    "count": 11
                }
            ],
            "endTs": "2024-05-12T12:00:00.000000Z",
            "startTs": "2024-05-12T11:58:00.000000Z"
        },
        {
            "counts": [
                {
                    "code": 200,
                    "count": 38
                },
                {
                    "code": 400,
                    "count": 3
                }
            ],
            "endTs": "2024-05-12T11:54:00.000000Z",
            "startTs": "2024-05-12T11:52:00.000000Z"
        },
    ]
]


@dataclass(frozen=True)
class Organisation:
    id: str | None
    name: str | None
    url: str | None
    api: bool | None
    licensing: str | None
    cloud: bool | None
    management: Mapping[any] | None

    @classmethod
    def parse(cls, org: Mapping[str, object]):
        return cls(
            id=str(org['id']) if org.get('id') is not None else None,
            name=str(org['name']) if org.get('name') is not None else None,
            url=str(org['url']) if org.get('url') is not None else None,
            api=bool(org['api']['enabled']) if org.get('api', {}).get('enabled') is not None else None,
            licensing=str(org['licensing']['model']) if org.get('licensing', {}).get('model') is not None else None,
            cloud=bool(org['cloud']['region']['name']) if org.get('cloud', {}).get('region', {}).get(
                'name') is not None else None,
            management=org['management'] if org.get('management') is not None else None,
        )


@dataclass(frozen=True)
class OrganizationApiCount:
    code: int
    count: int

    @classmethod
    def parse(cls, code: Mapping[str, str]):
        return cls(
            code=get_int(code.get('code')),
            count=get_int(code.get('count'))
        )


_api_status = {
    True: 'enabled',
    False: 'disabled',
}


def parse_meraki_organisations(string_table: StringTable) -> Mapping[str, Organisation] | None:
    if json_data := load_json(string_table):
        return {org['id']: Organisation.parse(org) for org in json_data}


agent_section_cisco_meraki_org_organisations = AgentSection(
    name='cisco_meraki_org_organisations',
    parsed_section_name='cisco_meraki_organisations_api',
    parse_function=parse_meraki_organisations,
)


def parse_cisco_meraki_org_api_requests_by_organization(
        string_table: StringTable
) -> Mapping[str, Sequence[OrganizationApiCount]] | None:
    if json_data := load_json(string_table):
        return {
            entry['org_id']: [
                OrganizationApiCount.parse(code) for code in entry['requests'][0]['counts']
            ] for entry in json_data
        }


agent_section_cisco_meraki_org_api_requests_by_organization = AgentSection(
    name='cisco_meraki_org_api_requests_by_organization',
    parsed_section_name='cisco_meraki_org_api_requests_by_organization',
    parse_function=parse_cisco_meraki_org_api_requests_by_organization,
)


def inventory_meraki_organisations(section: Mapping[str, Organisation]) -> InventoryResult:
    path = ['software', 'applications', 'cisco_meraki', 'organisations']

    for org in section.values():
        yield TableRow(
            path=path,
            key_columns={'org_id': org.id},
            inventory_columns={
                'org_name': org.name,
                'url': org.url,
                'api': _api_status[org.api],
                'licensing': org.licensing,
                'cloud': org.cloud,
            }
        )


inventory_plugin_cisco_meraki_organisations_api = InventoryPlugin(
    name='cisco_meraki_organisations_api',
    # sections=['cisco_meraki_organisations'],
    inventory_function=inventory_meraki_organisations,
)


def discover_organisations_api(
        params: Mapping[str, str],
        section_cisco_meraki_organisations_api: Mapping[str, Organisation] | None,
        section_cisco_meraki_org_api_requests_by_organization: Mapping[str, Sequence[OrganizationApiCount]] | None,
) -> DiscoveryResult:
    for organisation_id in section_cisco_meraki_organisations_api:
        match params['item_variant']:
            case 'org_id':
                item = organisation_id
            case 'org_name':
                item = f'{section_cisco_meraki_organisations_api[organisation_id].name}'
            case _:
                item = f'{section_cisco_meraki_organisations_api[organisation_id].name}/{organisation_id}'

        yield Service(
            item=item,
            parameters={
                'internal_item_name': organisation_id,
                'item_variant': params['item_variant'],
                # 'old_item_name': f'{section[organisation_id].organisation_name}/{organisation_id}',
            })


def check_organisations_api(
        item: str,
        params: Mapping[str, any],
        section_cisco_meraki_organisations_api: Mapping[str, Organisation] | None,
        section_cisco_meraki_org_api_requests_by_organization: Mapping[str, Sequence[OrganizationApiCount]] | None,
) -> CheckResult:
    if (org := section_cisco_meraki_organisations_api.get(params.get('internal_item_name'))) is None:
        return

    yield from add_org_id_name_to_output(
        org.id,
        org.name,
        params['item_variant'],
        params.get('dont_show_alias_on_info'),
    )

    yield Result(
        state=State.OK if org.api else State(params['state_api_not_enabled']),
        summary=f'({_api_status[org.api]})',
        details=f'Status: {_api_status[org.api]}',
    )

    if section_cisco_meraki_org_api_requests_by_organization is None or (
            api_requests := section_cisco_meraki_org_api_requests_by_organization.get(params.get(
                'internal_item_name'
            ))
    ) is None:
        return

    code_2xx = 0
    code_3xx = 0
    code_4xx = 0
    code_5xx = 0
    for entry in api_requests:
        if 199 < entry.code < 300:
            code_2xx += entry.count
        elif 299 < entry.code < 400:
            code_3xx += entry.count
        elif 399 < entry.code < 500:
            code_4xx += entry.count
        elif 499 < entry.code < 600:
            code_5xx += entry.count

    for value, label, metric in [
        (code_2xx, 'Code 2xx', '2xx'),
        (code_3xx, 'Code 3xx', '3xx'),
        (code_4xx, 'Code 4xx', '4xx'),
        (code_5xx, 'Code 5xx', '5xx'),
    ]:
        if value > 0:
            yield from check_levels(
                value=value,
                label=label,
                render_func=lambda v: f'{v}',
                metric_name=f'api_code_{metric}',
                notice_only=False,
            )


check_plugin_cisco_meraki_organisations_api = CheckPlugin(
    name='cisco_meraki_organisations_api',
    sections=['cisco_meraki_organisations_api', 'cisco_meraki_org_api_requests_by_organization'],
    service_name='Cisco Meraki API %s',
    discovery_function=discover_organisations_api,
    discovery_ruleset_name='discovery_meraki_organisations',
    discovery_default_parameters={
        'item_variant': 'org_id_name',
    },
    check_function=check_organisations_api,
    check_ruleset_name='cisco_meraki_organisations_api',
    check_default_parameters={
        'state_api_not_enabled': 1,
    },
)
