#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

import cmk.utils.store as store
from cmk.utils.license_usage.export import (
    LicenseUsageExtensions,
    LicenseUsageHistoryWithSiteHash,
    LicenseUsageSample,
    LicenseUsageSampleWithSiteHash,
)
from cmk.utils.paths import license_usage_dir

LicenseUsageHistoryDumpVersion = "1.3"


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


def load_extensions() -> LicenseUsageExtensions:
    extensions_filepath = _get_extensions_filepath()
    with store.locked(extensions_filepath):
        raw_extensions = deserialize_dump(
            store.load_bytes_from_file(
                extensions_filepath,
                default=b"{}",
            )
        )
    return LicenseUsageExtensions.parse(raw_extensions)


def get_history_dump_filepath() -> Path:
    return license_usage_dir / "history.json"


def save_history_dump(history_dump: LicenseUsageHistoryDump) -> None:
    history_dump_filepath = get_history_dump_filepath()
    store.save_bytes_to_file(history_dump_filepath, _serialize_dump(history_dump.for_report()))


def load_history_dump() -> LicenseUsageHistoryDump:
    history_dump_filepath = get_history_dump_filepath()
    raw_history_dump = deserialize_dump(
        store.load_bytes_from_file(
            history_dump_filepath,
            default=b"{}",
        )
    )
    return LicenseUsageHistoryDump.parse(raw_history_dump)


def _serialize_dump(dump: Mapping[str, Any]) -> bytes:
    dump_str = json.dumps(dump)
    return rot47(dump_str).encode("utf-8")


def deserialize_dump(raw_dump: bytes) -> Mapping[str, Any]:
    dump_str = rot47(raw_dump.decode("utf-8"))

    try:
        dump = json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}

    if isinstance(dump, dict) and all(isinstance(k, str) for k in dump):
        return dump

    return {}


def rot47(input_str: str) -> str:
    return "".join(_rot47(c) for c in input_str)


def _rot47(c: str) -> str:
    ord_c = ord(c)
    return chr(33 + ((ord_c + 14) % 94)) if 33 <= ord_c <= 126 else c
