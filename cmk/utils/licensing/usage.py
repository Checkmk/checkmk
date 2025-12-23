#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import random
import time
from collections import defaultdict, deque
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import auto, Enum
from pathlib import Path
from typing import Any, NamedTuple, Protocol
from uuid import UUID

import livestatus

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.site import omd_site
from cmk.ccc.version import Edition
from cmk.utils import paths
from cmk.utils.licensing.export import (
    LicenseUsageExtensions,
    LicenseUsageSample,
    make_parser,
    parse_protocol_version,
    RawLicenseUsageExtensions,
    RawLicenseUsageReport,
    RawLicenseUsageSample,
)
from cmk.utils.licensing.helper import (
    get_instance_id_file_path,
    hash_site_id,
    load_instance_id,
    rot47,
)
from cmk.utils.licensing.protocol_version import get_licensing_protocol_version
from cmk.utils.paths import licensing_dir, omd_root

CLOUD_SERVICE_PREFIXES = {"aws", "azure", "gcp"}


#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'

_LICENSE_LABEL_NAME = "cmk/licensing"
_LICENSE_LABEL_EXCLUDE = "excluded"
SYNTHETIC_MON_CHECK_NAME = "robotmk_test"
PATTERN_BASED_KPI_CHECK_NAME = "robotmk_pattern_based_kpi"
MARKER_BASED_KPI_CHECK_NAME = "robotmk_marker_based_kpi"


class DoCreateSample(Protocol):
    def __call__(self, now: Now, instance_id: UUID, site_hash: str) -> LicenseUsageSample: ...


@dataclass(frozen=True)
class Now:
    dt: datetime
    tz: str

    @classmethod
    def make(cls) -> Now:
        time_struct = time.localtime()
        return cls(
            dt=datetime.fromtimestamp(time.mktime(time_struct)),
            tz=time_struct.tm_zone,
        )


def try_update_license_usage(
    now: Now,
    instance_id: UUID | None,
    site_hash: str,
    do_create_sample: DoCreateSample,
) -> None:
    """Update the license usage history.

    The history has a max. length of 400 (days). This process will be skipped if another process
    already tries to update the history, ie. file_paths are locked."""
    if instance_id is None:
        raise ValueError("No such instance ID")

    report_file_path = get_license_usage_report_file_path()
    licensing_dir.mkdir(parents=True, exist_ok=True)
    next_run_file_path = get_next_run_file_path()

    with store.locked(next_run_file_path), store.locked(report_file_path):
        if now.dt.timestamp() < _get_next_run_ts(next_run_file_path):
            return

        history = LocalLicenseUsageHistory.parse(load_raw_license_usage_report(report_file_path))
        history.add_sample(do_create_sample(now, instance_id, site_hash))
        save_license_usage_report(
            report_file_path,
            RawLicenseUsageReport(
                VERSION=get_licensing_protocol_version(),
                history=history.for_report(),
            ),
        )

        store.save_text_to_file(next_run_file_path, rot47(str(_create_next_run_ts(now))))


