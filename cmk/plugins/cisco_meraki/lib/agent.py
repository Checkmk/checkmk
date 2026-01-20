#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_cisco_meraki

Checkmk special agent for monitoring Cisco Meraki.
"""
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

from .clients import MerakiClient
from .config import get_meraki_dashboard, MerakiConfig
from .constants import (
    AGENT,
    APIKEY_OPTION_NAME,
    OPTIONAL_SECTIONS_CHOICES,
    OPTIONAL_SECTIONS_DEFAULT,
)
from .log import LOGGER
from .schema import (
    ApiResponseCodes,
    Device,
    RawOrganisation,
    UplinkStatuses,
    UplinkUsageByInterface,
)

__version__ = "2.6.0b1"


# .
#   .--section-------------------------------------------------------------.
#   |                                 _   _                                |
#   |                   ___  ___  ___| |_(_) ___  _ __                     |
#   |                  / __|/ _ \/ __| __| |/ _ \| '_ \                    |
#   |                  \__ \  __/ (__| |_| | (_) | | | |                   |
#   |                  |___/\___|\___|\__|_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class Section:
    name: str
    data: Mapping[str, object]
    piggyback: str | None = None


# .
#   .--queries-------------------------------------------------------------.
#   |                                        _                             |
#   |                   __ _ _   _  ___ _ __(_) ___  ___                   |
#   |                  / _` | | | |/ _ \ '__| |/ _ \/ __|                  |
#   |                 | (_| | |_| |  __/ |  | |  __/\__ \                  |
#   |                  \__, |\__,_|\___|_|  |_|\___||___/                  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class MerakiOrganisation:
    config: MerakiConfig
    client: MerakiClient
    organisation: RawOrganisation

    @property
    def id(self) -> str:
        return self.organisation["id"]

    @property
    def name(self) -> str:
        return self.organisation["name"]

    @property
    def api_disabled(self) -> bool:
        return not self.organisation["api"]["enabled"]

    def query(self) -> Iterator[Section]:
        yield Section(
            name="cisco_meraki_org_organisations",
            data=self.organisation,
        )

        if self.config.required.api_response_codes:
            for raw_response_codes in self.client.get_api_response_codes(self.id):
                response_codes = ApiResponseCodes(
                    organization_id=self.id,
                    organization_name=self.name,
                    **raw_response_codes,
                )
                yield Section(
                    name="cisco_meraki_org_api_response_codes",
                    data=response_codes,
                )

        # If API is disabled for organization, it doesn't make sense to continue.
        if self.api_disabled:
            return

        if self.config.required.licenses_overview:
            if licenses_overview := self.client.get_licenses_overview(self.id, self.name):
                yield Section(
                    name="cisco_meraki_org_licenses_overview",
                    data=licenses_overview,
                )

        if networks := {net["id"]: net for net in self.client.get_networks(self.id, self.name)}:
            yield Section(name="cisco_meraki_org_networks", data=networks)

        devices_by_serial: dict[str, Device] = {}

        if self.config.required.devices:
            for raw_device in self.client.get_devices(self.id):
                network = networks.get(raw_device["networkId"])
                serial = raw_device["serial"]

                devices_by_serial[serial] = Device(
                    organisation_id=self.id,
                    organisation_name=self.name,
                    network_name=network["name"] if network else "",
                    **raw_device,
                )

        # If no devices are available for organization, it doesn't make sense to continue.
        if not devices_by_serial:
            return

        for device in devices_by_serial.values():
            serial = device["serial"]
            yield Section(
                name="cisco_meraki_org_device_info",
                data=device,
                piggyback=self._get_device_piggyback(serial, devices_by_serial),
            )

        if self.config.required.device_statuses:
            for device_status in self.client.get_devices_statuses(self.id):
                serial = device_status["serial"]
                if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                    yield Section(
                        name="cisco_meraki_org_device_status",
                        data=device_status,
                        piggyback=piggyback,
                    )

        if self.config.required.device_uplinks_info:
            for uplink_address in self.client.get_device_uplink_addresses(self.id):
                serial = uplink_address["serial"]
                if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                    yield Section(
                        name="cisco_meraki_org_device_uplinks_info",
                        data=uplink_address,
                        piggyback=piggyback,
                    )

        devices_by_type = defaultdict(list)
        for device in devices_by_serial.values():
            devices_by_type[device["productType"]].append(device)

        if devices_by_type.get("sensor"):
            if self.config.required.sensor_readings:
                for sensor_reading in self.client.get_sensor_readings(self.id):
                    serial = sensor_reading["serial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        yield Section(
                            name="cisco_meraki_org_sensor_readings",
                            data=sensor_reading,
                            piggyback=piggyback,
                        )

        if devices_by_type.get("appliance"):
            if self.config.required.appliance_uplinks:
                for raw_statuses in self.client.get_uplink_statuses(self.id):
                    serial = raw_statuses["serial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        uplink_statuses = UplinkStatuses(
                            networkName=networks[raw_statuses["networkId"]]["organizationName"],
                            usageByInterface=self._get_usage_by_serial(),
                            **raw_statuses,
                        )
                        yield Section(
                            name="cisco_meraki_org_appliance_uplinks",
                            data=uplink_statuses,
                            piggyback=piggyback,
                        )

            if self.config.required.appliance_vpns:
                for vpn_status in self.client.get_uplink_vpn_statuses(self.id):
                    serial = vpn_status["deviceSerial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        yield Section(
                            name="cisco_meraki_org_appliance_vpns",
                            data=vpn_status,
                            piggyback=piggyback,
                        )

            if self.config.required.appliance_performance:
                for device in devices_by_type["appliance"]:
                    serial = device["serial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        for appliance_performance in self.client.get_appliance_performance(serial):
                            yield Section(
                                name="cisco_meraki_org_appliance_performance",
                                data=appliance_performance,
                                piggyback=piggyback,
                            )

        if devices_by_type.get("wireless"):
            if self.config.required.wireless_device_statuses:
                for device in devices_by_type["wireless"]:
                    serial = device["serial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        for wireless_device in self.client.get_wireless_device_statuses(serial):
                            yield Section(
                                name="cisco_meraki_org_wireless_device_statuses",
                                data=wireless_device,
                                piggyback=piggyback,
                            )

            if self.config.required.wireless_ethernet_statuses:
                for wireless_ethernet_status in self.client.get_wireless_ethernet_statuses(self.id):
                    serial = wireless_ethernet_status["serial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        yield Section(
                            name="cisco_meraki_org_wireless_ethernet_statuses",
                            data=wireless_ethernet_status,
                            piggyback=piggyback,
                        )

        if devices_by_type.get("switch"):
            if self.config.required.switch_port_statuses:
                for switch in devices_by_type["switch"]:
                    serial = switch["serial"]
                    if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                        for switch_port_status in self.client.get_switch_port_statuses(serial):
                            yield Section(
                                name="cisco_meraki_org_switch_port_statuses",
                                data=switch_port_status,
                                piggyback=piggyback,
                            )

    def _get_device_piggyback(
        self, serial: str, devices_by_serial: Mapping[str, Device]
    ) -> str | None:
        if (device := devices_by_serial.get(serial)) is None:
            LOGGER.debug("Device piggyback not found: org_id=%r, device=%r", self.id, serial)
            return None

        net_id_prefix = f"{net_id}-" if (net_id := device.get("networkId")) else ""

        match self.config:
            case MerakiConfig(org_id_as_prefix=True, net_id_as_prefix=True):
                prefix = f"{self.id}-{net_id_prefix}"
            case MerakiConfig(org_id_as_prefix=True):
                prefix = f"{self.id}-"
            case MerakiConfig(net_id_as_prefix=True):
                prefix = net_id_prefix
            case _:
                prefix = ""

        if device_name := device.get("name"):
            return f"{prefix}{device_name}"

        if product_type := device.get("productType"):
            return f"{prefix}{serial}-{product_type}"

        return None

    def _get_usage_by_serial(self) -> UplinkUsageByInterface:
        return {
            uplink["interface"]: {
                "sent": uplink["sent"],
                "received": uplink["received"],
            }
            for network in self.client.get_uplink_usage(self.id)
            for uplink in network["byUplink"]
        }


def _query_meraki_objects(*, organisations: Sequence[MerakiOrganisation]) -> Iterable[Section]:
    for organisation in organisations:
        yield from organisation.query()


def _write_sections(sections: Iterable[Section]) -> None:
    sections_by_piggyback: dict = {}
    for section in sections:
        sections_by_piggyback.setdefault(section.piggyback, {}).setdefault(section.name, []).append(
            section.data
        )

    for piggyback, pb_section in sections_by_piggyback.items():
        sys.stdout.write(f"<<<<{piggyback or ''}>>>>\n")
        for section_name, section_data in pb_section.items():
            sys.stdout.write(f"<<<{section_name}:sep(0)>>>\n")
            sys.stdout.write(f"{json.dumps(section_data, sort_keys=True)}\n")
        sys.stdout.write("<<<<>>>>\n")


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )

    parser.add_argument("hostname")

    parser_add_secret_option(
        parser,
        long=f"--{APIKEY_OPTION_NAME}",
        required=True,
        help="API key for the Meraki API dashboard access.",
    )

    parser.add_argument("--proxy", type=str)

    parser.add_argument(
        "--region",
        choices=["default", "canada", "china", "india", "us_gov"],
        default="default",
    )

    parser.add_argument(
        "--org-id-as-prefix",
        default=False,
        action="store_const",
        const=True,
        help="Use organisation ID as device piggyback prefix.",
    )

    parser.add_argument(
        "--net-id-as-prefix",
        default=False,
        action="store_const",
        const=True,
        help="Use network ID as device piggyback prefix.",
    )

    parser.add_argument(
        "--no-cache",
        default=False,
        action="store_const",
        const=True,
        help="Always fetch data from Meraki API.",
    )

    parser.add_argument(
        "--timespan",
        default=900,  # 15 minutes
        help="The interval for which the information will be fetched in seconds.",
    )

    parser.add_argument("--cache-appliance-uplinks", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-appliance-vpns", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-devices", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-device-statuses", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-device-uplinks-info", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-licenses-overview", type=float, default=36000.0)  # 10 hours
    parser.add_argument("--cache-networks", type=float, default=36000.0)  # 10 hours
    parser.add_argument("--cache-organizations", type=float, default=36000.0)  # 10 hours
    parser.add_argument("--cache-wireless-device-statuses", type=float, default=1800.0)  # 30 mins
    parser.add_argument("--cache-wireless-ethernet-statuses", type=float, default=1800.0)  # 30 mins

    parser.add_argument(
        "--sections",
        nargs="+",
        choices=OPTIONAL_SECTIONS_CHOICES,
        default=OPTIONAL_SECTIONS_DEFAULT,
        help="Optional sections to be collected.",
    )

    parser.add_argument(
        "--orgs",
        nargs="+",
        default=[],
        help="Explicit organisation IDs that are checked.",
    )

    return parser.parse_args(argv)


def _get_organisations(config: MerakiConfig, client: MerakiClient) -> Sequence[RawOrganisation]:
    orgs = client.get_organizations()

    if config.org_ids:
        return [org for org in orgs if org["id"] in config.org_ids]

    return orgs


@dataclass(frozen=True, kw_only=True)
class MerakiRunContext:
    config: MerakiConfig
    client: MerakiClient


def run(ctx: MerakiRunContext) -> int:
    sections = _query_meraki_objects(
        organisations=[
            MerakiOrganisation(ctx.config, ctx.client, organisation)
            for organisation in _get_organisations(ctx.config, ctx.client)
        ]
    )

    _write_sections(sections)
    return 0


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    args = parse_arguments(sys.argv[1:])

    api_key = resolve_secret_option(args, APIKEY_OPTION_NAME).reveal()
    dashboard = get_meraki_dashboard(api_key, args.region, args.debug, args.proxy)

    ctx = MerakiRunContext(
        config=(config := MerakiConfig.build(args)),
        client=MerakiClient(dashboard, config),
    )

    return run(ctx)


if __name__ == "__main__":
    sys.exit(main())
