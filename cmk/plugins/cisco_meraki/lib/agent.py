#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import abc
import argparse
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from typing import TypedDict

import meraki  # type: ignore[import-untyped,unused-ignore,import-not-found]

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace
from cmk.special_agents.v0_unstable.misc import DataCache

from .config import get_meraki_dashboard, MerakiConfig
from .constants import (
    AGENT,
    API_NAME_DEVICE_NAME,
    API_NAME_DEVICE_SERIAL,
    API_NAME_ORGANISATION_ID,
    API_NAME_ORGANISATION_NAME,
    APIKEY_OPTION_NAME,
    SEC_NAME_DEVICE_INFO,
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_SENSOR_READINGS,
    SECTION_NAME_MAP,
)
from .log import LOGGER

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
#   .--caches--------------------------------------------------------------.
#   |                                  _                                   |
#   |                    ___ __ _  ___| |__   ___  ___                     |
#   |                   / __/ _` |/ __| '_ \ / _ \/ __|                    |
#   |                  | (_| (_| | (__| | | |  __/\__ \                    |
#   |                   \___\__,_|\___|_| |_|\___||___/                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class _Organisation(TypedDict):
    # See https://developer.cisco.com/meraki/api-v1/#!get-organizations
    # if you want to extend this
    id_: str
    name: str


class _ABCGetOrganisationsCache(DataCache):
    def __init__(self, config: MerakiConfig) -> None:
        super().__init__(config.cache_dir / config.hostname / "organisations", "organisations")
        self._dashboard = config.dashboard

    @property
    def cache_interval(self) -> int:
        # Once per day
        return 86400

    def get_validity_from_args(self, *args: object) -> bool:
        (org_ids,) = args
        try:
            cache_ids = [org["id_"] for org in self.get_cached_data()]
        except FileNotFoundError:
            cache_ids = []
        return cache_ids == org_ids

    @abc.abstractmethod
    def get_live_data(self, *args: object) -> Sequence[_Organisation]:
        raise NotImplementedError()


class GetOrganisationsByIDCache(_ABCGetOrganisationsCache):
    def __init__(self, config: MerakiConfig, org_ids: Sequence[str]) -> None:
        super().__init__(config)
        self._org_ids = org_ids

    def get_live_data(self, *args: object) -> Sequence[_Organisation]:
        def _get_organisation(org_id: str) -> _Organisation:
            try:
                org = self._dashboard.organizations.getOrganization(org_id)
            except meraki.exceptions.APIError as e:
                LOGGER.debug("Get organisation by ID %r: %r", org_id, e)
                return _Organisation(id_=org_id, name="")
            return _Organisation(
                id_=org[API_NAME_ORGANISATION_ID],
                name=org[API_NAME_ORGANISATION_NAME],
            )

        return [_get_organisation(org_id) for org_id in self._org_ids]


class GetOrganisationsCache(_ABCGetOrganisationsCache):
    def get_live_data(self, *args: object) -> Sequence[_Organisation]:
        try:
            return [
                _Organisation(
                    id_=organisation[API_NAME_ORGANISATION_ID],
                    name=organisation[API_NAME_ORGANISATION_NAME],
                )
                for organisation in self._dashboard.organizations.getOrganizations()
            ]
        except meraki.exceptions.APIError as e:
            LOGGER.debug("Get organisations: %r", e)
            return []


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
    organisation: _Organisation

    @property
    def organisation_id(self) -> str:
        return self.organisation["id_"]

    def query(self) -> Iterator[Section]:
        if SEC_NAME_LICENSES_OVERVIEW in self.config.section_names:
            if licenses_overview := self._get_licenses_overview():
                yield self._make_section(
                    name=SEC_NAME_LICENSES_OVERVIEW,
                    data=licenses_overview,
                )

        if self.config.devices_required:
            devices_by_serial = self._get_devices_by_serial()
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
            for device_status in self._get_device_statuses():
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
            for sensor_reading in self._get_sensor_readings():
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

    def _get_licenses_overview(self) -> MerakiAPIData | None:
        def _update_licenses_overview(
            licenses_overview: dict[str, object] | None,
        ) -> MerakiAPIData | None:
            if not licenses_overview:
                return None
            licenses_overview.update(
                {
                    "organisation_id": self.organisation["id_"],
                    "organisation_name": self.organisation["name"],
                }
            )
            return licenses_overview

        try:
            return _update_licenses_overview(
                self.config.dashboard.organizations.getOrganizationLicensesOverview(
                    self.organisation_id,
                )
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug("Organisation ID: %r: Get license overview: %r", self.organisation_id, e)
            return None

    def _get_devices_by_serial(self) -> Mapping[str, MerakiAPIData]:
        def _update_device(device: dict[str, object]) -> MerakiAPIData:
            device.update(
                {
                    "organisation_id": self.organisation["id_"],
                    "organisation_name": self.organisation["name"],
                }
            )
            return device

        try:
            return {
                str(device[API_NAME_DEVICE_SERIAL]): _update_device(device)
                for device in self.config.dashboard.organizations.getOrganizationDevices(
                    self.organisation_id, total_pages="all"
                )
            }
        except meraki.exceptions.APIError as e:
            LOGGER.debug("Organisation ID: %r: Get devices: %r", self.organisation_id, e)
            return {}

    def _get_device_statuses(self) -> Sequence[MerakiAPIData]:
        try:
            return self.config.dashboard.organizations.getOrganizationDevicesStatuses(
                self.organisation_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug("Organisation ID: %r: Get device statuses: %r", self.organisation_id, e)
            return []

    def _get_sensor_readings(self) -> Sequence[MerakiAPIData]:
        try:
            return self.config.dashboard.sensor.getOrganizationSensorReadingsLatest(
                self.organisation_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug("Organisation ID: %r: Get sensor readings: %r", self.organisation_id, e)
            return []

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


def _get_organisations(config: MerakiConfig, org_ids: Sequence[str]) -> Sequence[_Organisation]:
    if not config.organizations_required:
        return []
    return (
        GetOrganisationsByIDCache(config, org_ids) if org_ids else GetOrganisationsCache(config)
    ).get_data(org_ids)


def agent_cisco_meraki_main(args: argparse.Namespace) -> int:
    api_key = resolve_secret_option(args, APIKEY_OPTION_NAME).reveal()
    dashboard = get_meraki_dashboard(api_key, args.debug, args.proxy)
    config = MerakiConfig.build(dashboard, args.hostname, args.sections)

    sections = _query_meraki_objects(
        organisations=[
            MerakiOrganisation(config, organisation)
            for organisation in _get_organisations(config, args.orgs)
        ]
    )

    _write_sections(sections)
    return 0


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    args = parse_arguments(sys.argv[1:])
    return agent_cisco_meraki_main(args)