def create_sample(now: Now, instance_id: UUID, site_hash: str) -> LicenseUsageSample:
    """Calculation of hosts and services:
    num_hosts: Hosts
        - that are not shadow hosts
        - without the "cmk/licensing:excluded" label
    num_hosts_cloud: Hosts
        - that are not shadow hosts
        - without the "cmk/licensing:excluded" label
        - that monitor AWS, Azure or GCP services
    num_hosts_shadow: Hosts
        - that are shadow hosts
    num_hosts_excluded: Hosts
        - with the "cmk/licensing:excluded" label
    num_services: Services
        - that are not shadow services
        - without the "cmk/licensing:excluded" label
    num_services_cloud: Services
        - that are not shadow services
        - without the "cmk/licensing:excluded" label
        - that belong to hosts that monitor AWS, Azure or GCP services
    num_services_shadow: Services
        - that are shadow services
    num_services_excluded: Services
        - with the "cmk/licensing:excluded" label
    num_synthetic_tests Services
        - with the check_command: robotmk_test
        - that are not shadow services
        - without the "cmk/licensing:excluded" label
    num_synthetic_tests_excluded: Services
        - with the check_command: robotmk_test
        - that are not shadow services
        - with the "cmk/licensing:excluded" label
    num_synthetic_kpis Services
        - with the check_command: robotmk_pattern_based_kpi or robotmk_marker_based_kpi
        - that are not shadow services
        - without the "cmk/licensing:excluded" label
    num_synthetic_kpis_excluded: Services
        - with the check_command: robotmk_pattern_based_kpi or robotmk_marker_based_kpi
        - that are not shadow services
        - with the "cmk/licensing:excluded" label

    Shadow objects: 0: active, 1: passive, 2: shadow
    """
    sample_time = int(
        now.dt.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ).timestamp()
    )

    hosts_counter = _get_hosts_counter()
    services_counter = _get_services_counter()
    cloud_counter = _get_cloud_counter()
    synthetic_monitoring_counter = _get_synthetic_monitoring_counter()

    general_infos = cmk_version.get_general_version_infos(omd_root)
    extensions = _load_extensions()

    return LicenseUsageSample(
        instance_id=instance_id,
        site_hash=site_hash,
        version=cmk_version.omd_version(paths.omd_root),
        edition=_cmk_edition_to_licensing_edition(general_infos["edition"]),
        platform=general_infos["os"],
        is_cma=cmk_version.is_cma(),
        num_hosts=hosts_counter.num,
        num_hosts_cloud=cloud_counter.hosts,
        num_hosts_shadow=hosts_counter.num_shadow,
        num_hosts_excluded=hosts_counter.num_excluded,
        num_services=services_counter.num,
        num_services_cloud=cloud_counter.services,
        num_services_shadow=services_counter.num_shadow,
        num_services_excluded=services_counter.num_excluded,
        num_synthetic_tests=synthetic_monitoring_counter.num_services,
        num_synthetic_tests_excluded=synthetic_monitoring_counter.num_excluded,
        num_synthetic_kpis=synthetic_monitoring_counter.num_kpis,
        num_synthetic_kpis_excluded=synthetic_monitoring_counter.num_kpis_excluded,
        sample_time=sample_time,
        timezone=now.tz,
        extension_ntop=extensions.ntop,
    )


# TODO: Keep until we have a new protocol version which knows about the new edition names
def _cmk_edition_to_licensing_edition(cmk_edition: str) -> str:
    return {
        Edition.COMMUNITY.long: "cre",
        Edition.PRO.long: "cee",
        Edition.ULTIMATE.long: "cce",
        Edition.ULTIMATEMT.long: "cme",
        Edition.CLOUD.long: "cse",
    }[cmk_edition]


def _get_from_livestatus(query: str) -> Sequence[Sequence[Any]]:
    connection = livestatus.LocalConnection()
    connection.set_timeout(5)
    return connection.query(query)


class HostsOrServicesCounter(NamedTuple):
    num: int
    num_shadow: int
    num_excluded: int

    @classmethod
    def make(cls, livestatus_response: Sequence[Sequence[Any]]) -> HostsOrServicesCounter:
        stats = livestatus_response[0]
        return cls(num=int(stats[0]), num_shadow=int(stats[1]), num_excluded=int(stats[2]))


def _get_hosts_counter() -> HostsOrServicesCounter:
    return HostsOrServicesCounter.make(
        _get_from_livestatus(
            "GET hosts\n"
            "Stats: host_check_type != 2\n"
            f"Stats: host_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'\n"
            "StatsAnd: 2\n"
            "Stats: check_type = 2\n"
            f"Stats: host_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'\n"
        )
    )


def _get_services_counter() -> HostsOrServicesCounter:
    return HostsOrServicesCounter.make(
        _get_from_livestatus(
            "GET services\n"
            "Stats: host_check_type != 2\n"
            "Stats: check_type != 2\n"
            f"Stats: host_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'\n"
            f"Stats: service_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'\n"
            "StatsAnd: 4\n"
            "Stats: host_check_type = 2\n"
            "Stats: check_type = 2\n"
            "StatsAnd: 2\n"
            f"Stats: host_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'\n"
            f"Stats: service_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'\n"
            "StatsOr: 2\n"
        )
    )


@dataclass
class HostsOrServicesCloudCounter:
    hosts: int
    services: int

    @classmethod
    def make(cls, livestatus_response: Sequence[Sequence[Any]]) -> HostsOrServicesCloudCounter:
        def _contains_cloud_service(services: Sequence[str]) -> bool:
            return any(service.startswith(tuple(CLOUD_SERVICE_PREFIXES)) for service in services)

        services_per_host = defaultdict(list)
        for result in livestatus_response:
            services_per_host[result[0]].append(result[1].removeprefix("check_mk-"))

        cloud_services = {
            host: len(services)
            for host, services in services_per_host.items()
            if _contains_cloud_service(services)
        }
        return cls(hosts=len(cloud_services), services=sum(cloud_services.values()))


