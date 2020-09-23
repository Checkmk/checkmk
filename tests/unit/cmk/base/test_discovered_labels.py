#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping

import pytest  # type: ignore[import]

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.labels import DiscoveredHostLabelsStore

from cmk.base.discovered_labels import (
    DiscoveredHostLabelsDict,
    DiscoveredHostLabels,
    HostLabel,
    DiscoveredServiceLabels,
    ServiceLabel,
)


@pytest.fixture(name="labels", params=["host", "service"])
def labels_fixture(request):
    if request.param == "host":
        return DiscoveredHostLabels()
    return DiscoveredServiceLabels()


def test_discovered_labels_type(labels):
    assert isinstance(labels, MutableMapping)


def test_discovered_labels_is_empty(labels):
    assert labels.is_empty()
    labels["abc"] = "123"
    assert not labels.is_empty()


def test_discovered_labels_getitem(labels):
    labels["abc"] = "123"
    assert labels["abc"] == "123"


def test_discovered_labels_delitem(labels):
    labels["abc"] = "123"
    assert "abc" in labels

    del labels["abc"]
    assert "abc" not in labels


def test_discovered_labels_iter(labels):
    labels["abc"] = "123"
    labels["xyz"] = "bla"
    assert sorted(labels.keys()) == ["abc", "xyz"]


def test_discovered_labels_len(labels):
    assert len(labels) == 0

    labels["abc"] = "123"
    labels["xyz"] = "bla"

    assert len(labels) == 2


def test_discovered_labels_merge(labels):
    labels["äbc"] = "123"
    labels["xyz"] = "blä"

    merge_labels = labels.__class__()
    merge_labels["xyz"] = "blüb"

    labels.update(merge_labels)
    assert labels["äbc"] == "123"
    assert labels["xyz"] == "blüb"


def test_discovered_service_labels_to_dict():
    labels = DiscoveredServiceLabels()
    assert labels.to_dict() == {}

    labels["äbc"] = "123"
    labels["xyz"] = "blä"

    assert labels.to_dict() == {
        "äbc": "123",
        "xyz": "blä",
    }


def test_discovered_service_labels_repr():
    labels = DiscoveredServiceLabels()
    labels.add_label(ServiceLabel(u"äbc", u"123"))
    labels.add_label(ServiceLabel(u"ccc", u"ddd"))
    assert repr(
        labels) == "DiscoveredServiceLabels(ServiceLabel('ccc', 'ddd'), ServiceLabel('äbc', '123'))"


def test_discovered_host_labels_to_dict():
    labels = DiscoveredHostLabels()
    assert labels.to_dict() == {}

    labels.add_label(HostLabel(u"äbc", u"123", "plugin_1"))
    labels.add_label(HostLabel(u"xyz", u"blä", "plugin_2"))

    assert labels.to_dict() == {
        u"äbc": {
            "value": u"123",
            "plugin_name": "plugin_1",
        },
        u"xyz": {
            "value": u"blä",
            "plugin_name": "plugin_2",
        },
    }


def test_discovered_host_labels_to_list():
    labels = DiscoveredHostLabels()
    assert labels.to_list() == []

    labels.add_label(HostLabel(u"äbc", u"123", "plugin_1"))
    labels.add_label(HostLabel(u"xyz", u"blä", "plugin_2"))

    assert labels.to_list() == [
        HostLabel(u"xyz", u"blä", "plugin_2"),
        HostLabel(u"äbc", u"123", "plugin_1")
    ]


def test_discovered_host_labels_from_dict():
    label_dict: DiscoveredHostLabelsDict = {
        u"äbc": {
            "value": u"123",
            "plugin_name": "plugin_1",
        },
        u"xyz": {
            "value": u"blä",
            "plugin_name": "plugin_2",
        },
    }
    labels = DiscoveredHostLabels.from_dict(label_dict)
    assert labels.to_dict() == label_dict


def test_discovered_host_labels_add():
    labels_1 = DiscoveredHostLabels()
    labels_1.add_label(HostLabel(u"äbc", u"123", "plugin_1"))

    labels_2 = DiscoveredHostLabels()
    labels_2.add_label(HostLabel(u"xyz", u"blä", "plugin_2"))

    new_labels = labels_1 + labels_2
    assert new_labels.to_dict() == {
        u"äbc": {
            "value": u"123",
            "plugin_name": "plugin_1",
        },
        u"xyz": {
            "value": u"blä",
            "plugin_name": "plugin_2",
        },
    }

    labels_1 += labels_2
    assert labels_1.to_dict() == {
        u"äbc": {
            "value": u"123",
            "plugin_name": "plugin_1",
        },
        u"xyz": {
            "value": u"blä",
            "plugin_name": "plugin_2",
        },
    }


def test_discovered_host_labels_repr():
    labels = DiscoveredHostLabels()
    labels.add_label(HostLabel(u"äbc", u"123", "plugin_1"))
    labels.add_label(HostLabel(u"ccc", u"ddd", "plugin_2"))
    assert repr(
        labels
    ) == "DiscoveredHostLabels(HostLabel('ccc', 'ddd', plugin_name='plugin_2'), HostLabel('äbc', '123', plugin_name='plugin_1'))"


def test_discovered_host_label_equal():
    assert HostLabel(u"äbc", u"123") != HostLabel(u"xyz", u"blä")
    assert HostLabel(u"äbc", u"123") == HostLabel(u"äbc", u"123")


@pytest.fixture(name="discovered_host_labels_dir")
def discovered_host_labels_dir_fixture(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_save(discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore("host")

    labels = DiscoveredHostLabels(HostLabel(u"xyz", u"äbc"))
    label_dict = labels.to_dict()

    assert not store.file_path.exists()

    store.save(label_dict)
    assert store.file_path.exists()
    assert store.load() == label_dict


@pytest.mark.parametrize("cls", [HostLabel, ServiceLabel])
def test_label(cls):
    name, value = u"äbc", u"d{--lulu--}dd"
    l = cls(name, value)
    assert l.name == name
    assert l.value == value
    assert l.label == u"%s:%s" % (name, value)


@pytest.mark.parametrize("cls", [HostLabel, ServiceLabel])
def test_label_validation(cls):
    with pytest.raises(MKGeneralException, match="Invalid label name"):
        cls(b"\xc3\xbcbc", u"abc")

    with pytest.raises(MKGeneralException, match="Invalid label value"):
        cls(u"äbc", b"\xc3\xbcbc")
