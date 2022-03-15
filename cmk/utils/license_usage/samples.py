#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from cmk.utils.license_usage.export import (
    ABCMonthlyServiceAverages,
    DailyServices,
    deserialize_dump,
    LicenseUsageSample,
    RawSubscriptionDetails,
    serialize_dump,
)

LicenseUsageHistoryDumpVersion = "1.2"


@dataclass
class LicenseUsageHistoryDump:
    VERSION: str
    history: List[LicenseUsageSample]

    def add_sample(self, sample: LicenseUsageSample) -> None:
        self.history = ([sample] + self.history)[:400]

    def serialize(self) -> bytes:
        return serialize_dump(self)

    @classmethod
    def deserialize(cls, raw_dump: bytes) -> LicenseUsageHistoryDump:
        dump = deserialize_dump(raw_dump)
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
