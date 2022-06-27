#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import auto, Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, NamedTuple, Optional, Sequence, Tuple

import livestatus

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.license_usage.export import (
    LicenseUsageExtensions,
    LicenseUsageHistoryDumpVersion,
    LicenseUsageHistoryWithSiteHash,
    LicenseUsageSample,
    LicenseUsageSampleWithSiteHash,
)
from cmk.utils.paths import license_usage_dir, log_dir

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


def update_license_usage() -> int:
    """Update the license usage history

    If a sample could not be created (due to livestatus errors) then the update process will be
    skipped. This is important for checking the mtime of the history file during activate changes.

    The history has a max. length of 400 (days)."""
    logger = _init_logging()

    try:
        return _try_update_license_usage(logger)
    except Exception as e:
        logger.error("Error during license usage history update: %s", e)
        return 1


def _init_logging() -> logging.Logger:
    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")

    handler = logging.FileHandler(filename=f"{log_dir}/license-usage.log", encoding="utf-8")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)

    return logger


def _try_update_license_usage(logger: logging.Logger) -> int:
    try:
        sample = _create_sample()
    except (livestatus.MKLivestatusSocketError, livestatus.MKLivestatusNotFoundError) as e:
        logger.error("Creation of sample failed due to a livestatus error: %s", e)
        return 1

    license_usage_dir.mkdir(parents=True, exist_ok=True)
    next_run_filepath = license_usage_dir / "next_run"

    with store.locked(next_run_filepath), store.locked(_get_history_dump_filepath()):
        now = datetime.now()

        if now.timestamp() < _get_next_run_ts(next_run_filepath):
            return 0

        history_dump = _load_history_dump()
        history_dump.history.add_sample(sample)
        _save_history_dump(history_dump)

        store.save_text_to_file(next_run_filepath, _rot47(str(_create_next_run_ts(now))))

    return 0


def _create_sample() -> LicenseUsageSample:
    hosts_counter = _get_hosts_counter()
    services_counter = _get_services_counter()

    general_infos = cmk_version.get_general_version_infos()
    extensions = _load_extensions()

    return LicenseUsageSample(
        version=cmk_version.omd_version(),
        edition=general_infos["edition"],
        platform=general_infos["os"],
        is_cma=cmk_version.is_cma(),
        num_hosts=hosts_counter.included,
        num_hosts_excluded=hosts_counter.excluded,
        num_services=services_counter.included,
        num_services_excluded=services_counter.excluded,
        sample_time=int(time.time()),
        timezone=time.localtime().tm_zone,
        extension_ntop=extensions.ntop,
    )


class EntityCounter(NamedTuple):
    included: int
    excluded: int


def _get_hosts_counter() -> EntityCounter:
    included_num_hosts, excluded_num_hosts = _get_stats_from_livestatus(
        (
            "GET hosts\n"
            "Stats: host_labels != '{label_name}' '{label_value}'\n"
            "Stats: host_labels = '{label_name}' '{label_value}'\n"
        ).format(
            label_name=_LICENSE_LABEL_NAME,
            label_value=_LICENSE_LABEL_EXCLUDE,
        )
    )

    return EntityCounter(
        included=included_num_hosts,
        excluded=excluded_num_hosts,
    )


def _get_services_counter() -> EntityCounter:
    included_num_services, excluded_num_services = _get_stats_from_livestatus(
        (
            "GET services\n"
            "Stats: host_labels != '{label_name}' '{label_value}'\n"
            "Stats: service_labels != '{label_name}' '{label_value}'\n"
            "StatsAnd: 2\n"
            "Stats: host_labels = '{label_name}' '{label_value}'\n"
            "Stats: service_labels = '{label_name}' '{label_value}'\n"
            "StatsOr: 2\n"
        ).format(
            label_name=_LICENSE_LABEL_NAME,
            label_value=_LICENSE_LABEL_EXCLUDE,
        )
    )

    return EntityCounter(
        included=included_num_services,
        excluded=excluded_num_services,
    )


def _get_stats_from_livestatus(query: str) -> Tuple[int, int]:
    stats = livestatus.LocalConnection().query(query)[0]
    return int(stats[0]), int(stats[1])


def _get_next_run_ts(next_run_filepath: Path) -> int:
    return int(_rot47(store.load_text_from_file(next_run_filepath, default="_")))


def _create_next_run_ts(now: datetime) -> int:
    """The next run time is randomly set to the next day between 8 am and 4 pm."""
    eight_am_tdy = datetime(now.year, now.month, now.day, 8, 0, 0)
    start = eight_am_tdy + timedelta(days=1)
    end = start + timedelta(hours=8)
    return random.randrange(int(start.timestamp()), int(end.timestamp()), 600)


# .
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def _get_history_dump_filepath() -> Path:
    return license_usage_dir / "history.json"


@dataclass
class LicenseUsageHistoryDump:
    VERSION: str
    history: LicenseUsageHistory

    def for_report(self) -> Mapping[str, Any]:
        return {
            "VERSION": self.VERSION,
            "history": self.history.for_report(),
        }

    @classmethod
    def parse(cls, raw_dump: Mapping[str, Any]) -> LicenseUsageHistoryDump:
        if "VERSION" in raw_dump and "history" in raw_dump:
            return cls(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory.parse(raw_dump["VERSION"], raw_dump["history"]),
            )
        return cls(
            VERSION=LicenseUsageHistoryDumpVersion,
            history=LicenseUsageHistory([]),
        )


