#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

import pytest

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.type_defs import HostLabelValueDict, HostName, SectionName

import cmk.base.config as config
from cmk.base.discovered_labels import HostLabel, ServiceLabel


class TestServiceLabel:
    def test_label(self):
        assert ServiceLabel("foo", "bar").label == "foo:bar"

    def test_repr(self):
        assert repr(ServiceLabel("foo", "bar")) == "ServiceLabel('foo', 'bar')"

    def test_equality(self):
        assert ServiceLabel("a", "b") == ServiceLabel("a", "b")
        assert ServiceLabel("a", "b") != ServiceLabel("a", "c")
        assert ServiceLabel("a", "b") != ServiceLabel("c", "b")


def test_host_labels_to_dict():
    assert HostLabel("äbc", "123", SectionName("plugin_1")).to_dict() == {
        "value": "123",
        "plugin_name": "plugin_1",
    }


def test_host_labels_from_dict():
    label_dict: HostLabelValueDict = {
        "value": "123",
        "plugin_name": "plugin_1",
    }
    labels = HostLabel.from_dict("äbc", label_dict)
    assert labels.to_dict() == label_dict


def test_discovered_host_label_equal():
    sname = SectionName("sectionname")
    assert HostLabel("äbc", "123", sname) != HostLabel("xyz", "blä", sname)
    assert HostLabel("äbc", "123", sname) == HostLabel("äbc", "123", sname)


@pytest.fixture(name="discovered_host_labels_dir")
def discovered_host_labels_dir_fixture(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_save(discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore(HostName("host"))

    label_dict: Dict[str, HostLabelValueDict] = {  # save below expects Dict[Any, Any] :-|
        "xyz": {"value": "äbc", "plugin_name": "sectionname"}
    }

    assert not store.file_path.exists()

    store.save(label_dict)
    assert store.file_path.exists()
    assert store.load() == label_dict


@pytest.mark.parametrize("cls", [HostLabel, ServiceLabel])
def test_label(cls):
    name, value = "äbc", "d{--lulu--}dd"
    l = cls(name, value)
    assert l.name == name
    assert l.value == value
    assert l.label == "%s:%s" % (name, value)


@pytest.mark.parametrize("cls", [HostLabel, ServiceLabel])
def test_label_validation(cls):
    with pytest.raises(MKGeneralException, match="Invalid label name"):
        cls(b"\xc3\xbcbc", "abc")

    with pytest.raises(MKGeneralException, match="Invalid label value"):
        cls("äbc", b"\xc3\xbcbc")


def test_discovered_host_labels_path(discovered_host_labels_dir):
    hostname = "test.host.de"
    config.get_config_cache().initialize()
    assert not (discovered_host_labels_dir / hostname).exists()
    DiscoveredHostLabelsStore(HostName(hostname)).save({"something": {}})
    assert (discovered_host_labels_dir / (hostname + ".mk")).exists()
