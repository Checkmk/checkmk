#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence, Set
from pathlib import Path

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.inventory.paths import InventoryPaths
from cmk.update_config.internal import ConflictMode, ExpiryVersion
from cmk.update_config.plugins.pre_actions.inventory_trees import (
    _parse_transformation_durations,
    LegacyInventoryTrees,
)

_LOGGER = logging.getLogger("test")
_INVENTORY_PATHS = InventoryPaths(Path("/omd/sites/heute"))
_JSON_HEAD = b'{"'
_LEGACY_HEAD = b"{'"


class FakeListConfiguredHostNames:
    def __init__(self, host_names: Set[str]) -> None:
        self._host_names = host_names

    def __call__(self) -> Set[str]:
        return self._host_names


class FakeListFileNames:
    def __init__(self, listings: Mapping[Path, Sequence[str]]) -> None:
        self._listings = listings

    def __call__(self, directory: Path, /) -> Sequence[str]:
        return self._listings.get(directory, [])


class FakeReadHead:
    def __init__(self, heads: Mapping[Path, bytes]) -> None:
        self._heads = heads

    def __call__(self, file_path: Path, /) -> bytes:
        return self._heads.get(file_path, _JSON_HEAD)


class FakeTransformationResultsFile:
    def __init__(self, durations: Sequence[float]) -> None:
        self._durations = durations
        self.removed = False

    def load_durations(self) -> Sequence[float]:
        return self._durations

    def remove(self) -> None:
        self.removed = True


def _action(
    listings: Mapping[Path, Sequence[str]],
    heads: Mapping[Path, bytes],
    transformation_results: FakeTransformationResultsFile | None = None,
    host_names: Set[str] = frozenset({"host"}),
) -> LegacyInventoryTrees:
    return LegacyInventoryTrees(
        name="legacy_inventory_trees",
        title="Legacy inventory trees",
        sort_index=0,
        expiry_version=ExpiryVersion.CMK_310,
        inventory_paths=_INVENTORY_PATHS,
        list_host_names=FakeListConfiguredHostNames(host_names),
        list_file_names=FakeListFileNames(listings),
        read_head=FakeReadHead(heads),
        transformation_results=transformation_results or FakeTransformationResultsFile([]),
    )


def _json_site() -> Mapping[Path, Sequence[str]]:
    return {
        _INVENTORY_PATHS.inventory_dir: [".last", "host.json", "host.json.gz"],
        _INVENTORY_PATHS.status_data_dir: [".last", "host.json"],
        _INVENTORY_PATHS.archive_dir: ["host"],
        _INVENTORY_PATHS.archive_dir / "host": ["123.json"],
        _INVENTORY_PATHS.delta_cache_dir: ["host"],
        _INVENTORY_PATHS.delta_cache_dir / "host": ["None_123.json"],
    }


def test_json_trees_pass() -> None:
    _action(_json_site(), {})(_LOGGER, ConflictMode.ABORT, debug=False)


def test_json_trees_remove_the_transformation_results() -> None:
    transformation_results = FakeTransformationResultsFile([])

    _action(_json_site(), {}, transformation_results)(_LOGGER, ConflictMode.ABORT, debug=False)

    assert transformation_results.removed


def test_legacy_trees_keep_the_transformation_results() -> None:
    transformation_results = FakeTransformationResultsFile([])
    listings = {**_json_site(), _INVENTORY_PATHS.inventory_dir: ["host"]}

    _action(listings, {}, transformation_results)(_LOGGER, ConflictMode.FORCE, debug=False)

    assert not transformation_results.removed


@pytest.mark.parametrize(
    "directory, name",
    [
        pytest.param(_INVENTORY_PATHS.inventory_dir, "host", id="inventory"),
        pytest.param(_INVENTORY_PATHS.inventory_dir, "host.gz", id="inventory-gz"),
        pytest.param(_INVENTORY_PATHS.status_data_dir, "host", id="status-data"),
        pytest.param(_INVENTORY_PATHS.archive_dir / "host", "123", id="archive"),
        pytest.param(_INVENTORY_PATHS.delta_cache_dir / "host", "None_123", id="delta-cache"),
    ],
)
def test_a_legacy_file_name_aborts(directory: Path, name: str) -> None:
    listings = {**_json_site(), directory: [*_json_site()[directory], name]}
    with pytest.raises(MKUserError):
        _action(listings, {})(_LOGGER, ConflictMode.ABORT, debug=False)


