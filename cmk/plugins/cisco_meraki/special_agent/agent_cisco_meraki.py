#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import argparse
import logging
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
from typing import Final, TypedDict

import meraki  # type: ignore[import-untyped]

from cmk.utils import password_store
from cmk.utils.paths import tmp_dir

from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.misc import DataCache

_LOGGER = logging.getLogger("agent_cisco_meraki")

_BASE_CACHE_FILE_DIR = Path(tmp_dir) / "agents" / "agent_cisco_meraki"

_API_NAME_ORGANISATION_ID: Final = "id"
_API_NAME_ORGANISATION_NAME: Final = "name"
_API_NAME_DEVICE_SERIAL: Final = "serial"
_API_NAME_DEVICE_NAME: Final = "name"

_SEC_NAME_LICENSES_OVERVIEW: Final = "licenses-overview"
_SEC_NAME_DEVICE_INFO: Final = "_device_info"  # Not configurable, needed for piggyback
_SEC_NAME_DEVICE_STATUSES: Final = "device-statuses"
_SEC_NAME_SENSOR_READINGS: Final = "sensor-readings"

_SECTION_NAME_MAP = {
    _SEC_NAME_LICENSES_OVERVIEW: "licenses_overview",
    _SEC_NAME_DEVICE_INFO: "device_info",
    _SEC_NAME_DEVICE_STATUSES: "device_status",
    _SEC_NAME_SENSOR_READINGS: "sensor_readings",
}

MerakiAPIData = Mapping[str, object]

#   .--dashboard-----------------------------------------------------------.
#   |              _           _     _                         _           |
#   |           __| | __ _ ___| |__ | |__   ___   __ _ _ __ __| |          |
#   |          / _` |/ _` / __| '_ \| '_ \ / _ \ / _` | '__/ _` |          |
#   |         | (_| | (_| \__ \ | | | |_) | (_) | (_| | | | (_| |          |
#   |          \__,_|\__,_|___/_| |_|_.__/ \___/ \__,_|_|  \__,_|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _configure_meraki_dashboard(
    api_key: str,
    debug: bool,
    proxy: str | None,
) -> meraki.DashboardAPI:
    return meraki.DashboardAPI(
        api_key=api_key,
        print_console=True,
        output_log=False,
        suppress_logging=not (debug),
        requests_proxy=proxy,
    )


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
        super().__init__(_BASE_CACHE_FILE_DIR / config.hostname / "organisations", "organisations")
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
                _LOGGER.debug("Get organisation by ID %r: %r", org_id, e)
                return _Organisation(id_=org_id, name="")
            return _Organisation(
                id_=org[_API_NAME_ORGANISATION_ID],
                name=org[_API_NAME_ORGANISATION_NAME],
            )

        return [_get_organisation(org_id) for org_id in self._org_ids]


