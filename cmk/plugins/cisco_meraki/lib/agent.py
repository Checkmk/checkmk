#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from .schema import Device, RawOrganisation, UplinkStatuses, UplinkUsageByInterface

__version__ = "2.5.0b1"


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

        # If API is disabled for organization, it doesn't make sense to continue.
        if self.api_disabled:
            return

        if self.config.required.licenses_overview:
            if licenses_overview := self.client.get_licenses_overview(self.id, self.name):
                yield Section(
                    name="cisco_meraki_org_licenses_overview",
                    data=licenses_overview,
                )

        if self.config.required.devices:
            devices_by_serial = self.client.get_devices(self.id, self.name)
        else:
            devices_by_serial = {}

        # If no devices are available for organization, it doesn't make sense to continue.
        if not devices_by_serial:
            return

        for device in devices_by_serial.values():
            yield Section(
                name="cisco_meraki_org_device_info",
                data=device,
                piggyback=self._get_device_piggyback(device["serial"], devices_by_serial),
            )

        if self.config.required.device_statuses:
            for device_status in self.client.get_devices_statuses(self.id):
                # Empty device names are possible when reading from the meraki API, let's set the
                # piggyback to None so that the output is written to the main section.
                if (
                    piggyback := self._get_device_piggyback(
                        device_status["serial"], devices_by_serial
                    )
                ) is not None:
                    yield Section(
                        name="cisco_meraki_org_device_status",
                        data=device_status,
                        piggyback=piggyback or None,
                    )

        devices_by_type = defaultdict(list)
        for device in devices_by_serial.values():
            devices_by_type[device["productType"]].append(device)

        if devices_by_type.get("sensor"):
            if self.config.required.sensor_readings:
                for sensor_reading in self.client.get_sensor_readings(self.id):
                    # Empty device names are possible when reading from the meraki API, let's set the
                    # piggyback to None so that the output is written to the main section.
                    if (
                        piggyback := self._get_device_piggyback(
                            sensor_reading["serial"], devices_by_serial
                        )
                    ) is not None:
                        yield Section(
                            name="cisco_meraki_org_sensor_readings",
                            data=sensor_reading,
                            piggyback=piggyback or None,
                        )

        if networks := {net["id"]: net for net in self.client.get_networks(self.id, self.name)}:
            yield Section(name="cisco_meraki_org_networks", data=networks)

        if devices_by_type.get("appliance"):
            if self.config.required.appliance_uplinks:
                for raw_data in self.client.get_uplink_statuses(self.id):
                    if piggyback := self._get_device_piggyback(
                        raw_data["serial"], devices_by_serial
                    ):
                        uplink_statuses = UplinkStatuses(
                            networkName=networks[raw_data["networkId"]]["organizationName"],
                            usageByInterface=self._get_usage_by_serial(),
                            **raw_data,
                        )
                        yield Section(
                            name="cisco_meraki_org_appliance_uplinks",
                            data=uplink_statuses,
                            piggyback=piggyback,
                        )

            if self.config.required.appliance_vpns:
                for vpn_status in self.client.get_uplink_vpn_statuses(self.id):
                    if piggyback := self._get_device_piggyback(
                        vpn_status["deviceSerial"], devices_by_serial
                    ):
                        yield Section(
                            name="cisco_meraki_org_appliance_vpns",
                            data=vpn_status,
                            piggyback=piggyback,
                        )

            if self.config.required.appliance_performance:
                for device in devices_by_type["appliance"]:
                    serial = device["serial"]
                    for appliance_performance in self.client.get_appliance_performance(serial):
                        if piggyback := self._get_device_piggyback(serial, devices_by_serial):
                            yield Section(
                                name="cisco_meraki_org_appliance_performance",
                                data=appliance_performance,
                                piggyback=piggyback,
                            )

    def _get_device_piggyback(
        self, serial: str, devices_by_serial: Mapping[str, Device]
    ) -> str | None:
        prefix = self._get_piggyback_prefix()
        try:
            return f"{prefix}{devices_by_serial[serial]['name']}"
        except KeyError as e:
            LOGGER.debug("Organisation ID: %r: Get device piggyback: %r", self.id, e)
            return None

    def _get_piggyback_prefix(self) -> str:
        prefix = ""
        if self.config.org_id_as_prefix:
            prefix += self.id + "-"
        return prefix

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
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
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
        "--no-cache",
        default=False,
        action="store_const",
        const=True,
        help="Always fetch data from Meraki API.",
    )

    parser.add_argument("--cache-appliance-uplinks", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-appliance-vpns", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-devices", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-device-statuses", type=float, default=3600.0)  # 1 hour
    parser.add_argument("--cache-licenses-overview", type=float, default=36000.0)  # 10 hours
    parser.add_argument("--cache-networks", type=float, default=36000.0)  # 10 hours
    parser.add_argument("--cache-organizations", type=float, default=36000.0)  # 10 hours
    parser.add_argument("--cache-sensor-readings", type=float, default=0.0)  # 0 minutes

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
