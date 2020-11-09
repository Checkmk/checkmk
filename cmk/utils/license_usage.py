#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import List
from dataclasses import dataclass, asdict

LicenseUsageHistoryDumpVersion = "1.0"


@dataclass
class LicenseUsageSample:
    version: str
    edition: str
    platform: str
    is_cma: bool
    sample_time: int
    timezone: str
    num_hosts: int
    num_services: int


@dataclass
class LicenseUsageHistoryDump:
    VERSION: str
    history: List[LicenseUsageSample]

    def add_sample(self, sample: LicenseUsageSample) -> None:
        self.history = ([sample] + self.history)[:400]

    def serialize(self) -> bytes:
        history_dump_str = json.dumps(asdict(self))
        return rot47(history_dump_str).encode("utf-8")

    @classmethod
    def deserialize(cls, raw_history_dump: bytes) -> 'LicenseUsageHistoryDump':
        history_dump_str = rot47(raw_history_dump.decode("utf-8"))

        try:
            history_dump = json.loads(history_dump_str)
        except json.decoder.JSONDecodeError:
            history_dump = {}

        return cls(
            VERSION=history_dump.get("VERSION", LicenseUsageHistoryDumpVersion),
            history=[LicenseUsageSample(**sample) for sample in history_dump.get("history", [])],
        )


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
