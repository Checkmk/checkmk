#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass, field

from cmk.agent_based.v1.value_store import set_value_store_manager
from cmk.base.check_legacy_includes.wmi import wmi_yield_raw_persec
from cmk.plugins.windows.agent_based.libwmi import WMITable


@dataclass
class _ValueStoreManager:
    """Stand-in for the check engine, which owns the value store in production."""

    active_service_interface: MutableMapping[str, object] = field(default_factory=dict)

    def save(self) -> None:
        pass


@contextmanager
def _value_store() -> Iterator[None]:
    with set_value_store_manager(_ValueStoreManager(), store_changes=False):
        yield


def _table_with_zero_frequency() -> WMITable:
    # A host whose WMI provider reports a counter frequency of 0. The value
    # arrives as the string "0", which is truthy, so a plain falsiness guard
    # does not catch it.
    return WMITable(
        name="",
        headers=["Timestamp_PerfTime", "Frequency_PerfTime", "Requests", "WMIStatus"],
        key_field=None,
        timestamp=None,
        frequency=None,
        rows=[["1234567", "0", "42", "OK"]],
    )


def test_wmi_yield_raw_persec_reports_unusable_frequency() -> None:
    with _value_store():
        results = list(
            wmi_yield_raw_persec(
                _table_with_zero_frequency(), 0, "Requests", "Requests", "requests"
            )
        )
    assert results == [
        (3, "Requests: cannot compute a rate, the host reported a counter frequency of 0")
    ]
