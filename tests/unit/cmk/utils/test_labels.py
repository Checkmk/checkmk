#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.labels import ABCLabelConfig, DiscoveredHostLabelsStore, LabelManager


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


class _LabelConfig(ABCLabelConfig):
    def __init__(
        self,
        *,
        host_labels: Mapping[str, str] | None = None,
        service_labels: Mapping[str, str] | None = None,
    ) -> None:
        self._host_labels = host_labels or {}
        self._service_labels = service_labels or {}

    def host_labels(self, *args: object) -> Mapping[str, str]:
        return self._host_labels

    def service_labels(self, *args: object) -> Mapping[str, str]:
        return self._service_labels


class _LabelManagerWithMockedDiscoerdLabels(LabelManager):
    def _discovered_labels_of_host(self, hostname):
        return {
            "prio-1": "discovered-value",
            "prio-2": "discovered-value",
            "prio-3": "discovered-value",
            "prio-4": "discovered-value",
        }


class TestLabelManager:
    def test_host_label_merge_prio(self) -> None:
        label_manager = _LabelManagerWithMockedDiscoerdLabels(
            label_config=_LabelConfig(
                host_labels={
                    "prio-1": "ruleset-value",
                    "prio-2": "ruleset-value",
                    "prio-3": "ruleset-value",
                },
            ),
            nodes_of={},
            explicit_host_labels={
                HostName("horst"): {
                    "prio-1": "explicit-value",
                    "prio-2": "explicit-value",
                }
            },
            builtin_host_labels={
                HostName("horst"): {
                    "prio-1": "builtin-value",
                },
            },
        )

        assert label_manager.labels_of_host(HostName("horst")) == {
            "prio-1": "builtin-value",
            "prio-2": "explicit-value",
            "prio-3": "ruleset-value",
            "prio-4": "discovered-value",
        }
        # I am not sure this is right. But namespaces are disjoint, so it might not matter
        assert label_manager.label_sources_of_host(HostName("horst")) == {
            "prio-1": "discovered",
            "prio-2": "explicit",
            "prio-3": "ruleset",
            "prio-4": "discovered",
        }

    def test_labels_of_service(self) -> None:
        test_host = HostName("test-host")

        label_manager = LabelManager(
            label_config=_LabelConfig(
                service_labels={
                    "label1": "val1",
                }
            ),
            nodes_of={},
            explicit_host_labels={},
            builtin_host_labels={},
        )

        assert label_manager.labels_of_service(test_host, "CPU load", {}) == {
            "label1": "val1",
        }
        assert label_manager.label_sources_of_service(test_host, "CPU load", {}) == {
            "label1": "ruleset",
        }

    def test_labels_of_service_discovered_labels(self) -> None:
        test_host = HostName("test-host")
        xyz_host = HostName("xyz")
        discovered_labels = {
            "prio-1": "this-will-be-overwritten",
            "prio-2": "discovered-value",
        }
        label_manager = LabelManager(
            label_config=_LabelConfig(
                service_labels={
                    "prio-1": "ruleset-value",
                }
            ),
            nodes_of={},
            explicit_host_labels={},
            builtin_host_labels={},
        )

        service_description = "CPU load"

        assert label_manager.labels_of_service(xyz_host, service_description, {}) == {
            "prio-1": "ruleset-value",
        }
        assert label_manager.label_sources_of_service(xyz_host, service_description, {}) == {
            "prio-1": "ruleset",
        }

        assert label_manager.labels_of_service(
            test_host, service_description, discovered_labels
        ) == {
            "prio-1": "ruleset-value",
            "prio-2": "discovered-value",
        }
        assert label_manager.label_sources_of_service(
            test_host, service_description, discovered_labels
        ) == {
            "prio-1": "ruleset",
            "prio-2": "discovered",
        }
