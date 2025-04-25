#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths

from cmk.gui.watolib.host_label_sync import (
    get_host_labels_entry_of_host,
    get_updated_host_label_files,
    save_updated_host_label_files,
)


@pytest.fixture(name="discovered_host_labels_dir")
def fixture_discovered_host_labels_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_get_updated_host_label_files(discovered_host_labels_dir: Path) -> None:
    time_1 = 1616655912.123
    time_2 = 1616655912.234

    save_updated_host_label_files(
        [
            ("host1.mk", time_1, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n"),
            ("host2.mk", time_2, "{'äbc': {'value': 'xyz', 'plugin_name': 'plugin_1'}}\n"),
        ]
    )

    assert get_updated_host_label_files(newer_than=time_1 - 1) == [
        ("host1.mk", time_1, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n"),
        ("host2.mk", time_2, "{'äbc': {'value': 'xyz', 'plugin_name': 'plugin_1'}}\n"),
    ]
    assert get_updated_host_label_files(newer_than=time_1) == [
        ("host2.mk", time_2, "{'äbc': {'value': 'xyz', 'plugin_name': 'plugin_1'}}\n"),
    ]
    assert not get_updated_host_label_files(newer_than=time_2)


def test_get_host_labels_entry_of_host(discovered_host_labels_dir: Path) -> None:
    save_updated_host_label_files(
        [
            ("host1.mk", 123, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n"),
        ]
    )

    assert get_host_labels_entry_of_host(HostName("host1")) == (
        "host1.mk",
        123,
        "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n",
    )


def test_get_host_labels_entry_of_host_not_existing() -> None:
    with pytest.raises(FileNotFoundError):
        assert get_host_labels_entry_of_host(HostName("not-existing"))
