#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping

from cmk.utils.license_usage.export import (
    ABCMonthlyServiceAverages,
    DailyServices,
    RawSubscriptionDetails,
)

LicenseUsageHistoryDumpVersion = "1.2"


@dataclass
class LicenseUsageExtensions:
    ntop: bool

    def serialize(self) -> bytes:
        return _serialize(self)

    @classmethod
    def deserialize(cls, raw_extensions: bytes) -> LicenseUsageExtensions:
        extensions = _deserialize(raw_extensions)
        return cls(ntop=extensions.get("ntop", False))

    @classmethod
    def parse(cls, raw_sample: Mapping[str, Any]) -> LicenseUsageExtensions:
        # Extensions are created after execute_activate_changes and may be missing when downloading
        # or submitting license usage reports. This means that the extensions are not really
        # dependent on the report version:
        # Old: {..., "extensions": {"ntop": True/False}, ...}
        # New: {..., "extension_ntop": True/False, ...}
        parsed_extensions = {
            ext_key: raw_sample.get(ext_key, raw_sample.get("extensions", {}).get(key, False))
            for key in ["ntop"]
            for ext_key in ("extension_%s" % key,)
        }
        return cls(ntop=parsed_extensions["extension_ntop"])


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
    extension_ntop: bool

    @classmethod
    def get_parser(cls, report_version: str) -> Callable[[Mapping[str, Any]], LicenseUsageSample]:
        if report_version == "1.0":
            parser = cls._parse_sample_v1_0

        elif report_version in ["1.1", "1.2"]:
            parser = cls._parse_sample_v1_1

        else:
            raise NotImplementedError(f"Unknown report version {report_version}")

        return lambda raw_sample: cls._parse(parser(raw_sample), raw_sample)

    @staticmethod
    def _parse_sample_v1_0(sample: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "version": sample["version"],
            "edition": sample["edition"],
            "platform": sample["platform"],
            "is_cma": sample["is_cma"],
            "sample_time": sample["sample_time"],
            "timezone": sample["timezone"],
            "num_hosts": sample["num_hosts"],
            "num_services": sample["num_services"],
            "num_hosts_excluded": 0,
            "num_services_excluded": 0,
        }

    @staticmethod
    def _parse_sample_v1_1(sample: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "version": sample["version"],
            "edition": sample["edition"],
            "platform": sample["platform"],
            "is_cma": sample["is_cma"],
            "sample_time": sample["sample_time"],
            "timezone": sample["timezone"],
            "num_hosts": sample["num_hosts"],
            "num_services": sample["num_services"],
            "num_hosts_excluded": sample["num_hosts_excluded"],
            "num_services_excluded": sample["num_services_excluded"],
        }

    @classmethod
    def _parse(
        cls, parsed_sample: Mapping[str, Any], raw_sample: Mapping[str, Any]
    ) -> LicenseUsageSample:
        extensions = LicenseUsageExtensions.parse(raw_sample)
        return cls(
            version=parsed_sample["version"],
            edition=parsed_sample["edition"],
            # Restrict platform string to 50 chars due to the restriction of the license DB field.
            platform=parsed_sample["platform"][:50],
            is_cma=parsed_sample["is_cma"],
            sample_time=parsed_sample["sample_time"],
            timezone=parsed_sample["timezone"],
            num_hosts=parsed_sample["num_hosts"],
            num_hosts_excluded=parsed_sample["num_hosts_excluded"],
            num_services=parsed_sample["num_services"],
            num_services_excluded=parsed_sample["num_services_excluded"],
            extension_ntop=extensions.ntop,
        )


@dataclass
class LicenseUsageHistoryDump:
    VERSION: str
    history: List[LicenseUsageSample]

    def add_sample(self, sample: LicenseUsageSample) -> None:
        self.history = ([sample] + self.history)[:400]

    def serialize(self) -> bytes:
        return _serialize(self)

    @classmethod
    def deserialize(cls, raw_dump: bytes) -> LicenseUsageHistoryDump:
        dump = _deserialize(raw_dump)
        if not dump:
            return cls(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[],
            )

        parser = LicenseUsageSample.get_parser(dump["VERSION"])
        return cls(
            VERSION=LicenseUsageHistoryDumpVersion,
            history=[parser(s) for s in dump.get("history", [])],
        )


def _serialize(dump: Any) -> bytes:
    dump_str = json.dumps(asdict(dump))
    return rot47(dump_str).encode("utf-8")


def _deserialize(raw_dump: bytes) -> Mapping[str, Any]:
    dump_str = rot47(raw_dump.decode("utf-8"))

    try:
        return json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}


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
