# encoding: utf-8
# pylint: disable=redefined-outer-name

import collections
import pytest  # type: ignore
import cmk.utils.paths
from cmk_base.discovered_host_labels import DiscoveredHostLabels, DiscoveredHostLabelsStore


def test_discovered_host_labels_type():
    labels = DiscoveredHostLabels()
    assert isinstance(labels, collections.MutableMapping)


def test_discovered_host_labels_is_empty():
    labels = DiscoveredHostLabels()
    assert labels.is_empty()
    labels["abc"] = "123"
    assert not labels.is_empty()


def test_discovered_host_labels_getitem():
    labels = DiscoveredHostLabels()
    labels["abc"] = "123"
    assert labels["abc"] == "123"


def test_discovered_host_labels_delitem():
    labels = DiscoveredHostLabels()

    labels["abc"] = "123"
    assert "abc" in labels

    del labels["abc"]
    assert "abc" not in labels


def test_discovered_host_labels_iter():
    labels = DiscoveredHostLabels()

    labels["abc"] = "123"
    labels["xyz"] = "bla"

    assert next(labels.iterkeys()) in ["abc", "xyz"]
    assert sorted(list(labels.iterkeys())) == ["abc", "xyz"]


def test_discovered_host_labels_len():
    labels = DiscoveredHostLabels()
    assert len(labels) == 0

    labels["abc"] = "123"
    labels["xyz"] = "bla"

    assert len(labels) == 2


def test_discovered_host_labels_to_dict():
    labels = DiscoveredHostLabels()
    assert labels.to_dict() == {}

    labels["äbc"] = "123"
    labels["xyz"] = "blä"

    assert labels.to_dict() == {
        "äbc": "123",
        "xyz": "blä",
    }


@pytest.fixture()
def discovered_labels_dir(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_file_path(discovered_labels_dir):
    assert DiscoveredHostLabelsStore("host").file_path == discovered_labels_dir / "host.mk"


def test_discovered_host_labels_store_save(discovered_labels_dir):
    store = DiscoveredHostLabelsStore("host")
    labels = DiscoveredHostLabels()
    labels["xyz"] = "äbc"
    label_dict = labels.to_dict()

    assert not store.file_path.exists()  # pylint: disable=no-member

    store.save(label_dict)
    assert store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == label_dict


def test_discovered_host_labels_store_load_default(discovered_labels_dir):
    store = DiscoveredHostLabelsStore("host")
    assert not store.file_path.exists()  # pylint: disable=no-member
    assert store.load() == {}