class GetOrganisationsCache(_ABCGetOrganisationsCache):
    def get_live_data(self, *args: object) -> Sequence[_Organisation]:
        try:
            return [
                _Organisation(
                    id_=organisation[_API_NAME_ORGANISATION_ID],
                    name=organisation[_API_NAME_ORGANISATION_NAME],
                )
                for organisation in self._dashboard.organizations.getOrganizations()
            ]
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Get organisations: %r", e)
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
        if _SEC_NAME_LICENSES_OVERVIEW in self.config.section_names:
            if licenses_overview := self._get_licenses_overview():
                yield self._make_section(
                    name=_SEC_NAME_LICENSES_OVERVIEW,
                    data=licenses_overview,
                )

        if _need_devices(self.config.section_names):
            devices_by_serial = self._get_devices_by_serial()
        else:
            devices_by_serial = {}

        for device in devices_by_serial.values():
            try:
                device_piggyback = str(device[_API_NAME_DEVICE_NAME])
            except KeyError as e:
                _LOGGER.debug(
                    "Organisation ID: %r: Get device piggyback: %r", self.organisation_id, e
                )
                continue

            yield self._make_section(
                name=_SEC_NAME_DEVICE_INFO,
                data=device,
                piggyback=device_piggyback,
            )

        if _SEC_NAME_DEVICE_STATUSES in self.config.section_names:
            for device_status in self._get_device_statuses():
                # Empty device names are possible when reading from the meraki API, let's set the
                # piggyback to None so that the output is written to the main section.
                if (
                    piggyback := self._get_device_piggyback(device_status, devices_by_serial)
                ) is not None:
                    yield self._make_section(
                        name=_SEC_NAME_DEVICE_STATUSES,
                        data=device_status,
                        piggyback=piggyback or None,
                    )

        if _SEC_NAME_SENSOR_READINGS in self.config.section_names:
            for sensor_reading in self._get_sensor_readings():
                # Empty device names are possible when reading from the meraki API, let's set the
                # piggyback to None so that the output is written to the main section.
                if (
                    piggyback := self._get_device_piggyback(sensor_reading, devices_by_serial)
                ) is not None:
                    yield self._make_section(
                        name=_SEC_NAME_SENSOR_READINGS,
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
            _LOGGER.debug("Organisation ID: %r: Get license overview: %r", self.organisation_id, e)
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
                str(device[_API_NAME_DEVICE_SERIAL]): _update_device(device)
                for device in self.config.dashboard.organizations.getOrganizationDevices(
                    self.organisation_id, total_pages="all"
                )
            }
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get devices: %r", self.organisation_id, e)
            return {}

    def _get_device_statuses(self) -> Sequence[MerakiAPIData]:
        try:
            return self.config.dashboard.organizations.getOrganizationDevicesStatuses(
                self.organisation_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get device statuses: %r", self.organisation_id, e)
            return []

    def _get_sensor_readings(self) -> Sequence[MerakiAPIData]:
        try:
            return self.config.dashboard.sensor.getOrganizationSensorReadingsLatest(
                self.organisation_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get sensor readings: %r", self.organisation_id, e)
            return []

    def _get_device_piggyback(
        self, device: MerakiAPIData, devices_by_serial: Mapping[str, MerakiAPIData]
    ) -> str | None:
        try:
            serial = str(device[_API_NAME_DEVICE_SERIAL])
            return str(devices_by_serial[serial][_API_NAME_DEVICE_NAME])
        except KeyError as e:
            _LOGGER.debug("Organisation ID: %r: Get device piggyback: %r", self.organisation_id, e)
            return None

    def _make_section(
        self, *, name: str, data: MerakiAPIData, piggyback: str | None = None
    ) -> Section:
        return Section(
            api_data_source=MerakiAPIDataSource.org,
            name=_SECTION_NAME_MAP[name],
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
        with ConditionalPiggybackSection(piggyback):
            for section_name, section_data in pb_section.items():
                with SectionWriter(section_name) as writer:
                    writer.append_json(section_data)


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument("hostname")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--apikey-reference",
        help="Password store reference to the API key for the Meraki API dashboard access.",
    )
    group.add_argument(
        "--apikey",
        help="API key for the Meraki API dashboard access.",
    )

    parser.add_argument("--proxy", type=str)

    parser.add_argument(
        "--sections",
        nargs="+",
        choices=list(_SECTION_NAME_MAP),
        default=list(_SECTION_NAME_MAP),
        help="Explicit sections that are collected.",
    )

    parser.add_argument(
        "--orgs",
        nargs="+",
        default=[],
        help="Explicit organisation IDs that are checked.",
    )

    return parser.parse_args(argv)


@dataclass(frozen=True)
class MerakiConfig:
    dashboard: meraki.DashboardAPI
    hostname: str
    section_names: Sequence[str]


def _get_organisations(config: MerakiConfig, org_ids: Sequence[str]) -> Sequence[_Organisation]:
    if not _need_organisations(config.section_names):
        return []
    return (
        GetOrganisationsByIDCache(config, org_ids) if org_ids else GetOrganisationsCache(config)
    ).get_data(org_ids)


def _need_organisations(section_names: Sequence[str]) -> bool:
    return any(
        s in section_names
        for s in [
            _SEC_NAME_LICENSES_OVERVIEW,
            _SEC_NAME_DEVICE_STATUSES,
            _SEC_NAME_SENSOR_READINGS,
        ]
    )


def _need_devices(section_names: Sequence[str]) -> bool:
    return any(
        s in section_names
        for s in [
            _SEC_NAME_DEVICE_STATUSES,
            _SEC_NAME_SENSOR_READINGS,
        ]
    )


def _make_secret(args: Args) -> str:
    if args.apikey:
        return args.apikey
    pw_id, pw_file = args.apikey_reference.split(":", 1)
    return password_store.lookup(Path(pw_file), pw_id)


def agent_cisco_meraki_main(args: Args) -> int:
    config = MerakiConfig(
        dashboard=_configure_meraki_dashboard(
            _make_secret(args),
            args.debug,
            args.proxy,
        ),
        hostname=args.hostname,
        section_names=args.sections,
    )

    sections = _query_meraki_objects(
        organisations=[
            MerakiOrganisation(config, organisation)
            for organisation in _get_organisations(config, args.orgs)
        ]
    )

    _write_sections(sections)
    return 0


def main() -> int:
    return special_agent_main(
        parse_arguments, agent_cisco_meraki_main, apply_password_store_hack=False
    )
