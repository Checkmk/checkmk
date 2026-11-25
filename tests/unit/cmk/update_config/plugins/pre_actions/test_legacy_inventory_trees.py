#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.inventory.paths import Paths as InventoryPaths
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.legacy_inventory_trees import LegacyInventoryTrees
from cmk.update_config.plugins.pre_actions.utils import ConflictMode

_SITE_ROOT = Path("/site")
_INVENTORY_PATHS = InventoryPaths(_SITE_ROOT)

_LEGACY_TREES = {
    _INVENTORY_PATHS.inventory_dir: [
        "host1",
        "host2.gz",
        "host3.json",
        "host4.json.gz",
        ".last",
        ".host5.new",
    ],
    _INVENTORY_PATHS.status_data_dir: ["host1", "host3.json"],
    _INVENTORY_PATHS.archive_dir: ["host1"],
    _INVENTORY_PATHS.archive_dir / "host1": ["100", "200.json"],
    _INVENTORY_PATHS.delta_cache_dir: ["host1"],
    _INVENTORY_PATHS.delta_cache_dir / "host1": ["None_100", "100_200.json"],
}

_JSON_TREES = {
    _INVENTORY_PATHS.inventory_dir: ["host1.json", "host2.json.gz", ".last"],
    _INVENTORY_PATHS.archive_dir: ["host1"],
    _INVENTORY_PATHS.archive_dir / "host1": ["100.json"],
}


class FakeListFileNames:
    def __init__(self, file_names: Mapping[Path, Sequence[str]]) -> None:
        self._file_names = file_names

    def __call__(self, directory: Path, /) -> Sequence[str]:
        return self._file_names.get(directory, [])


def _result(duration: object) -> object:
    return {"host_name": "host", "path": "/path", "duration": duration, "size": 1}


def _run(
    caplog: pytest.LogCaptureFixture,
    file_names: Mapping[Path, Sequence[str]],
    results: object,
    from_version: str | None = None,
) -> None:
    action = LegacyInventoryTrees(
        name="legacy_inventory_trees",
        title="title",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_260,
        inventory_paths=_INVENTORY_PATHS,
        list_file_names=FakeListFileNames(file_names),
        load_transformation_results=lambda: results,
        read_from_version=lambda: from_version,
    )
    with caplog.at_level(logging.WARNING):
        action(logging.getLogger("test"), ConflictMode.ABORT)


def test_no_warning_without_legacy_trees(caplog: pytest.LogCaptureFixture) -> None:
    _run(caplog, _JSON_TREES, [_result(1.0)])
    assert not caplog.records


def test_warning_without_transformation_results(caplog: pytest.LogCaptureFixture) -> None:
    _run(caplog, _LEGACY_TREES, [])
    assert (
        "HW/SW Inventory: 5 trees still use the legacy file format.\n"
        "Checkmk 3.0 reads only trees in the new file format. Convert all trees before"
        " updating to it.\n"
        "A nightly job converts 1/200 of all trees per run.\n"
        "To convert them now, for example outside business hours, run as site user:\n"
        "  cmk-transform-inventory-trees --bundle-length 5\n"
        "To see the progress and the trees of hosts that no longer exist, run:\n"
        "  cmk-transform-inventory-trees --show-results\n"
        "Trees of hosts that no longer exist are not converted; delete the files listed there."
    ) in caplog.text


def test_warning_estimates_remaining_duration(caplog: pytest.LogCaptureFixture) -> None:
    _run(caplog, _LEGACY_TREES, [_result(0.5), _result(1.5)])
    assert (
        "HW/SW Inventory: 5 trees still use the legacy file format.\n"
        "Checkmk 3.0 reads only trees in the new file format. Convert all trees before"
        " updating to it.\n"
        "A nightly job converts 1/200 of all trees per run. Measured on 2 converted trees,"
        " converting the remaining ones takes about 5.00 s.\n"
    ) in caplog.text


def test_estimate_ignores_whole_second_durations(caplog: pytest.LogCaptureFixture) -> None:
    _run(caplog, _LEGACY_TREES, [_result(0), _result(2.0)])
    assert "Measured on 1 converted trees, converting the remaining ones takes about 10.0 s." in (
        caplog.text
    )


def test_no_estimate_from_malformed_results(caplog: pytest.LogCaptureFixture) -> None:
    _run(caplog, _LEGACY_TREES, {"duration": 1.0})
    assert "A nightly job converts 1/200 of all trees per run.\n" in caplog.text


def test_no_warning_on_update_from_before_the_transformation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run(caplog, _LEGACY_TREES, [], "2.4.0p20.community")
    assert not caplog.records


def test_warning_on_update_from_a_version_with_the_transformation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run(caplog, _LEGACY_TREES, [], "2.5.0p21.community")
    assert "HW/SW Inventory: 5 trees still use the legacy file format.\n" in caplog.text
