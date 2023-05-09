#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.utils.paths
from cmk.utils.labels import (DiscoveredHostLabelsStore, get_updated_host_label_files,
                              save_updated_host_label_files, get_host_labels_entry_of_host)

# Manager is currently not tested explicitly. Indirect tests can be found
# at tests/unit/cmk/base/test_config.py::test_host_config_labels*


@pytest.fixture(name="discovered_host_labels_dir")
def fixture_discovered_host_labels_dir(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_file_path(discovered_host_labels_dir):
    assert DiscoveredHostLabelsStore("host").file_path == discovered_host_labels_dir / "host.mk"


def test_discovered_host_labels_store_load_default(discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore("host")
    assert not store.file_path.exists()
    assert store.load() == {}


def test_get_updated_host_label_files(discovered_host_labels_dir):
    time_1 = 1616655912.123
    time_2 = 1616655912.234

    save_updated_host_label_files([
        ('host1.mk', time_1, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n"),
        ('host2.mk', time_2, "{'äbc': {'value': 'xyz', 'plugin_name': 'plugin_1'}}\n"),
    ])

    assert get_updated_host_label_files(newer_than=time_1 - 1) == [
        ('host1.mk', time_1, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n"),
        ('host2.mk', time_2, "{'äbc': {'value': 'xyz', 'plugin_name': 'plugin_1'}}\n"),
    ]
    assert get_updated_host_label_files(newer_than=time_1) == [
        ('host2.mk', time_2, "{'äbc': {'value': 'xyz', 'plugin_name': 'plugin_1'}}\n"),
    ]
    assert get_updated_host_label_files(newer_than=time_2) == []


def test_get_host_labels_entry_of_host(discovered_host_labels_dir):
    save_updated_host_label_files([
        ('host1.mk', 123, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n"),
    ])

    assert get_host_labels_entry_of_host("host1") == (
        'host1.mk', 123, "{'äbc': {'value': '123', 'plugin_name': 'plugin_1'}}\n")


def test_get_host_labels_entry_of_host_not_existing():
    with pytest.raises(FileNotFoundError):
        assert get_host_labels_entry_of_host("not-existing")