def _get_cloud_counter() -> HostsOrServicesCloudCounter:
    return HostsOrServicesCloudCounter.make(
        _get_from_livestatus(
            "GET services"
            "\nColumns: host_name service_check_command"
            "\nFilter: host_check_type != 2"
            "\nFilter: check_type != 2"
            f"\nFilter: host_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'"
            f"\nFilter: service_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'"
        )
    )


class HostsOrServicesSyntheticCounter(NamedTuple):
    num_services: int
    num_excluded: int
    num_kpis: int
    num_kpis_excluded: int

    @classmethod
    def make(cls, livestatus_response: Sequence[Sequence[Any]]) -> HostsOrServicesSyntheticCounter:
        stats = livestatus_response[0]
        return cls(
            num_services=int(stats[0]),
            num_excluded=int(stats[1]),
            num_kpis=int(stats[2]),
            num_kpis_excluded=int(stats[3]),
        )


def _get_synthetic_monitoring_counter() -> HostsOrServicesSyntheticCounter:
    shadow_entity_type = "2"
    num_synthetic_tests_query = [
        f"\nStats: host_check_type != {shadow_entity_type}",
        f"\nStats: check_type != {shadow_entity_type}",
        f"\nStats: host_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        f"\nStats: service_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        f"\nStats: check_command = check_mk-{SYNTHETIC_MON_CHECK_NAME}",
        "\nStatsAnd: 5",
    ]
    num_synthetic_tests_excluded_query = [
        f"\nStats: host_check_type != {shadow_entity_type}",
        f"\nStats: check_type != {shadow_entity_type}",
        f"\nStats: host_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        f"\nStats: service_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        "\nStatsOr: 2",
        f"\nStats: check_command = check_mk-{SYNTHETIC_MON_CHECK_NAME}",
        "\nStatsAnd: 4",
    ]
    num_synthetic_kpis_query = [
        f"\nStats: host_check_type != {shadow_entity_type}",
        f"\nStats: check_type != {shadow_entity_type}",
        f"\nStats: host_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        f"\nStats: service_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        f"\nStats: check_command = check_mk-{PATTERN_BASED_KPI_CHECK_NAME}",
        f"\nStats: check_command = check_mk-{MARKER_BASED_KPI_CHECK_NAME}",
        "\nStatsOr: 2",
        "\nStatsAnd: 5",
    ]
    num_synthetic_kpis_excluded_query = [
        f"\nStats: host_check_type != {shadow_entity_type}",
        f"\nStats: check_type != {shadow_entity_type}",
        f"\nStats: host_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        f"\nStats: service_labels = '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'",
        "\nStatsOr: 2",
        f"\nStats: check_command = check_mk-{PATTERN_BASED_KPI_CHECK_NAME}",
        f"\nStats: check_command = check_mk-{MARKER_BASED_KPI_CHECK_NAME}",
        "\nStatsOr: 2",
        "\nStatsAnd: 4",
    ]
    livestatus_query = (
        "GET services"
        + "".join(num_synthetic_tests_query)
        + "".join(num_synthetic_tests_excluded_query)
        + "".join(num_synthetic_kpis_query)
        + "".join(num_synthetic_kpis_excluded_query)
    )

    return HostsOrServicesSyntheticCounter.make(_get_from_livestatus(livestatus_query))


def _get_next_run_ts(file_path: Path) -> int:
    return int(rot47(store.load_text_from_file(file_path, default="_")))


def _create_next_run_ts(now: Now) -> int:
    """The next run time is randomly set to the next day between 8 am and 4 pm."""
    eight_am_tdy = datetime(now.dt.year, now.dt.month, now.dt.day, 8, 0, 0)
    start = eight_am_tdy + timedelta(days=1)
    end = start + timedelta(hours=8)
    return random.randrange(int(start.timestamp()), int(end.timestamp()), 600)


def get_license_usage_report_file_path() -> Path:
    return licensing_dir / "history.json"


def get_next_run_file_path() -> Path:
    return licensing_dir / "next_run"


def save_license_usage_report(file_path: Path, raw_report: RawLicenseUsageReport) -> None:
    store.save_bytes_to_file(file_path, _serialize_dump(raw_report))


def load_raw_license_usage_report(file_path: Path) -> object:
    return deserialize_dump(store.load_bytes_from_file(file_path, default=b"{}"))


# .
#   .--history-------------------------------------------------------------.
#   |                   _     _     _                                      |
#   |                  | |__ (_)___| |_ ___  _ __ _   _                    |
#   |                  | '_ \| / __| __/ _ \| '__| | | |                   |
#   |                  | | | | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


