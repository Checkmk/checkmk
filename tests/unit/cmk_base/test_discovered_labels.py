# encoding: utf-8
# pylint: disable=redefined-outer-name

import collections
import pytest  # type: ignore
import cmk.utils.paths
from cmk.utils.structured_data import StructuredDataTree
from cmk_base.discovered_labels import (
    DiscoveredHostLabels,
    DiscoveredHostLabelsStore,
    DiscoveredServiceLabels,
    DiscoveredServiceLabelsStore,
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


def test_discovered_host_labels_store_file_path(discovered_host_labels_dir):
    assert DiscoveredHostLabelsStore("host").file_path == discovered_host_labels_dir / "host.mk"


def test_discovered_host_labels_store_save(labels, discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore("host")
    labels["xyz"] = "äbc"
    label_dict = labels.to_dict()

    assert not store.file_path.exists()  # pylint: disable=no-member

    store.save(label_dict)
    assert store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == label_dict


def test_discovered_host_labels_store_load_default(discovered_host_labels_dir):
    store = DiscoveredHostLabelsStore("host")
    assert not store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == {}


@pytest.fixture()
def discovered_service_labels_dir(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_service_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_service_labels_dir", path)
    return path


def test_discovered_service_labels_store_file_path(discovered_service_labels_dir):
    assert DiscoveredServiceLabelsStore(
        "host", "SÄRVICE").file_path == discovered_service_labels_dir / "host" / "SÄRVICE.mk"


def test_discovered_service_labels_store_save(labels, discovered_service_labels_dir):
    store = DiscoveredServiceLabelsStore("host", "SÄRVICE")
    labels["xyz"] = "äbc"
    label_dict = labels.to_dict()

    assert not store.file_path.exists()  # pylint: disable=no-member

    store.save(label_dict)
    assert store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == label_dict


def test_discovered_service_labels_store_load_default(discovered_service_labels_dir):
    store = DiscoveredServiceLabelsStore("host", "SÄRVICE")
    assert not store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == {}
