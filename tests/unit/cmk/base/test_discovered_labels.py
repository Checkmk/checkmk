#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.labels import (
    _Label,
    DiscoveredHostLabelsStore,
    HostLabel,
    HostLabelValueDict,
    ServiceLabel,
)
from cmk.utils.sectionname import SectionName


class TestServiceLabel:
    def test_label(self) -> None:
        assert ServiceLabel("foo", "bar").label == "foo:bar"

    def test_repr(self) -> None:
        assert repr(ServiceLabel("foo", "bar")) == "ServiceLabel('foo', 'bar')"

    def test_equality(self) -> None:
        assert ServiceLabel("a", "b") == ServiceLabel("a", "b")
        assert ServiceLabel("a", "b") != ServiceLabel("a", "c")
        assert ServiceLabel("a", "b") != ServiceLabel("c", "b")


def test_host_labels_to_dict() -> None:
    assert HostLabel("äbc", "123", SectionName("plugin_1")).to_dict() == {
        "value": "123",
        "plugin_name": "plugin_1",
    }


def test_discovered_host_labels_serialization() -> None:
    for hl in (
        HostLabel("äbc", "123", SectionName("sectionname")),
        HostLabel("äbc", "123", None),
    ):
        assert hl == HostLabel.deserialize(hl.serialize())


def test_host_labels_from_dict() -> None:
    label_dict: HostLabelValueDict = {
        "value": "123",
        "plugin_name": "plugin_1",
    }
    labels = HostLabel.from_dict("äbc", label_dict)
    assert labels.to_dict() == label_dict


def test_discovered_host_label_equal() -> None:
    sname = SectionName("sectionname")
    assert HostLabel("äbc", "123", sname) != HostLabel("xyz", "blä", sname)
    assert HostLabel("äbc", "123", sname) == HostLabel("äbc", "123", sname)


@pytest.fixture(name="discovered_host_labels_dir")
def discovered_host_labels_dir_fixture(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_save(discovered_host_labels_dir: Path) -> None:
    store = DiscoveredHostLabelsStore(HostName("host"))

    labels = [HostLabel("xyz", "äbc", SectionName("sectionname"))]

    assert not store.file_path.exists()

    store.save(labels)
    assert store.file_path.exists()
    assert store.load() == labels


def test_label() -> None:
    name, value = "äbc", "d{--lulu--}dd"
    l = _Label(name, value)
    assert l.name == name
    assert l.value == value
    assert l.label == f"{name}:{value}"


def test_label_validation() -> None:
    with pytest.raises(MKGeneralException, match="Invalid label name"):
        _Label(b"\xc3\xbcbc", "abc")  # type: ignore[arg-type]

    with pytest.raises(MKGeneralException, match="Invalid label value"):
        _Label("äbc", b"\xc3\xbcbc")  # type: ignore[arg-type]


def test_discovered_host_labels_path(discovered_host_labels_dir: Path) -> None:
    hostname = "test.host.de"
    assert not (discovered_host_labels_dir / hostname).exists()
    DiscoveredHostLabelsStore(HostName(hostname)).save(
        [HostLabel("something", "wonderful", SectionName("norris"))]
    )
    assert (discovered_host_labels_dir / (hostname + ".mk")).exists()
