#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Callable, Mapping, Sequence
from operator import attrgetter
from pathlib import Path
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.cleanup import filter_inventory_cleanup_parameters, InventoryCleanup, matches
from cmk.inventory.config import (
    InvCleanupParams,
    InvCleanupParamsChoice,
    InvCleanupParamsCombined,
    InvCleanupParamsDefaultCombined,
    InvCleanupParamsOfHosts,
)
from cmk.inventory.paths import InventoryPaths, TreePath, TreePathGz

from ._logger import null_logger


def test_matches_the_host_name() -> None:
    assert matches(regex_or_name="hostname", host_name=HostName("hostname"))


def test_does_not_match_another_host_name() -> None:
    assert not matches(regex_or_name="hostname", host_name=HostName("other-hostname"))


def test_matches_a_regex() -> None:
    assert matches(regex_or_name="~host.*", host_name=HostName("hostname"))


def test_matches_a_regex_that_covers_the_beginning() -> None:
    assert matches(regex_or_name="~host", host_name=HostName("hostname"))


def test_does_not_match_a_regex_that_covers_the_end() -> None:
    assert not matches(regex_or_name="~name", host_name=HostName("hostname"))


def _cleanup_parameters(*regexes_or_explicits: Sequence[str]) -> InvCleanupParams:
    return InvCleanupParams(
        for_hosts=[
            InvCleanupParamsOfHosts(
                regex_or_explicit=regex_or_explicit,
                parameters=(
                    "combined",
                    InvCleanupParamsCombined(
                        strategy="and", file_age=1, number_of_history_entries=2
                    ),
                ),
            )
            for regex_or_explicit in regexes_or_explicits
        ],
        default=InvCleanupParamsDefaultCombined(
            strategy="and", file_age=123, number_of_history_entries=456
        ),
        abandoned_file_age=100,
    )


@pytest.mark.parametrize(
    "cleanup_parameters, host_names, expected",
    [
        pytest.param(_cleanup_parameters(), [], _cleanup_parameters(), id="no-hosts-at-all"),
        pytest.param(
            _cleanup_parameters(["hostname"]), [], _cleanup_parameters(), id="no-hosts-of-site"
        ),
        pytest.param(
            _cleanup_parameters(),
            [HostName("hostname")],
            _cleanup_parameters(),
            id="no-parameters-of-hosts",
        ),
        pytest.param(
            _cleanup_parameters(["hostname1"]),
            [HostName("hostname2")],
            _cleanup_parameters(),
            id="no-match",
        ),
        pytest.param(
            _cleanup_parameters(["hostname"]),
            [HostName("hostname")],
            _cleanup_parameters(["hostname"]),
            id="match",
        ),
        pytest.param(
            _cleanup_parameters(["~h", "~g", "hostname"]),
            [HostName("hostname")],
            _cleanup_parameters(["~h", "hostname"]),
            id="regex-match",
        ),
        pytest.param(
            _cleanup_parameters(["~g"]),
            [HostName("hostname")],
            _cleanup_parameters(),
            id="no-regex-match",
        ),
    ],
)
def test_filter_inventory_cleanup_parameters_keeps_the_matching_hosts(
    cleanup_parameters: InvCleanupParams,
    host_names: Sequence[HostName],
    expected: InvCleanupParams,
) -> None:
    assert (
        filter_inventory_cleanup_parameters(
            cleanup_parameters=cleanup_parameters,
            host_names=host_names,
        )
        == expected
    )


type _FileOf = Callable[[TreePath | TreePathGz], Path]


_NOW = 101


_TIMESTAMP = 100


_FILE_KINDS = pytest.mark.parametrize(
    "file_of",
    [
        pytest.param(attrgetter("path"), id="json"),
        pytest.param(attrgetter("legacy"), id="legacy"),
    ],
)


def _for_hostname(parameters: InvCleanupParamsChoice) -> InvCleanupParams:
    return InvCleanupParams(
        for_hosts=[InvCleanupParamsOfHosts(regex_or_explicit=["hostname"], parameters=parameters)],
        default=None,
        abandoned_file_age=1,
    )


def _abandoned_only(abandoned_file_age: int) -> InvCleanupParams:
    return InvCleanupParams(for_hosts=[], default=None, abandoned_file_age=abandoned_file_age)


