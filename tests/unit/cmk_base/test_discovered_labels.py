# encoding: utf-8
# pylint: disable=redefined-outer-name

import collections
import pytest  # type: ignore

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.labels import DiscoveredHostLabelsStore

from cmk_base.discovered_labels import (
    DiscoveredHostLabels,
    HostLabel,
    DiscoveredServiceLabels,
    ServiceLabel,
)


@pytest.fixture(params=["host", "service"])
def labels(request):
    if request.param == "host":
        return DiscoveredHostLabels()
    return DiscoveredServiceLabels()


def test_discovered_labels_type(labels):
    assert isinstance(labels, collections.MutableMapping)


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

    assert next(labels.iterkeys()) in ["abc", "xyz"]
    assert sorted(list(labels.iterkeys())) == ["abc", "xyz"]


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


def test_discovered_host_labels_from_dict():
    label_dict = {
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


@pytest.fixture()
def discovered_host_labels_dir(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_save(discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore("host")

    labels = DiscoveredHostLabels(HostLabel(u"xyz", u"äbc"))
    label_dict = labels.to_dict()

    assert not store.file_path.exists()  # pylint: disable=no-member

    store.save(label_dict)
    assert store.file_path.exists()  # pylint: disable=no-member
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
        cls("übc", u"abc")

    with pytest.raises(MKGeneralException, match="Invalid label value"):
        cls(u"äbc", "übc")
