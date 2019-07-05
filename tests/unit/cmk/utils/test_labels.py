# encoding: utf-8
# pylint: disable=redefined-outer-name

import pytest  # type: ignore
import cmk.utils.paths
from cmk.utils.labels import (
    DiscoveredHostLabelsStore,
    DiscoveredServiceLabelsStore,
)


@pytest.fixture()
def discovered_host_labels_dir(tmp_path, monkeypatch):
    path = tmp_path / "var" / "check_mk" / "discovered_host_labels"
    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", path)
    return path


def test_discovered_host_labels_store_file_path(discovered_host_labels_dir):
    assert DiscoveredHostLabelsStore("host").file_path == discovered_host_labels_dir / "host.mk"


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
        "host").file_path == discovered_service_labels_dir / "host.mk"


def test_discovered_service_labels_store_load_default(discovered_service_labels_dir):
    store = DiscoveredServiceLabelsStore("host")
    assert not store.file_path.exists()  # pylint: disable=no-member
    assert store.load().get(u"särvice", {}) == {}