def _combined(
    strategy: Literal["and", "or"], file_age: int, number_of_history_entries: int
) -> InvCleanupParams:
    return _for_hostname(
        (
            "combined",
            InvCleanupParamsCombined(
                strategy=strategy,
                file_age=file_age,
                number_of_history_entries=number_of_history_entries,
            ),
        )
    )


def _run(omd_root: Path, params: InvCleanupParams, *, host_names: Sequence[HostName]) -> None:
    InventoryCleanup(omd_root).run(params, host_names=host_names, now=_NOW, logger=null_logger())


def _create(file_path: Path) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch()
    return file_path


def _create_tree_files(
    omd_root: Path, host_name: HostName, file_of: _FileOf, *, mtime: int
) -> Mapping[str, Path]:
    inv_paths = InventoryPaths(omd_root)
    files = {
        "inventory": _create(file_of(inv_paths.inventory_tree(host_name))),
        "inventory gz": _create(file_of(inv_paths.inventory_tree_gz(host_name))),
        "status data": _create(file_of(inv_paths.status_data_tree(host_name))),
    }
    for file_path in files.values():
        os.utime(file_path, (mtime, mtime))
    return files


def _create_one_archive_file(omd_root: Path, file_of: _FileOf) -> Mapping[str, Path]:
    archive_tree = InventoryPaths(omd_root).archive_tree(HostName("hostname"), _TIMESTAMP - 1)
    return {
        **_create_tree_files(omd_root, HostName("hostname"), file_of, mtime=_TIMESTAMP),
        "archive 99": _create(file_of(archive_tree)),
    }


def _create_history_files(
    omd_root: Path, host_name: HostName, file_of: _FileOf
) -> Mapping[str, Path]:
    inv_paths = InventoryPaths(omd_root)
    archive_files = {
        f"archive {ts}": _create(file_of(inv_paths.archive_tree(host_name, ts)))
        for ts in range(96, 100)
    }
    delta_cache_files = {
        f"delta {ts}_{ts + 1}": _create(file_of(inv_paths.delta_cache_tree(host_name, ts, ts + 1)))
        for ts in range(95, 100)
    }
    return {
        **_create_tree_files(omd_root, host_name, file_of, mtime=_TIMESTAMP),
        **archive_files,
        **delta_cache_files,
        "archive dir": inv_paths.archive_host(host_name),
        "delta cache dir": inv_paths.delta_cache_host(host_name),
    }


def _removed(files: Mapping[str, Path]) -> Sequence[str]:
    return [label for label, file_path in files.items() if not file_path.exists()]


@pytest.mark.parametrize(
    "created",
    [
        pytest.param([], id="none"),
        pytest.param(["archive"], id="archive"),
        pytest.param(["delta cache"], id="delta-cache"),
        pytest.param(["archive", "delta cache"], id="both"),
    ],
)
def test_cleanup_leaves_the_history_directories_as_they_are(
    tmp_path: Path, created: Sequence[str]
) -> None:
    inv_paths = InventoryPaths(tmp_path)
    directories = {
        "archive": inv_paths.archive_host(HostName("hostname")),
        "delta cache": inv_paths.delta_cache_host(HostName("hostname")),
    }
    for name in created:
        directories[name].mkdir(parents=True)

    _run(tmp_path, _abandoned_only(100), host_names=[HostName("hostname")])

    assert [name for name, directory in directories.items() if directory.exists()] == created


@_FILE_KINDS
@pytest.mark.parametrize(
    "params, removed",
    [
        pytest.param(_abandoned_only(1), [], id="no-parameters"),
        pytest.param(_for_hostname(("file_age", 2)), ["archive 99"], id="file-age"),
        pytest.param(
            _for_hostname(("number_of_history_entries", 1)), [], id="number-of-history-entries"
        ),
        pytest.param(_combined("and", 2, 1), ["archive 99"], id="and"),
        pytest.param(_combined("or", 2, 1), ["archive 99"], id="or"),
    ],
)
def test_cleanup_of_a_single_archive_file(
    tmp_path: Path, file_of: _FileOf, params: InvCleanupParams, removed: Sequence[str]
) -> None:
    files = _create_one_archive_file(tmp_path, file_of)

    _run(tmp_path, params, host_names=[HostName("hostname")])

    assert _removed(files) == removed