def _save_history_dump(history_dump: LicenseUsageHistoryDump) -> None:
    history_dump_filepath = _get_history_dump_filepath()
    store.save_bytes_to_file(history_dump_filepath, _serialize_dump(history_dump.for_report()))


def _load_history_dump() -> LicenseUsageHistoryDump:
    history_dump_filepath = _get_history_dump_filepath()
    raw_history_dump = deserialize_dump(
        store.load_bytes_from_file(
            history_dump_filepath,
            default=b"{}",
        )
    )
    return LicenseUsageHistoryDump.parse(raw_history_dump)


# .
#   .--history-------------------------------------------------------------.
#   |                   _     _     _                                      |
#   |                  | |__ (_)___| |_ ___  _ __ _   _                    |
#   |                  | '_ \| / __| __/ _ \| '__| | | |                   |
#   |                  | | | | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


class LicenseUsageHistory:
    def __init__(self, iterable: Iterable[LicenseUsageSample]) -> None:
        self._samples = deque(iterable, maxlen=400)

    def __iter__(self) -> Iterator[LicenseUsageSample]:
        return iter(self._samples)

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def last(self) -> Optional[LicenseUsageSample]:
        return self._samples[0] if self._samples else None

    def for_report(self) -> Sequence[Mapping[str, Any]]:
        return [sample.for_report() for sample in self]

    @classmethod
    def parse(
        cls, report_version: str, raw_history: Sequence[Mapping[str, Any]]
    ) -> LicenseUsageHistory:
        parser = LicenseUsageSample.get_parser(report_version)
        return cls(parser(raw_sample) for raw_sample in raw_history)

    def add_sample(self, sample: LicenseUsageSample) -> None:
        self._samples.appendleft(sample)

    def add_site_hash(self, raw_site_id: str) -> LicenseUsageHistoryWithSiteHash:
        site_hash = self._hash_site_id(raw_site_id)
        return LicenseUsageHistoryWithSiteHash(
            [
                LicenseUsageSampleWithSiteHash(
                    version=sample.version,
                    edition=sample.edition,
                    platform=sample.platform,
                    is_cma=sample.is_cma,
                    sample_time=sample.sample_time,
                    timezone=sample.timezone,
                    num_hosts=sample.num_hosts,
                    num_services=sample.num_services,
                    num_hosts_excluded=sample.num_hosts_excluded,
                    num_services_excluded=sample.num_services_excluded,
                    extension_ntop=sample.extension_ntop,
                    site_hash=site_hash,
                )
                for sample in self
            ]
        )

    @staticmethod
    def _hash_site_id(raw_site_id: str) -> str:
        # We have to hash the site ID because some sites contain project names.
        # This hash also has to be constant because it will be used as an DB index.
        h = hashlib.new("sha256")
        h.update(raw_site_id.encode("utf-8"))
        return h.hexdigest()


# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _get_extensions_filepath() -> Path:
    return license_usage_dir / "extensions.json"


def save_extensions(extensions: LicenseUsageExtensions) -> None:
    license_usage_dir.mkdir(parents=True, exist_ok=True)
    extensions_filepath = _get_extensions_filepath()

    with store.locked(extensions_filepath):
        store.save_bytes_to_file(extensions_filepath, _serialize_dump(extensions.for_report()))


def _load_extensions() -> LicenseUsageExtensions:
    extensions_filepath = _get_extensions_filepath()
    with store.locked(extensions_filepath):
        raw_extensions = deserialize_dump(
            store.load_bytes_from_file(
                extensions_filepath,
                default=b"{}",
            )
        )
    return LicenseUsageExtensions.parse(raw_extensions)


def _serialize_dump(dump: Mapping[str, Any]) -> bytes:
    dump_str = json.dumps(dump)
    return _rot47(dump_str).encode("utf-8")


def deserialize_dump(raw_dump: bytes) -> Mapping[str, Any]:
    dump_str = _rot47(raw_dump.decode("utf-8"))

    try:
        dump = json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}

    if isinstance(dump, dict) and all(isinstance(k, str) for k in dump):
        return dump

    return {}


def _rot47(input_str: str) -> str:
    return "".join(_rot47_char(c) for c in input_str)


def _rot47_char(c: str) -> str:
    ord_c = ord(c)
    return chr(33 + ((ord_c + 14) % 94)) if 33 <= ord_c <= 126 else c


class LicenseUsageReportValidity(Enum):
    older_than_five_days = auto()
    older_than_three_days = auto()
    recent_enough = auto()


def get_license_usage_report_validity() -> LicenseUsageReportValidity:
    history_dump_filepath = _get_history_dump_filepath()

    with store.locked(history_dump_filepath):
        if history_dump_filepath.stat().st_size == 0:
            update_license_usage()
            return LicenseUsageReportValidity.recent_enough

        age = time.time() - history_dump_filepath.stat().st_mtime
        if age >= 432000:
            # crit if greater than five days: block activate changes
            return LicenseUsageReportValidity.older_than_five_days

        if age >= 259200:
            # warn if greater than three days: warn during activating changes
            return LicenseUsageReportValidity.older_than_three_days

    return LicenseUsageReportValidity.recent_enough
