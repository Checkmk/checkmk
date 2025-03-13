#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

from cmk.gui.watolib.appendstore import ABCAppendStore


class TestAppendStore(ABCAppendStore[object]):
    @staticmethod
    def _serialize(entry: object) -> object:
        return entry

    @staticmethod
    def _deserialize(raw: object) -> object:
        return raw


def test_read(tmp_path: Path) -> None:
    file = tmp_path / "test"
    store = TestAppendStore(file)

    file.write_bytes(b'{"foo": 1}\0{"bar": 2}\0')

    assert store.read() == [{"foo": 1}, {"bar": 2}]


def test_mutable_view(tmp_path: Path) -> None:
    file = tmp_path / "test"
    store = TestAppendStore(file)

    with store.mutable_view() as view:
        view.append({"foo": 1})
        view.append({"bar": 2})

    file.read_bytes() == b'{"foo": 1}\0{"bar": 2}\0'


def test_append(tmp_path: Path) -> None:
    file = tmp_path / "test"
    store = TestAppendStore(file)

    store.append({"foo": 1})
    store.append({"bar": 2})

    file.read_bytes() == b'{"foo": 1}\0{"bar": 2}\0'
