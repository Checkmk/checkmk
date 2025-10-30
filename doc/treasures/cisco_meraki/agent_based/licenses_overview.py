#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
    check_levels,
    render,
)
from cmk_addons.plugins.meraki.lib.utils import MerakiAPIData, add_org_id_name_to_output, load_json


@dataclass(frozen=True)
class LicensesOverview:
    status: str
    expiration_date: datetime | None
    licensed_device_counts: Mapping[str, int]
    organisation_id: str
    organisation_name: str

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "LicensesOverview":
        return cls(
            status=str(row["status"]),
            expiration_date=cls._parse_expiration_date(str(row["expirationDate"])),
            licensed_device_counts=(
                counts if isinstance(counts := row["licensedDeviceCounts"], dict) else {}
            ),
            organisation_id=row['organisation_id'],
            organisation_name=row['organisation_name'],
        )

    @staticmethod
    def _parse_expiration_date(raw_expiration_date: str) -> datetime | None:
        try:
            return datetime.strptime(raw_expiration_date, "%b %d, %Y %Z")
        except ValueError:
            return None


Section = Mapping[str, LicensesOverview]


def parse_licenses_overview(string_table: StringTable) -> Section:
    return {
        f"{row['organisation_id']}": LicensesOverview.parse(row) for row in load_json(string_table)
    }


agent_section_cisco_meraki_org_licenses_overview = AgentSection(
    name="cisco_meraki_org_licenses_overview",
    parse_function=parse_licenses_overview,
)


def discover_licenses_overview(params: Mapping[str, str], section: Section) -> DiscoveryResult:
    for organisation_id in section:
        match params['item_variant']:
            case 'org_id':
                item = organisation_id
            case 'org_name':
                item = f'{section[organisation_id].organisation_name}'
            case _:
                item = f'{section[organisation_id].organisation_name}/{organisation_id}'

        yield Service(
            item=item,
            parameters={
                'internal_item_name': organisation_id,
                'item_variant': params['item_variant'],
                'old_item_name': f'{section[organisation_id].organisation_name}/{organisation_id}',
            })


def check_licenses_overview(
    item: str,
    params: Mapping[str, any],
    section: Section,
) -> CheckResult:
    if not params.get('internal_item_name'):
        yield Result(
            state=State.WARN,
            summary='This host is using old discovery parameters. Do a rediscover (tabula rasa) for this host please.',
        )
        item = params.get('old_item_name', item)

    if (item_data := section.get(params.get('internal_item_name', item))) is None:
        return

    yield from add_org_id_name_to_output(
        item_data.organisation_id,
        item_data.organisation_name,
        params['item_variant'],
        params.get('dont_show_alias_on_info'),
    )

    yield Result(
        state=State.OK if item_data.status == "OK" else State(params['state_license_not_ok']),
        summary=f"Status: {item_data.status}",
    )

    if item_data.expiration_date is not None:
        yield from _check_expiration_date(item_data.expiration_date, params)

    if item_data.licensed_device_counts:
        licensed_devices = sum(item_data.licensed_device_counts.values())
        yield Result(
            state=State.OK,
            summary=f'Licensed devices: {licensed_devices}'
        )
        yield Metric(value=licensed_devices, name='sum_licensed_devices')

    for device_type, device_count in sorted(item_data.licensed_device_counts.items(), key=lambda t: t[0], ):
        yield Result(state=State.OK, notice=f"{device_type}: {device_count} licensed devices")


def _check_expiration_date(
    expiration_date: datetime,
    params: Mapping[str, any],
) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Expiration date: {expiration_date.strftime('%Y-%m-%d')}",  # changed from US format
    )

    age = expiration_date.timestamp() - time.time()
    levels_lower = params.get("remaining_expiration_time")

    if age < 0:
        yield Result(
            state=State.CRIT,
            summary=f"Licenses expired: {render.timespan(abs(age))} ago",
        )
        yield Metric(
            value=age,
            name='remaining_time',
            levels=levels_lower
        )

    else:
        yield from check_levels(
            value=age,
            levels_lower=levels_lower,
            label="Remaining time",
            render_func=render.timespan,
            # metric_name="remaining_time"
        )
        # needed as lower levels don't go the graphing system
        yield Metric(
            value=age,
            name='remaining_time',
            levels=levels_lower[1] if levels_lower else None
        )


check_plugin_cisco_meraki_org_licenses_overview=CheckPlugin(
    name="cisco_meraki_org_licenses_overview",
    service_name="Cisco Meraki Licenses %s",
    discovery_function=discover_licenses_overview,
    discovery_ruleset_name='discovery_meraki_organisations',
    discovery_default_parameters={
        'item_variant': 'org_id_name',
    },
    check_function=check_licenses_overview,
    check_ruleset_name="cisco_meraki_org_licenses_overview",
    check_default_parameters={
        'state_license_not_ok': 1,
    },
)


#
# inventory license overview
#
# ToDo: add senors (MT) -> do the need a license? -> done
def inventory_licenses_overview(section: Section | None) -> InventoryResult:
    path = ['software', 'applications', 'cisco_meraki', 'licenses']
    for org_id, org_data in section.items():
        licenses = {'org_name': org_data.organisation_name}
        for device_type, device_count in org_data.licensed_device_counts.items():
            if device_type.lower().startswith('mg'):  # gateways
                licenses.update({'mg': licenses.get('mg', 0) + device_count})
            elif device_type.lower().startswith('mx'):  # firewalls
                licenses.update({'mx': licenses.get('mx', 0) + device_count})
            elif device_type.lower().startswith('ms'):  # switches
                licenses.update({'ms': licenses.get('ms', 0) + device_count})
            elif device_type.lower().startswith('mv'):  # video / camera
                licenses.update({'mv': licenses.get('mv', 0) + device_count})
            elif device_type.lower().startswith('mt'):  # sensors
                licenses.update({'mt': licenses.get('mt', 0) + device_count})
            elif device_type.lower().startswith('mr'):  # access points
                licenses.update({'mr': licenses.get('mr', 0) + device_count})
            elif device_type.lower().startswith('wireless'):  # merge with access points
                licenses.update({'mr': licenses.get('mr', 0) + device_count})
            elif device_type.lower().startswith('sm'):  # systems manager
                licenses.update({'sm': licenses.get('sm', 0) + device_count})
            else:  # fallback for unknown device type
                licenses.update({device_type.lower(): licenses.get(device_type.lower(), 0) + device_count})
        licenses.update({'summary': sum(org_data.licensed_device_counts.values())})

        yield TableRow(
            path=path,
            key_columns={'org_id': org_id},
            inventory_columns=licenses
        )


inventory_plugin_cisco_meraki_org_licenses_overview=InventoryPlugin(
    name="cisco_meraki_org_licenses_overview",
    inventory_function=inventory_licenses_overview,
    sections=['cisco_meraki_org_licenses_overview']
)
