# encoding: utf-8
# pylint: disable=redefined-outer-name

import collections
import pytest  # type: ignore

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.structured_data import StructuredDataTree
from cmk.utils.labels import DiscoveredHostLabelsStore

from cmk_base.discovered_labels import (
    DiscoveredHostLabels,
    DiscoveredServiceLabels,
    ServiceLabel,
)


@pytest.fixture(params=["host", "service"])
def labels(request):
    if request.param == "host":
        return DiscoveredHostLabels(StructuredDataTree())
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


def test_discovered_labels_to_dict(labels):
    assert labels.to_dict() == {}

    labels["äbc"] = "123"
    labels["xyz"] = "blä"

    assert labels.to_dict() == {
        "äbc": "123",
        "xyz": "blä",
    }


def test_discovered_add_label(labels):
    if isinstance(labels, DiscoveredServiceLabels):
        pytest.skip("Not implemented for service")

    labels.add_label("abc", "123", plugin_name="xyz")
    assert labels["abc"] == "123"
    inventory_labels = labels._inventory_tree.get_list(
        "software.applications.check_mk.host_labels:")
    assert inventory_labels[0] == {
        'inventory_plugin_name': 'xyz',
        'label': ('abc', '123'),
    }


@pytest.fixture()
def discovered_host_labels_dir(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_save(discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore("host")

    labels = DiscoveredHostLabels(StructuredDataTree())
    labels["xyz"] = "äbc"
    label_dict = labels.to_dict()

    assert not store.file_path.exists()  # pylint: disable=no-member

    store.save(label_dict)
    assert store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == label_dict


def test_service_label():
    name, value = u"äbc", u"d{--lulu--}dd"
    l = ServiceLabel(name, value)
    assert l.name == name
    assert l.value == value
    assert l.label == u"%s:%s" % (name, value)


def test_service_label_validation():
    with pytest.raises(MKGeneralException, match="Invalid label name"):
        ServiceLabel("übc", u"abc")

    with pytest.raises(MKGeneralException, match="Invalid label value"):
        ServiceLabel(u"äbc", "übc")