@pytest.mark.parametrize(
    "directory, name",
    [
        pytest.param(_INVENTORY_PATHS.inventory_dir, ".host.json.newab12cd", id="inventory"),
        pytest.param(_INVENTORY_PATHS.status_data_dir, ".host.json.newab12cd", id="status-data"),
        pytest.param(_INVENTORY_PATHS.archive_dir / "host", ".123.json.newab12cd", id="archive"),
        pytest.param(
            _INVENTORY_PATHS.delta_cache_dir / "host", ".None_123.json.newab12cd", id="delta-cache"
        ),
    ],
)
def test_a_leftover_temporary_file_passes(directory: Path, name: str) -> None:
    listings = {**_json_site(), directory: [*_json_site()[directory], name]}
    _action(listings, {})(_LOGGER, ConflictMode.ABORT, debug=False)


@pytest.mark.parametrize(
    "file_path",
    [
        pytest.param(_INVENTORY_PATHS.inventory_dir / "host.json", id="inventory"),
        pytest.param(_INVENTORY_PATHS.inventory_dir / "host.json.gz", id="inventory-gz"),
        pytest.param(_INVENTORY_PATHS.status_data_dir / "host.json", id="status-data"),
    ],
)
def test_a_legacy_tree_of_a_host_named_like_a_json_file_aborts(file_path: Path) -> None:
    with pytest.raises(MKUserError):
        _action(_json_site(), {file_path: _LEGACY_HEAD}, host_names={"host", "host.json"})(
            _LOGGER, ConflictMode.ABORT, debug=False
        )


def test_a_tree_named_like_a_json_file_of_no_configured_host_passes() -> None:
    _action(_json_site(), {_INVENTORY_PATHS.inventory_dir / "host.json": _LEGACY_HEAD})(
        _LOGGER, ConflictMode.ABORT, debug=False
    )


def test_force_continues_despite_legacy_trees() -> None:
    listings = {**_json_site(), _INVENTORY_PATHS.inventory_dir: ["host"]}
    _action(listings, {})(_LOGGER, ConflictMode.FORCE, debug=False)


def test_the_warning_names_the_legacy_file(caplog: pytest.LogCaptureFixture) -> None:
    listings = {**_json_site(), _INVENTORY_PATHS.inventory_dir: ["host"]}
    with caplog.at_level(logging.WARNING):
        _action(listings, {})(_LOGGER, ConflictMode.FORCE, debug=False)
    assert str(_INVENTORY_PATHS.inventory_dir / "host") in caplog.text


def _twenty_legacy_archive_trees() -> Mapping[Path, Sequence[str]]:
    return {
        **_json_site(),
        _INVENTORY_PATHS.archive_dir / "host": [str(timestamp) for timestamp in range(20)],
    }


def test_the_warning_estimates_the_duration_from_the_transformation_results(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        _action(_twenty_legacy_archive_trees(), {}, FakeTransformationResultsFile([1.0, 3.0]))(
            _LOGGER, ConflictMode.FORCE, debug=False
        )
    assert "Measured on 2 converted trees, converting them takes about 40.0 s." in caplog.text


def test_the_warning_has_no_estimate_without_measured_durations(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        _action(_twenty_legacy_archive_trees(), {})(_LOGGER, ConflictMode.FORCE, debug=False)
    assert "Measured on" not in caplog.text


def test_the_warning_bounds_the_bundle_length_by_the_legacy_files(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        _action(_twenty_legacy_archive_trees(), {})(_LOGGER, ConflictMode.FORCE, debug=False)
    assert "--bundle-length 20\n" in caplog.text


def test_parse_transformation_durations_drops_the_whole_seconds_results() -> None:
    assert _parse_transformation_durations(
        [
            {"host_name": "host1", "path": "p1", "duration": 0, "size": 1},
            {"host_name": "host2", "path": "p2", "duration": 1, "size": 1},
            {"host_name": "host3", "path": "p3", "duration": 0.25, "size": 1},
            {"host_name": "host4", "path": "p4", "duration": 1.0, "size": 1},
        ]
    ) == [0.25, 1.0]
