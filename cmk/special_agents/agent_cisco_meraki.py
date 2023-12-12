#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import argparse
import logging
from abc import abstractmethod
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
from typing import Any, Final

import meraki  # type: ignore[import]
from typing_extensions import TypedDict

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

_DEFAULT_CACHE_INTERVAL = 86400
_MIN_CACHE_INTERVAL = 300

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


@dataclass(frozen=True)
class MerakiConfig:
    dashboard: meraki.DashboardAPI
    hostname: str
    section_names: Sequence[str]
    use_cache: bool = False


class _Organisation(TypedDict):
    # See https://developer.cisco.com/meraki/api-v1/#!get-organizations
    # if you want to extend this
    id_: str
    name: str


# .
#   .--caches--------------------------------------------------------------.
#   |                                  _                                   |
#   |                    ___ __ _  ___| |__   ___  ___                     |
#   |                   / __/ _` |/ __| '_ \ / _ \/ __|                    |
#   |                  | (_| (_| | (__| | | |  __/\__ \                    |
#   |                   \___\__,_|\___|_| |_|\___||___/                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
#
# --\ DataCache
#   |
#   |--\ MerakiSection
#      |  - adds cache_interval = _DEFAULT_CACHE_INTERVAL
#      |  - adds get_validity_from_args = True
#      |
#      |--> MerakiGetOrganizations
#      |
#      |--\ MerakiSectionOrg
#      |  |  - adds org_id parameter
#      |  |
#      |  |--> MerakiGetOrganization
#      |  |--> MerakiGetOrganizationLicensesOverview
#      |  |--> MerakiGetOrganizationDevices
#      |  |--> MerakiGetOrganizationDevicesStatuses
#      |  |--> MerakiGetOrganizationSensorReadingsLatest


class MerakiSection(DataCache):
    def __init__(
        self,
        config: MerakiConfig,
        cache_interval: int = _DEFAULT_CACHE_INTERVAL,
    ):
        self._config = config
        self._cache_dir = _BASE_CACHE_FILE_DIR / self._config.hostname
        self._cache_interval = cache_interval
        super().__init__(self._cache_dir, self.name)

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError()

    @property
    def cache_interval(self):
        return self._cache_interval

    def get_validity_from_args(self, *args: Any) -> bool:
        # always True. For now there are no changing arguments, related to the cache
        return True


class MerakiSectionOrg(MerakiSection):
    def __init__(
        self,
        config: MerakiConfig,
        org_id: str,
        cache_interval: int = _DEFAULT_CACHE_INTERVAL,
    ):
        self._org_id = org_id
        super().__init__(config=config, cache_interval=cache_interval)


class MerakiGetOrganizations(MerakiSection):
    @property
    def name(self):
        return "getOrganizations"

    def get_live_data(self, *args):
        try:
            return self._config.dashboard.organizations.getOrganizations()
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Get organisations: %r", e)
            return []


class MerakiGetOrganization(MerakiSectionOrg):
    @property
    def name(self):
        return f"getOrganization_{self._org_id}"

    def get_live_data(self, *args):
        try:
            return self._config.dashboard.organizations.getOrganization(self._org_id)
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Get organisation by id %r: %r", self._org_id, e)
            return {}


