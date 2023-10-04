#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import DiscoveredHostLabelsStore


@pytest.fixture(name="discovered_host_labels_dir")
def fixture_discovered_host_labels_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_file_path(discovered_host_labels_dir: Path) -> None:
    assert (
        DiscoveredHostLabelsStore(HostName("host")).file_path
        == discovered_host_labels_dir / "host.mk"
    )


def test_discovered_host_labels_store_load_default(discovered_host_labels_dir: Path) -> None:
    store = DiscoveredHostLabelsStore(HostName("host"))
    assert not store.file_path.exists()
    assert not store.load()
