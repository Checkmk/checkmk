#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

import cmk.utils.paths
from cmk.utils.type_defs import HostName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, AutochecksStore
from cmk.checkengine.discovery._autochecks import _AutochecksSerializer as AutochecksSerializer

# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
def autochecks_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))


class TestAutochecksSerializer:
    def test_empty(self) -> None:
        serial = b"[\n]\n"
        obj: list[AutocheckEntry] = []
        assert AutochecksSerializer.serialize(obj) == serial
        assert AutochecksSerializer.deserialize(serial) == obj

    def test_with_item(self) -> None:
        serial = (
            b"[\n  {'check_plugin_name': 'norris', 'item': 'abc',"
            b" 'parameters': {}, 'service_labels': {}},\n]\n"
        )
        obj = [AutocheckEntry(CheckPluginName("norris"), "abc", {}, {})]
        assert AutochecksSerializer.serialize(obj) == serial
        assert AutochecksSerializer.deserialize(serial) == obj

    def test_without_item(self) -> None:
        serial = (
            b"[\n  {'check_plugin_name': 'norris', 'item': None,"
            b" 'parameters': {}, 'service_labels': {}},\n]\n"
        )
        obj = [AutocheckEntry(CheckPluginName("norris"), None, {}, {})]
        assert AutochecksSerializer.serialize(obj) == serial
        assert AutochecksSerializer.deserialize(serial) == obj


def _entries() -> Sequence[AutocheckEntry]:
    return [AutocheckEntry(CheckPluginName("norris"), "abc", {}, {})]


class TestAutochecksStore:
    def test_clear(self) -> None:
        store = AutochecksStore(HostName("herbert"))
        store.write(_entries())
        assert store.read()
        store.clear()
        assert not store.read()

    def test_write_read(self) -> None:
        store = AutochecksStore(HostName("herbert"))
        store.write(_entries())
        assert store.read() == _entries()