class MerakiGetOrganizationLicensesOverview(MerakiSectionOrg):
    @property
    def name(self):
        return f"getOrganizationLicensesOverview_{self._org_id}"

    def get_live_data(self, *args):
        try:
            return self._config.dashboard.organizations.getOrganizationLicensesOverview(
                self._org_id
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get license overview: %r", self._org_id, e)
            return []


class MerakiGetOrganizationDevices(MerakiSectionOrg):
    @property
    def name(self):
        return f"getOrganizationDevices_{self._org_id}"

    def get_live_data(self, *args):
        try:
            return self._config.dashboard.organizations.getOrganizationDevices(
                self._org_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get devices: %r", self._org_id, e)
            return {}


class MerakiGetOrganizationDevicesStatuses(MerakiSectionOrg):
    @property
    def name(self):
        return f"getOrganizationDevicesStatuses_{self._org_id}"

    def get_live_data(self, *args):
        try:
            return self._config.dashboard.organizations.getOrganizationDevicesStatuses(
                self._org_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get device statuses: %r", self._org_id, e)
            return []


class MerakiGetOrganizationSensorReadingsLatest(MerakiSectionOrg):
    @property
    def name(self):
        return f"getOrganizationSensorReadingsLatest_{self._org_id}"

    def get_live_data(self, *args):
        try:
            return self._config.dashboard.sensor.getOrganizationSensorReadingsLatest(
                self._org_id, total_pages="all"
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get sensor readings: %r", self._org_id, e)
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
            for device_status in MerakiGetOrganizationDevicesStatuses(
                config=self.config,
                org_id=self.organisation_id,
                cache_interval=_MIN_CACHE_INTERVAL,
            ).get_data(use_cache=self.config.use_cache):
                if piggyback := self._get_device_piggyback(device_status, devices_by_serial):
                    yield self._make_section(
                        name=_SEC_NAME_DEVICE_STATUSES,
                        data=device_status,
                        piggyback=piggyback,
                    )

        if _SEC_NAME_SENSOR_READINGS in self.config.section_names:
            for sensor_reading in MerakiGetOrganizationSensorReadingsLatest(
                config=self.config,
                org_id=self.organisation_id,
                cache_interval=_MIN_CACHE_INTERVAL,
            ).get_data(use_cache=self.config.use_cache):
                if piggyback := self._get_device_piggyback(sensor_reading, devices_by_serial):
                    yield self._make_section(
                        name=_SEC_NAME_SENSOR_READINGS,
                        data=sensor_reading,
                        piggyback=piggyback,
                    )

    def _get_licenses_overview(self) -> MerakiAPIData | None:
        def _update_licenses_overview(
            licenses_overview: dict[str, object] | None
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

        return _update_licenses_overview(
            MerakiGetOrganizationLicensesOverview(
                config=self.config, org_id=self.organisation_id
            ).get_data(use_cache=self.config.use_cache)
        )

    def _get_devices_by_serial(self) -> Mapping[str, MerakiAPIData]:
        def _update_device(device: dict[str, object]) -> MerakiAPIData:
            device.update(
                {
                    "organisation_id": self.organisation["id_"],
                    "organisation_name": self.organisation["name"],
                }
            )
            return device

        return {
            str(device[_API_NAME_DEVICE_SERIAL]): _update_device(device)
            for device in MerakiGetOrganizationDevices(
                config=self.config, org_id=self.organisation_id
            ).get_data(use_cache=self.config.use_cache)
        }

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
    parser.add_argument(
        "apikey",
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


def _get_organisations(config: MerakiConfig, org_ids: Sequence[str]) -> Sequence[_Organisation]:
    if not _need_organisations(config.section_names):
        return []
    organisations = [
        _Organisation(
            id_=organisation[_API_NAME_ORGANISATION_ID],
            name=organisation[_API_NAME_ORGANISATION_NAME],
        )
        for organisation in MerakiGetOrganizations(config=config).get_data(
            use_cache=config.use_cache
        )
    ]
    if org_ids:
        organisations = [
            organisation for organisation in organisations if organisation["id_"] in org_ids
        ]
    return organisations


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


def agent_cisco_meraki_main(args: Args) -> int:
    config = MerakiConfig(
        dashboard=_configure_meraki_dashboard(
            args.apikey,
            args.debug,
            args.proxy,
        ),
        hostname=args.hostname,
        section_names=args.sections,
    )
    sections = _query_meraki_objects(
        organisations=[
            MerakiOrganisation(config=config, organisation=organisation)
            for organisation in _get_organisations(config=config, org_ids=args.orgs)
        ]
    )

    _write_sections(sections)
    return 0


def main() -> int:
    return special_agent_main(parse_arguments, agent_cisco_meraki_main)