class LocalLicenseUsageHistory:
    def __init__(self, iterable: Iterable[LicenseUsageSample]) -> None:
        self._samples = deque(iterable, maxlen=400)

    def __iter__(self) -> Iterator[LicenseUsageSample]:
        return iter(self._samples)

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def last(self) -> LicenseUsageSample | None:
        return self._samples[0] if self._samples else None

    def for_report(self) -> list[RawLicenseUsageSample]:
        return [sample.for_report() for sample in self._samples]

    @classmethod
    def update(
        cls, raw_report: object, *, instance_id: UUID, site_hash: str
    ) -> LocalLicenseUsageHistory:
        if not raw_report:
            return cls([])
        parser = make_parser(parse_protocol_version(raw_report)).parse_sample
        if not isinstance(raw_report, dict):
            raise TypeError("Wrong report type: %r" % type(raw_report))
        return cls(
            parser(instance_id, site_hash, raw_sample)
            for raw_sample in raw_report.get("history", [])
        )

    @classmethod
    def parse(cls, raw_report: object) -> LocalLicenseUsageHistory:
        if not raw_report:
            return cls([])
        parser = make_parser(parse_protocol_version(raw_report)).parse_sample
        if not isinstance(raw_report, dict):
            raise TypeError("Wrong report type: %r" % type(raw_report))
        return cls(parser(None, "", raw_sample) for raw_sample in raw_report.get("history", []))

    def add_sample(self, sample: LicenseUsageSample) -> None:
        if sample.sample_time in {s.sample_time for s in self._samples}:
            return
        self._samples.appendleft(sample)


# .
#   .--extensions----------------------------------------------------------.
#   |                      _                 _                             |
#   |             _____  _| |_ ___ _ __  ___(_) ___  _ __  ___             |
#   |            / _ \ \/ / __/ _ \ '_ \/ __| |/ _ \| '_ \/ __|            |
#   |           |  __/>  <| ||  __/ | | \__ \ | (_) | | | \__ \            |
#   |            \___/_/\_\\__\___|_| |_|___/_|\___/|_| |_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _get_extensions_file_path() -> Path:
    return licensing_dir / "extensions.json"


def save_extensions(extensions: LicenseUsageExtensions) -> None:
    licensing_dir.mkdir(parents=True, exist_ok=True)
    extensions_file_path = _get_extensions_file_path()

    with store.locked(extensions_file_path):
        store.save_bytes_to_file(
            extensions_file_path,
            _serialize_dump(extensions.for_report()),
        )


def _parse_extensions(raw: object) -> LicenseUsageExtensions:
    if isinstance(raw, dict):
        return LicenseUsageExtensions(ntop=raw.get("ntop", False))
    raise TypeError("Wrong extensions type: %r" % type(raw))


def _load_extensions() -> LicenseUsageExtensions:
    extensions_file_path = _get_extensions_file_path()
    with store.locked(extensions_file_path):
        raw_extensions = deserialize_dump(
            store.load_bytes_from_file(
                extensions_file_path,
                default=b"{}",
            )
        )
    return _parse_extensions(raw_extensions)


# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _serialize_dump(dump: RawLicenseUsageReport | RawLicenseUsageExtensions) -> bytes:
    return rot47(json.dumps(dump)).encode("utf-8")


def deserialize_dump(raw_dump: bytes) -> object:
    dump_str = rot47(raw_dump.decode("utf-8"))

    try:
        dump = json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}

    if isinstance(dump, dict):
        return dump

    return {}


class LicenseUsageReportValidity(Enum):
    older_than_five_days = auto()
    older_than_three_days = auto()
    recent_enough = auto()


def get_license_usage_report_validity() -> LicenseUsageReportValidity:
    report_file_path = get_license_usage_report_file_path()

    with store.locked(report_file_path):
        # TODO use len(history)
        if report_file_path.stat().st_size == 0:
            try_update_license_usage(
                Now.make(),
                load_instance_id(get_instance_id_file_path(omd_root)),
                hash_site_id(omd_site()),
                create_sample,
            )
            return LicenseUsageReportValidity.recent_enough

        # TODO use max. sample time
        age = time.time() - report_file_path.stat().st_mtime
        if age >= 432000:
            # crit if greater than five days: block activate changes
            return LicenseUsageReportValidity.older_than_five_days

        if age >= 259200:
            # warn if greater than three days: warn during activating changes
            return LicenseUsageReportValidity.older_than_three_days

    return LicenseUsageReportValidity.recent_enough
