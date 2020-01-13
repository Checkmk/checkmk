# encoding: utf-8
# pylint: disable=redefined-outer-name

import pytest  # type: ignore
import cmk.utils.paths
from cmk.utils.labels import DiscoveredHostLabelsStore

# Manager is currently not tested explicitly. Indirect tests can be found
# at tests/unit/cmk/base/test_config.py::test_host_config_labels*


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