_TOO_OLD = ["archive 96", "archive 97", "delta 95_96", "delta 96_97", "delta 97_98"]


_BEYOND_NUMBER = ["archive 96", "delta 95_96", "delta 96_97"]


@_FILE_KINDS
@pytest.mark.parametrize(
    "params, removed",
    [
        pytest.param(_for_hostname(("file_age", 3)), _TOO_OLD, id="file-age"),
        pytest.param(
            _for_hostname(("number_of_history_entries", 2)),
            _BEYOND_NUMBER,
            id="number-of-history-entries",
        ),
        pytest.param(_combined("and", 3, 2), _BEYOND_NUMBER, id="and"),
        pytest.param(_combined("or", 3, 2), _TOO_OLD, id="or"),
    ],
)
def test_cleanup_of_a_history(
    tmp_path: Path, file_of: _FileOf, params: InvCleanupParams, removed: Sequence[str]
) -> None:
    files = _create_history_files(tmp_path, HostName("hostname"), file_of)

    _run(tmp_path, params, host_names=[HostName("hostname")])

    assert _removed(files) == [*removed, "delta 99_100"]


@_FILE_KINDS
def test_cleanup_removes_an_abandoned_host_whose_youngest_file_is_too_old(
    tmp_path: Path, file_of: _FileOf
) -> None:
    known = _create_history_files(tmp_path, HostName("known"), file_of)
    unknown = _create_history_files(tmp_path, HostName("unknown"), file_of)

    _run(tmp_path, _abandoned_only(1), host_names=[HostName("known")])

    assert (_removed(known), _removed(unknown)) == ([], list(unknown))


@_FILE_KINDS
def test_cleanup_keeps_an_abandoned_host_whose_youngest_file_is_not_too_old(
    tmp_path: Path, file_of: _FileOf
) -> None:
    known = _create_history_files(tmp_path, HostName("known"), file_of)
    unknown = _create_history_files(tmp_path, HostName("unknown"), file_of)

    _run(tmp_path, _abandoned_only(2), host_names=[HostName("known")])

    assert (_removed(known), _removed(unknown)) == ([], [])


@_FILE_KINDS
@pytest.mark.parametrize(
    "mtime, removed",
    [
        pytest.param(99, ["inventory", "inventory gz", "status data"], id="too-old"),
        pytest.param(100, [], id="not-too-old"),
    ],
)
def test_cleanup_of_the_tree_files_of_an_abandoned_host_without_history(
    tmp_path: Path, file_of: _FileOf, mtime: int, removed: Sequence[str]
) -> None:
    _create_history_files(tmp_path, HostName("known"), file_of)
    _create_history_files(tmp_path, HostName("unknown"), file_of)
    files = _create_tree_files(tmp_path, HostName("unknown-no-history"), file_of, mtime=mtime)

    _run(tmp_path, _abandoned_only(2), host_names=[HostName("known")])

    assert _removed(files) == removed


def test_file_age_removes_an_archive_file_dated_at_the_epoch(tmp_path: Path) -> None:
    archive_file = _create(InventoryPaths(tmp_path).archive_tree(HostName("hostname"), 0).path)

    _run(tmp_path, _for_hostname(("file_age", 3)), host_names=[HostName("hostname")])

    assert not archive_file.exists()


def test_without_host_names_no_abandoned_file_is_removed(tmp_path: Path) -> None:
    abandoned_file = _create(tmp_path / "var/check_mk/inventory/unknown-host.json")
    os.utime(abandoned_file, (0, 0))

    _run(tmp_path, _abandoned_only(1), host_names=[])

    assert abandoned_file.exists()


@pytest.mark.parametrize(
    "file_name",
    [
        pytest.param("inventory_archive/hostname/not-a-timestamp", id="archive"),
        pytest.param("inventory_delta_cache/hostname/not-a-timestamp", id="delta-cache"),
    ],
)
def test_a_history_file_without_timestamps_is_kept(tmp_path: Path, file_name: str) -> None:
    file_path = _create(tmp_path / "var/check_mk" / file_name)

    _run(tmp_path, _for_hostname(("file_age", 1)), host_names=[HostName("hostname")])

    assert file_path.exists()
