#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

LicenseUsageHistoryDumpVersion = "1.1"


@dataclass
class LicenseUsageExtensions:
    ntop: bool

    def serialize(self) -> bytes:
        return _serialize(self)

    @classmethod
    def deserialize(cls, raw_extensions: bytes) -> 'LicenseUsageExtensions':
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
    def deserialize(cls, raw_history_dump: bytes) -> 'LicenseUsageHistoryDump':
        history_dump = _deserialize(raw_history_dump)
        return cls(
            VERSION=LicenseUsageHistoryDumpVersion,
            history=[
                _migrate_sample(history_dump["VERSION"], s)
                for s in history_dump.get("history", [])
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
