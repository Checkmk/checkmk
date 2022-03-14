#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List

from cmk.utils.license_usage.export import (
    ABCMonthlyServiceAverages,
    DailyServices,
    RawSubscriptionDetails,
)

LicenseUsageHistoryDumpVersion = "1.1"


@dataclass
class LicenseUsageExtensions:
    ntop: bool

    def serialize(self) -> bytes:
        return _serialize(self)

    @classmethod
    def deserialize(cls, raw_extensions: bytes) -> "LicenseUsageExtensions":
        extensions = _migrate_extensions(_deserialize(raw_extensions))
        return cls(**extensions)


@dataclass
class LicenseUsageSample:
    version: str
    edition: str
    platform: str
    is_cma: bool
    sample_time: int
    timezone: str
    num_hosts: int
    num_hosts_excluded: int
    num_services: int
    num_services_excluded: int
    extensions: LicenseUsageExtensions


@dataclass
class LicenseUsageHistoryDump:
    VERSION: str
    history: List[LicenseUsageSample]

    def add_sample(self, sample: LicenseUsageSample) -> None:
        self.history = ([sample] + self.history)[:400]

    def serialize(self) -> bytes:
        return _serialize(self)

    @classmethod
    def deserialize(cls, raw_history_dump: bytes) -> "LicenseUsageHistoryDump":
        history_dump = _deserialize(raw_history_dump)
        return cls(
            VERSION=LicenseUsageHistoryDumpVersion,
            history=[
                _migrate_sample(history_dump["VERSION"], s) for s in history_dump.get("history", [])
            ],
        )


def _serialize(dump: Any) -> bytes:
    dump_str = json.dumps(asdict(dump))
    return rot47(dump_str).encode("utf-8")


def _deserialize(raw_dump: bytes) -> Dict:
    dump_str = rot47(raw_dump.decode("utf-8"))

    try:
        return json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}


def _migrate_sample(prev_dump_version: str, sample: Dict) -> LicenseUsageSample:
    if prev_dump_version == "1.0":
        sample.setdefault("num_hosts_excluded", 0)
        sample.setdefault("num_services_excluded", 0)

    # Restrict platform string to 50 chars due to the restriction of the license DB field.
    sample["platform"] = sample["platform"][:50]

    migrated_extensions = _migrate_extensions(sample.get("extensions", {}))
    sample["extensions"] = LicenseUsageExtensions(**migrated_extensions)
    return LicenseUsageSample(**sample)


def _migrate_extensions(extensions: Dict) -> Dict:
    # May be missing independent of dump version:
    # It's only after execute_activate_changes created the extensions dump then it's available.
    extensions.setdefault("ntop", False)
    return extensions


def rot47(input_str: str) -> str:
    decoded_str = ""
    for char in input_str:
        ord_char = ord(char)
        if 33 <= ord_char <= 126:
            decoded_char = chr(33 + ((ord_char + 14) % 94))
        else:
            decoded_char = char
        decoded_str += decoded_char
    return decoded_str


class MonthlyServiceAveragesOfCmkUser(ABCMonthlyServiceAverages):
    def __init__(
        self,
        username: str,
        subscription_details: RawSubscriptionDetails,
        short_samples: List,
    ) -> None:
        super().__init__(username, subscription_details, short_samples)
        self._last_daily_services: Dict = {}

    @property
    def last_daily_services(self) -> Dict:
        return self._last_daily_services

    def _calculate_daily_services(self) -> DailyServices:
        daily_services: DailyServices = {}
        for site_id, history in self._short_samples:
            self._last_daily_services.setdefault(site_id, history[0] if history else None)

            for sample in history:
                sample_date = datetime.fromtimestamp(sample.sample_time)
                daily_services.setdefault(
                    datetime(sample_date.year, sample_date.month, sample_date.day),
                    Counter(),
                ).update(num_services=sample.num_services)
        return daily_services

    def get_aggregation(self) -> Dict:
        aggregation = super().get_aggregation()
        aggregation.update(
            {
                "daily_services": self.daily_services,
                "monthly_service_averages": self.monthly_service_averages,
            }
        )
        return aggregation
