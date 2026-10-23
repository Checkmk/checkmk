#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import override

import pytest

from cmk.gui.watolib.appendstore import ABCAppendStore


class AppendStoreTest(ABCAppendStore[object]):
    @staticmethod
    @override
    def _serialize(entry: object) -> object:
        return entry

    @staticmethod
    @override
    def _deserialize(raw: object) -> object:
        return raw


def test_read(tmp_path: Path) -> None:
    file = tmp_path / "test"
    store = AppendStoreTest(file)

    file.write_bytes(b'{"foo": 1}\0{"bar": 2}\0')

    assert store.read() == [{"foo": 1}, {"bar": 2}]


def test_mutable_view(tmp_path: Path) -> None:
    file = tmp_path / "test"
    store = AppendStoreTest(file)

    with store.mutable_view() as view:
        view.append({"foo": 1})
        view.append({"bar": 2})

    assert file.read_bytes() == b"{'foo': 1}\0{'bar': 2}\0"


class _BrokenEntryAppendStore(AppendStoreTest):
    @staticmethod
    @override
    def _serialize(entry: object) -> object:
        if entry == "broken":
            raise ValueError(entry)
        return entry


def test_failed_write_back_keeps_the_previous_entries(tmp_path: Path) -> None:
    file = tmp_path / "test"
    file.write_bytes(b"{'foo': 1}\0{'bar': 2}\0")
    store = _BrokenEntryAppendStore(file)

    with pytest.raises(ValueError, match="broken"), store.mutable_view() as view:
        view.insert(0, "broken")

    assert store.read() == [{"foo": 1}, {"bar": 2}]


def test_append(tmp_path: Path) -> None:
    file = tmp_path / "test"
    store = AppendStoreTest(file)

    store.append({"foo": 1})
    store.append({"bar": 2})

    file.read_bytes() == b'{"foo": 1}\0{"bar": 2}\0'
