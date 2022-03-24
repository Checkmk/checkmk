#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cmk.utils.license_usage.export import deserialize_dump, LicenseUsageSample, serialize_dump

LicenseUsageHistoryDumpVersion = "1.3"


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
