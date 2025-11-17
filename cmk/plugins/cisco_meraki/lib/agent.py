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
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

from .clients import MerakiClient
from .config import get_meraki_dashboard, MerakiConfig
from .constants import (
    AGENT,
    API_NAME_DEVICE_NAME,
    API_NAME_DEVICE_SERIAL,
    APIKEY_OPTION_NAME,
    SEC_NAME_DEVICE_INFO,
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_SENSOR_READINGS,
    SECTION_NAME_MAP,
)
from .log import LOGGER
from .schema import Organisation

__version__ = "2.5.0b1"


MerakiAPIData = Mapping[str, object]

# .
#   .--section-------------------------------------------------------------.
#   |                                 _   _                                |
#   |                   ___  ___  ___| |_(_) ___  _ __                     |
#   |                  / __|/ _ \/ __| __| |/ _ \| '_ \                    |
#   |                  \__ \  __/ (__| |_| | (_) | | | |                   |
#   |                  |___/\___|\___|\__|_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class MerakiAPIDataSource(Enum):
    org = auto()


@dataclass(frozen=True)
class Section:
    api_data_source: MerakiAPIDataSource
    name: str
    data: MerakiAPIData
    piggyback: str | None = None

    def get_name(self) -> str:
        return "_".join(["cisco_meraki", self.api_data_source.name, self.name])


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
    organisation: Organisation

    @property
    def organisation_id(self) -> str:
        return self.organisation["id_"]

    def query(self) -> Iterator[Section]:
        if SEC_NAME_LICENSES_OVERVIEW in self.config.section_names:
            if licenses_overview := self.client.get_licenses_overview(**self.organisation):
                yield self._make_section(
                    name=SEC_NAME_LICENSES_OVERVIEW,
                    data=licenses_overview,
                )

        if self.config.devices_required:
            devices_by_serial = self.client.get_devices(**self.organisation)
        else:
            devices_by_serial = {}

        for device in devices_by_serial.values():
            try:
                device_piggyback = str(device[API_NAME_DEVICE_NAME])
            except KeyError as e:
                LOGGER.debug(
                    "Organisation ID: %r: Get device piggyback: %r", self.organisation_id, e
                )
                continue

            yield self._make_section(
                name=SEC_NAME_DEVICE_INFO,
                data=device,
                piggyback=device_piggyback,
            )

        if SEC_NAME_DEVICE_STATUSES in self.config.section_names:
            for device_status in self.client.get_devices_statuses(self.organisation_id):
                # Empty device names are possible when reading from the meraki API, let's set the
                # piggyback to None so that the output is written to the main section.
                if (
                    piggyback := self._get_device_piggyback(device_status, devices_by_serial)
                ) is not None:
                    yield self._make_section(
                        name=SEC_NAME_DEVICE_STATUSES,
                        data=device_status,
                        piggyback=piggyback or None,
                    )

        if SEC_NAME_SENSOR_READINGS in self.config.section_names:
            for sensor_reading in self.client.get_sensor_readings(self.organisation_id):
                # Empty device names are possible when reading from the meraki API, let's set the
                # piggyback to None so that the output is written to the main section.
                if (
                    piggyback := self._get_device_piggyback(sensor_reading, devices_by_serial)
                ) is not None:
                    yield self._make_section(
                        name=SEC_NAME_SENSOR_READINGS,
                        data=sensor_reading,
                        piggyback=piggyback or None,
                    )

    def _get_device_piggyback(
        self, device: MerakiAPIData, devices_by_serial: Mapping[str, MerakiAPIData]
    ) -> str | None:
        try:
            serial = str(device[API_NAME_DEVICE_SERIAL])
            return str(devices_by_serial[serial][API_NAME_DEVICE_NAME])
        except KeyError as e:
            LOGGER.debug("Organisation ID: %r: Get device piggyback: %r", self.organisation_id, e)
            return None

    def _make_section(
        self, *, name: str, data: MerakiAPIData, piggyback: str | None = None
    ) -> Section:
        return Section(
            api_data_source=MerakiAPIDataSource.org,
            name=SECTION_NAME_MAP[name],
            data=data,
            piggyback=piggyback,
        )


def _query_meraki_objects(*, organisations: Sequence[MerakiOrganisation]) -> Iterable[Section]:
    for organisation in organisations:
        yield from organisation.query()


def _write_sections(sections: Iterable[Section]) -> None:
    sections_by_piggyback: dict = {}
    for section in sections:
        sections_by_piggyback.setdefault(section.piggyback, {}).setdefault(
            section.get_name(), []
        ).append(section.data)

    for piggyback, pb_section in sections_by_piggyback.items():
        sys.stdout.write(f"<<<<{piggyback or ''}>>>>\n")
        for section_name, section_data in pb_section.items():
            sys.stdout.write(
                f"<<<{section_name}:sep(0)>>>\n{json.dumps(section_data, sort_keys=True)}\n"
            )
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
        "--no-cache",
        default=False,
        action="store_const",
        const=True,
        help="Always fetch data from Meraki API.",
    )

    parser.add_argument("--cache-devices", type=int, default=60)
    parser.add_argument("--cache-device-statuses", type=int, default=60)
    parser.add_argument("--cache-licenses-overview", type=int, default=600)
    parser.add_argument("--cache-organizations", type=int, default=600)
    parser.add_argument("--cache-sensor-readings", type=int, default=0)

    parser.add_argument(
        "--sections",
        nargs="+",
        choices=list(SECTION_NAME_MAP),
        default=list(SECTION_NAME_MAP),
        help="Explicit sections that are collected.",
    )

    parser.add_argument(
        "--orgs",
        nargs="+",
        default=[],
        help="Explicit organisation IDs that are checked.",
    )

    return parser.parse_args(argv)


def _get_organisations(config: MerakiConfig, client: MerakiClient) -> Sequence[Organisation]:
    if not config.organizations_required:
        return []

    orgs = client.get_organizations()

    if config.org_ids:
        return [org for org in orgs if org["id_"] in config.org_ids]

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
    dashboard = get_meraki_dashboard(api_key, args.debug, args.proxy)

    ctx = MerakiRunContext(
        config=(config := MerakiConfig.build(args)),
        client=MerakiClient.build(dashboard, config),
    )

    return run(ctx)
