#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import cmk.utils.store as store
from cmk.utils.license_usage.export import LicenseUsageExtensions, LicenseUsageHistory
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
