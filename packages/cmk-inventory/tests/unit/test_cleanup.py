#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.cleanup import (
    filter_inventory_cleanup_parameters,
    InvCleanupParams,
    InvCleanupParamsCombined,
    InvCleanupParamsDefaultCombined,
    InvCleanupParamsOfHosts,
    InventoryCleanup,
    matches,
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


@pytest.mark.parametrize(
    "cleanup_parameters, hosts_of_site, expected",
    [
        pytest.param(
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [],
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="no-of-hosts-and-no-hosts-of-site",
        ),
        pytest.param(
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    )
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [],
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="of-hosts-and-no-hosts-of-site",
        ),
        pytest.param(
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [HostName("hostname")],
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="no-of-hosts-and-hosts-of-site",
        ),
        pytest.param(
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname1"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    )
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [HostName("hostname2")],
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="of-hosts-and-hosts-of-site-and-no-match",
        ),
        pytest.param(
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    )
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [HostName("hostname")],
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    )
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="of-hosts-and-hosts-of-site-and-match",
        ),
        pytest.param(
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["~h", "~g", "hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    )
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [HostName("hostname")],
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["~h", "hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    )
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="regex-match",
        ),
        pytest.param(
            InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["~g"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=1,
                                number_of_history_entries=2,
                            ),
                        ),
                    ),
                ],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            [HostName("hostname")],
            InvCleanupParams(
                for_hosts=[],
                default=InvCleanupParamsDefaultCombined(
                    strategy="and",
                    file_age=123,
                    number_of_history_entries=456,
                ),
                abandoned_file_age=100,
            ),
            id="no-regex-match",
        ),
    ],
)
def test_filter_inventory_cleanup_parameters(
    cleanup_parameters: InvCleanupParams,
    hosts_of_site: Sequence[HostName],
    expected: InvCleanupParams,
) -> None:
    assert (
        filter_inventory_cleanup_parameters(
            cleanup_parameters=cleanup_parameters,
            host_names=hosts_of_site,
        )
        == expected
    )


def test_cleanup_without_history_creates_no_history_directory(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=100,
        ),
        host_names=[HostName("hostname")],
        now=100,
        logger=null_logger(),
    )
    assert (
        archive_host.exists(),
        delta_cache_host.exists(),
    ) == (False, False)


def test_cleanup_keeps_an_empty_archive_directory(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=100,
        ),
        host_names=[HostName("hostname")],
        now=100,
        logger=null_logger(),
    )
    assert (
        archive_host.exists(),
        delta_cache_host.exists(),
    ) == (True, False)


def test_cleanup_keeps_an_empty_delta_cache_directory(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=100,
        ),
        host_names=[HostName("hostname")],
        now=100,
        logger=null_logger(),
    )
    assert (
        archive_host.exists(),
        delta_cache_host.exists(),
    ) == (False, True)


def test_cleanup_keeps_both_empty_history_directories(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=100,
        ),
        host_names=[HostName("hostname")],
        now=100,
        logger=null_logger(),
    )
    assert (
        archive_host.exists(),
        delta_cache_host.exists(),
    ) == (True, True)


@dataclass(frozen=True, kw_only=True)
class _OneArchiveFile:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath
    archive_tree: TreePath


@dataclass(frozen=True, kw_only=True)
class _Files:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath
    archive_tree_1: TreePath
    archive_tree_2: TreePath
    archive_tree_3: TreePath
    archive_tree_4: TreePath
    delta_cache_tree_None_1: TreePath
    delta_cache_tree_1_2: TreePath
    delta_cache_tree_2_3: TreePath
    delta_cache_tree_3_4: TreePath
    delta_cache_tree_4_ts: TreePath


@dataclass(frozen=True, kw_only=True)
class _FilesNoHistory:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath


def _legacy_setup_one_archive_file(tmp_path: Path, *, timestamp: int) -> _OneArchiveFile:
    inv_paths = InventoryPaths(tmp_path)
    host_name = HostName("hostname")

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (timestamp, timestamp))

    archive_tree = inv_paths.archive_tree(host_name, timestamp - 1)
    archive_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    archive_tree.legacy.touch()

    return _OneArchiveFile(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
        archive_tree=archive_tree,
    )


def test_legacy_one_archive(tmp_path: Path) -> None:
    files = _legacy_setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree.legacy.exists(),
    ) == (True, True, True, True)


def test_legacy_one_archive_file_file_age(tmp_path: Path) -> None:
    files = _legacy_setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("file_age", 2),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree.legacy.exists(),
    ) == (True, True, True, False)


def test_legacy_one_archive_file_number_of_history_entries(tmp_path: Path) -> None:
    files = _legacy_setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("number_of_history_entries", 1),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree.legacy.exists(),
    ) == (True, True, True, True)


def test_legacy_one_archive_file_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _legacy_setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="and",
                            file_age=2,
                            number_of_history_entries=1,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree.legacy.exists(),
    ) == (True, True, True, False)


def test_legacy_one_archive_file_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _legacy_setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="or",
                            file_age=2,
                            number_of_history_entries=1,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree.legacy.exists(),
    ) == (True, True, True, False)


def _legacy_setup_files(tmp_path: Path, host_name: HostName, *, timestamp: int) -> _Files:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (timestamp, timestamp))

    archive_tree_1 = inv_paths.archive_tree(host_name, timestamp - 4)
    archive_tree_2 = inv_paths.archive_tree(host_name, timestamp - 3)
    archive_tree_3 = inv_paths.archive_tree(host_name, timestamp - 2)
    archive_tree_4 = inv_paths.archive_tree(host_name, timestamp - 1)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(host_name, timestamp - 5, timestamp - 4)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(host_name, timestamp - 4, timestamp - 3)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(host_name, timestamp - 3, timestamp - 2)
    delta_cache_tree_3_4 = inv_paths.delta_cache_tree(host_name, timestamp - 2, timestamp - 1)
    delta_cache_tree_4_ts = inv_paths.delta_cache_tree(host_name, timestamp - 1, timestamp)

    for file_path in [
        archive_tree_1,
        archive_tree_2,
        archive_tree_3,
        archive_tree_4,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_4,
        delta_cache_tree_4_ts,
    ]:
        file_path.legacy.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()

    return _Files(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
        archive_tree_1=archive_tree_1,
        archive_tree_2=archive_tree_2,
        archive_tree_3=archive_tree_3,
        archive_tree_4=archive_tree_4,
        delta_cache_tree_None_1=delta_cache_tree_None_1,
        delta_cache_tree_1_2=delta_cache_tree_1_2,
        delta_cache_tree_2_3=delta_cache_tree_2_3,
        delta_cache_tree_3_4=delta_cache_tree_3_4,
        delta_cache_tree_4_ts=delta_cache_tree_4_ts,
    )


def test_legacy_file_age(tmp_path: Path) -> None:
    files = _legacy_setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("file_age", 3),
                )
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree_1.legacy.exists(),
        files.archive_tree_2.legacy.exists(),
        files.archive_tree_3.legacy.exists(),
        files.archive_tree_4.legacy.exists(),
        files.delta_cache_tree_None_1.legacy.exists(),
        files.delta_cache_tree_1_2.legacy.exists(),
        files.delta_cache_tree_2_3.legacy.exists(),
        files.delta_cache_tree_3_4.legacy.exists(),
        files.delta_cache_tree_4_ts.legacy.exists(),
    ) == (True, True, True, False, False, True, True, False, False, False, True, False)


def test_legacy_number_of_history_entries(tmp_path: Path) -> None:
    files = _legacy_setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("number_of_history_entries", 2),
                )
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree_1.legacy.exists(),
        files.archive_tree_2.legacy.exists(),
        files.archive_tree_3.legacy.exists(),
        files.archive_tree_4.legacy.exists(),
        files.delta_cache_tree_None_1.legacy.exists(),
        files.delta_cache_tree_1_2.legacy.exists(),
        files.delta_cache_tree_2_3.legacy.exists(),
        files.delta_cache_tree_3_4.legacy.exists(),
        files.delta_cache_tree_4_ts.legacy.exists(),
    ) == (True, True, True, False, True, True, True, False, False, True, True, False)


def test_legacy_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _legacy_setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="and",
                            file_age=3,
                            number_of_history_entries=2,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree_1.legacy.exists(),
        files.archive_tree_2.legacy.exists(),
        files.archive_tree_3.legacy.exists(),
        files.archive_tree_4.legacy.exists(),
        files.delta_cache_tree_None_1.legacy.exists(),
        files.delta_cache_tree_1_2.legacy.exists(),
        files.delta_cache_tree_2_3.legacy.exists(),
        files.delta_cache_tree_3_4.legacy.exists(),
        files.delta_cache_tree_4_ts.legacy.exists(),
    ) == (True, True, True, False, True, True, True, False, False, True, True, False)


def test_legacy_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _legacy_setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="or",
                            file_age=3,
                            number_of_history_entries=2,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.legacy.exists(),
        files.inventory_tree_gz.legacy.exists(),
        files.status_data_tree.legacy.exists(),
        files.archive_tree_1.legacy.exists(),
        files.archive_tree_2.legacy.exists(),
        files.archive_tree_3.legacy.exists(),
        files.archive_tree_4.legacy.exists(),
        files.delta_cache_tree_None_1.legacy.exists(),
        files.delta_cache_tree_1_2.legacy.exists(),
        files.delta_cache_tree_2_3.legacy.exists(),
        files.delta_cache_tree_3_4.legacy.exists(),
        files.delta_cache_tree_4_ts.legacy.exists(),
    ) == (True, True, True, False, False, True, True, False, False, False, True, False)


def test_legacy_abandoned_file_age_youngest_too_old(tmp_path: Path) -> None:
    known_files = _legacy_setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _legacy_setup_files(tmp_path, HostName("unknown"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.legacy.exists(),
        known_files.inventory_tree_gz.legacy.exists(),
        known_files.status_data_tree.legacy.exists(),
        known_files.archive_tree_1.legacy.exists(),
        known_files.archive_tree_2.legacy.exists(),
        known_files.archive_tree_3.legacy.exists(),
        known_files.archive_tree_4.legacy.exists(),
        known_files.delta_cache_tree_None_1.legacy.exists(),
        known_files.delta_cache_tree_1_2.legacy.exists(),
        known_files.delta_cache_tree_2_3.legacy.exists(),
        known_files.delta_cache_tree_3_4.legacy.exists(),
        known_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files.inventory_tree.legacy.exists(),
        unknown_files.inventory_tree_gz.legacy.exists(),
        unknown_files.status_data_tree.legacy.exists(),
        unknown_files.archive_tree_1.legacy.exists(),
        unknown_files.archive_tree_2.legacy.exists(),
        unknown_files.archive_tree_3.legacy.exists(),
        unknown_files.archive_tree_4.legacy.exists(),
        unknown_files.archive_tree_4.legacy.parent.exists(),
        unknown_files.delta_cache_tree_None_1.legacy.exists(),
        unknown_files.delta_cache_tree_1_2.legacy.exists(),
        unknown_files.delta_cache_tree_2_3.legacy.exists(),
        unknown_files.delta_cache_tree_3_4.legacy.exists(),
        unknown_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files.delta_cache_tree_4_ts.legacy.parent.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    )


def test_legacy_abandoned_file_age_youngest_not_too_old(tmp_path: Path) -> None:
    known_files = _legacy_setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _legacy_setup_files(tmp_path, HostName("unknown"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=2,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.legacy.exists(),
        known_files.inventory_tree_gz.legacy.exists(),
        known_files.status_data_tree.legacy.exists(),
        known_files.archive_tree_1.legacy.exists(),
        known_files.archive_tree_2.legacy.exists(),
        known_files.archive_tree_3.legacy.exists(),
        known_files.archive_tree_4.legacy.exists(),
        known_files.delta_cache_tree_None_1.legacy.exists(),
        known_files.delta_cache_tree_1_2.legacy.exists(),
        known_files.delta_cache_tree_2_3.legacy.exists(),
        known_files.delta_cache_tree_3_4.legacy.exists(),
        known_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files.inventory_tree.legacy.exists(),
        unknown_files.inventory_tree_gz.legacy.exists(),
        unknown_files.status_data_tree.legacy.exists(),
        unknown_files.archive_tree_1.legacy.exists(),
        unknown_files.archive_tree_2.legacy.exists(),
        unknown_files.archive_tree_3.legacy.exists(),
        unknown_files.archive_tree_4.legacy.exists(),
        unknown_files.delta_cache_tree_None_1.legacy.exists(),
        unknown_files.delta_cache_tree_1_2.legacy.exists(),
        unknown_files.delta_cache_tree_2_3.legacy.exists(),
        unknown_files.delta_cache_tree_3_4.legacy.exists(),
        unknown_files.delta_cache_tree_4_ts.legacy.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )


def _legacy_setup_files_no_history(
    tmp_path: Path, host_name: HostName, *, timestamp: int
) -> _FilesNoHistory:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (timestamp, timestamp))

    return _FilesNoHistory(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
    )


def test_legacy_abandoned_file_age_remaining_files_too_old(tmp_path: Path) -> None:
    known_files = _legacy_setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _legacy_setup_files(tmp_path, HostName("unknown"), timestamp=100)
    unknown_files_no_history = _legacy_setup_files_no_history(
        tmp_path, HostName("unknown-no-history"), timestamp=99
    )
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=2,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.legacy.exists(),
        known_files.inventory_tree_gz.legacy.exists(),
        known_files.status_data_tree.legacy.exists(),
        known_files.archive_tree_1.legacy.exists(),
        known_files.archive_tree_2.legacy.exists(),
        known_files.archive_tree_3.legacy.exists(),
        known_files.archive_tree_4.legacy.exists(),
        known_files.delta_cache_tree_None_1.legacy.exists(),
        known_files.delta_cache_tree_1_2.legacy.exists(),
        known_files.delta_cache_tree_2_3.legacy.exists(),
        known_files.delta_cache_tree_3_4.legacy.exists(),
        known_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files.inventory_tree.legacy.exists(),
        unknown_files.inventory_tree_gz.legacy.exists(),
        unknown_files.status_data_tree.legacy.exists(),
        unknown_files.archive_tree_1.legacy.exists(),
        unknown_files.archive_tree_2.legacy.exists(),
        unknown_files.archive_tree_3.legacy.exists(),
        unknown_files.archive_tree_4.legacy.exists(),
        unknown_files.delta_cache_tree_None_1.legacy.exists(),
        unknown_files.delta_cache_tree_1_2.legacy.exists(),
        unknown_files.delta_cache_tree_2_3.legacy.exists(),
        unknown_files.delta_cache_tree_3_4.legacy.exists(),
        unknown_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files_no_history.inventory_tree.legacy.exists(),
        unknown_files_no_history.inventory_tree_gz.legacy.exists(),
        unknown_files_no_history.status_data_tree.legacy.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
    )


def test_legacy_abandoned_file_age_remaining_files_not_too_old(tmp_path: Path) -> None:
    known_files = _legacy_setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _legacy_setup_files(tmp_path, HostName("unknown"), timestamp=100)
    unknown_files_no_history = _legacy_setup_files_no_history(
        tmp_path, HostName("unknown-no-history"), timestamp=100
    )
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=2,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.legacy.exists(),
        known_files.inventory_tree_gz.legacy.exists(),
        known_files.status_data_tree.legacy.exists(),
        known_files.archive_tree_1.legacy.exists(),
        known_files.archive_tree_2.legacy.exists(),
        known_files.archive_tree_3.legacy.exists(),
        known_files.archive_tree_4.legacy.exists(),
        known_files.delta_cache_tree_None_1.legacy.exists(),
        known_files.delta_cache_tree_1_2.legacy.exists(),
        known_files.delta_cache_tree_2_3.legacy.exists(),
        known_files.delta_cache_tree_3_4.legacy.exists(),
        known_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files.inventory_tree.legacy.exists(),
        unknown_files.inventory_tree_gz.legacy.exists(),
        unknown_files.status_data_tree.legacy.exists(),
        unknown_files.archive_tree_1.legacy.exists(),
        unknown_files.archive_tree_2.legacy.exists(),
        unknown_files.archive_tree_3.legacy.exists(),
        unknown_files.archive_tree_4.legacy.exists(),
        unknown_files.delta_cache_tree_None_1.legacy.exists(),
        unknown_files.delta_cache_tree_1_2.legacy.exists(),
        unknown_files.delta_cache_tree_2_3.legacy.exists(),
        unknown_files.delta_cache_tree_3_4.legacy.exists(),
        unknown_files.delta_cache_tree_4_ts.legacy.exists(),
        unknown_files_no_history.inventory_tree.legacy.exists(),
        unknown_files_no_history.inventory_tree_gz.legacy.exists(),
        unknown_files_no_history.status_data_tree.legacy.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )


def _setup_one_archive_file(tmp_path: Path, *, timestamp: int) -> _OneArchiveFile:
    inv_paths = InventoryPaths(tmp_path)
    host_name = HostName("hostname")

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.path.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.path.touch()
    os.utime(inventory_tree.path, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.path.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.path.touch()
    os.utime(inventory_tree_gz.path, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.path.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.path.touch()
    os.utime(status_data_tree.path, (timestamp, timestamp))

    archive_tree = inv_paths.archive_tree(host_name, timestamp - 1)
    archive_tree.path.parent.mkdir(parents=True, exist_ok=True)
    archive_tree.path.touch()

    return _OneArchiveFile(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
        archive_tree=archive_tree,
    )


def test_one_archive(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree.path.exists(),
    ) == (True, True, True, True)


def test_one_archive_file_file_age(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("file_age", 2),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree.path.exists(),
    ) == (True, True, True, False)


def test_one_archive_file_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("number_of_history_entries", 1),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree.path.exists(),
    ) == (True, True, True, True)


def test_one_archive_file_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="and",
                            file_age=2,
                            number_of_history_entries=1,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree.path.exists(),
    ) == (True, True, True, False)


def test_one_archive_file_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="or",
                            file_age=2,
                            number_of_history_entries=1,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree.path.exists(),
    ) == (True, True, True, False)


def _setup_files(tmp_path: Path, host_name: HostName, *, timestamp: int) -> _Files:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.path.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.path.touch()
    os.utime(inventory_tree.path, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.path.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.path.touch()
    os.utime(inventory_tree_gz.path, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.path.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.path.touch()
    os.utime(status_data_tree.path, (timestamp, timestamp))

    archive_tree_1 = inv_paths.archive_tree(host_name, timestamp - 4)
    archive_tree_2 = inv_paths.archive_tree(host_name, timestamp - 3)
    archive_tree_3 = inv_paths.archive_tree(host_name, timestamp - 2)
    archive_tree_4 = inv_paths.archive_tree(host_name, timestamp - 1)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(host_name, timestamp - 5, timestamp - 4)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(host_name, timestamp - 4, timestamp - 3)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(host_name, timestamp - 3, timestamp - 2)
    delta_cache_tree_3_4 = inv_paths.delta_cache_tree(host_name, timestamp - 2, timestamp - 1)
    delta_cache_tree_4_ts = inv_paths.delta_cache_tree(host_name, timestamp - 1, timestamp)

    for file_path in [
        archive_tree_1,
        archive_tree_2,
        archive_tree_3,
        archive_tree_4,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_4,
        delta_cache_tree_4_ts,
    ]:
        file_path.path.parent.mkdir(parents=True, exist_ok=True)
        file_path.path.touch()

    return _Files(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
        archive_tree_1=archive_tree_1,
        archive_tree_2=archive_tree_2,
        archive_tree_3=archive_tree_3,
        archive_tree_4=archive_tree_4,
        delta_cache_tree_None_1=delta_cache_tree_None_1,
        delta_cache_tree_1_2=delta_cache_tree_1_2,
        delta_cache_tree_2_3=delta_cache_tree_2_3,
        delta_cache_tree_3_4=delta_cache_tree_3_4,
        delta_cache_tree_4_ts=delta_cache_tree_4_ts,
    )


def test_file_age(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("file_age", 3),
                )
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree_1.path.exists(),
        files.archive_tree_2.path.exists(),
        files.archive_tree_3.path.exists(),
        files.archive_tree_4.path.exists(),
        files.delta_cache_tree_None_1.path.exists(),
        files.delta_cache_tree_1_2.path.exists(),
        files.delta_cache_tree_2_3.path.exists(),
        files.delta_cache_tree_3_4.path.exists(),
        files.delta_cache_tree_4_ts.path.exists(),
    ) == (True, True, True, False, False, True, True, False, False, False, True, False)


def test_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("number_of_history_entries", 2),
                )
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree_1.path.exists(),
        files.archive_tree_2.path.exists(),
        files.archive_tree_3.path.exists(),
        files.archive_tree_4.path.exists(),
        files.delta_cache_tree_None_1.path.exists(),
        files.delta_cache_tree_1_2.path.exists(),
        files.delta_cache_tree_2_3.path.exists(),
        files.delta_cache_tree_3_4.path.exists(),
        files.delta_cache_tree_4_ts.path.exists(),
    ) == (True, True, True, False, True, True, True, False, False, True, True, False)


def test_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="and",
                            file_age=3,
                            number_of_history_entries=2,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree_1.path.exists(),
        files.archive_tree_2.path.exists(),
        files.archive_tree_3.path.exists(),
        files.archive_tree_4.path.exists(),
        files.delta_cache_tree_None_1.path.exists(),
        files.delta_cache_tree_1_2.path.exists(),
        files.delta_cache_tree_2_3.path.exists(),
        files.delta_cache_tree_3_4.path.exists(),
        files.delta_cache_tree_4_ts.path.exists(),
    ) == (True, True, True, False, True, True, True, False, False, True, True, False)


def test_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=(
                        "combined",
                        InvCleanupParamsCombined(
                            strategy="or",
                            file_age=3,
                            number_of_history_entries=2,
                        ),
                    ),
                ),
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert (
        files.inventory_tree.path.exists(),
        files.inventory_tree_gz.path.exists(),
        files.status_data_tree.path.exists(),
        files.archive_tree_1.path.exists(),
        files.archive_tree_2.path.exists(),
        files.archive_tree_3.path.exists(),
        files.archive_tree_4.path.exists(),
        files.delta_cache_tree_None_1.path.exists(),
        files.delta_cache_tree_1_2.path.exists(),
        files.delta_cache_tree_2_3.path.exists(),
        files.delta_cache_tree_3_4.path.exists(),
        files.delta_cache_tree_4_ts.path.exists(),
    ) == (True, True, True, False, False, True, True, False, False, False, True, False)


def test_abandoned_file_age_youngest_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.path.exists(),
        known_files.inventory_tree_gz.path.exists(),
        known_files.status_data_tree.path.exists(),
        known_files.archive_tree_1.path.exists(),
        known_files.archive_tree_2.path.exists(),
        known_files.archive_tree_3.path.exists(),
        known_files.archive_tree_4.path.exists(),
        known_files.delta_cache_tree_None_1.path.exists(),
        known_files.delta_cache_tree_1_2.path.exists(),
        known_files.delta_cache_tree_2_3.path.exists(),
        known_files.delta_cache_tree_3_4.path.exists(),
        known_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files.inventory_tree.path.exists(),
        unknown_files.inventory_tree_gz.path.exists(),
        unknown_files.status_data_tree.path.exists(),
        unknown_files.archive_tree_1.path.exists(),
        unknown_files.archive_tree_2.path.exists(),
        unknown_files.archive_tree_3.path.exists(),
        unknown_files.archive_tree_4.path.exists(),
        unknown_files.archive_tree_4.path.parent.exists(),
        unknown_files.delta_cache_tree_None_1.path.exists(),
        unknown_files.delta_cache_tree_1_2.path.exists(),
        unknown_files.delta_cache_tree_2_3.path.exists(),
        unknown_files.delta_cache_tree_3_4.path.exists(),
        unknown_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files.delta_cache_tree_4_ts.path.parent.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    )


def test_abandoned_file_age_youngest_not_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=2,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.path.exists(),
        known_files.inventory_tree_gz.path.exists(),
        known_files.status_data_tree.path.exists(),
        known_files.archive_tree_1.path.exists(),
        known_files.archive_tree_2.path.exists(),
        known_files.archive_tree_3.path.exists(),
        known_files.archive_tree_4.path.exists(),
        known_files.delta_cache_tree_None_1.path.exists(),
        known_files.delta_cache_tree_1_2.path.exists(),
        known_files.delta_cache_tree_2_3.path.exists(),
        known_files.delta_cache_tree_3_4.path.exists(),
        known_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files.inventory_tree.path.exists(),
        unknown_files.inventory_tree_gz.path.exists(),
        unknown_files.status_data_tree.path.exists(),
        unknown_files.archive_tree_1.path.exists(),
        unknown_files.archive_tree_2.path.exists(),
        unknown_files.archive_tree_3.path.exists(),
        unknown_files.archive_tree_4.path.exists(),
        unknown_files.delta_cache_tree_None_1.path.exists(),
        unknown_files.delta_cache_tree_1_2.path.exists(),
        unknown_files.delta_cache_tree_2_3.path.exists(),
        unknown_files.delta_cache_tree_3_4.path.exists(),
        unknown_files.delta_cache_tree_4_ts.path.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )


def _setup_files_no_history(
    tmp_path: Path, host_name: HostName, *, timestamp: int
) -> _FilesNoHistory:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.path.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.path.touch()
    os.utime(inventory_tree.path, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.path.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.path.touch()
    os.utime(inventory_tree_gz.path, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.path.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.path.touch()
    os.utime(status_data_tree.path, (timestamp, timestamp))

    return _FilesNoHistory(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
    )


def test_abandoned_file_age_remaining_files_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    unknown_files_no_history = _setup_files_no_history(
        tmp_path, HostName("unknown-no-history"), timestamp=99
    )
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=2,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.path.exists(),
        known_files.inventory_tree_gz.path.exists(),
        known_files.status_data_tree.path.exists(),
        known_files.archive_tree_1.path.exists(),
        known_files.archive_tree_2.path.exists(),
        known_files.archive_tree_3.path.exists(),
        known_files.archive_tree_4.path.exists(),
        known_files.delta_cache_tree_None_1.path.exists(),
        known_files.delta_cache_tree_1_2.path.exists(),
        known_files.delta_cache_tree_2_3.path.exists(),
        known_files.delta_cache_tree_3_4.path.exists(),
        known_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files.inventory_tree.path.exists(),
        unknown_files.inventory_tree_gz.path.exists(),
        unknown_files.status_data_tree.path.exists(),
        unknown_files.archive_tree_1.path.exists(),
        unknown_files.archive_tree_2.path.exists(),
        unknown_files.archive_tree_3.path.exists(),
        unknown_files.archive_tree_4.path.exists(),
        unknown_files.delta_cache_tree_None_1.path.exists(),
        unknown_files.delta_cache_tree_1_2.path.exists(),
        unknown_files.delta_cache_tree_2_3.path.exists(),
        unknown_files.delta_cache_tree_3_4.path.exists(),
        unknown_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files_no_history.inventory_tree.path.exists(),
        unknown_files_no_history.inventory_tree_gz.path.exists(),
        unknown_files_no_history.status_data_tree.path.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
    )


def test_abandoned_file_age_remaining_files_not_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    unknown_files_no_history = _setup_files_no_history(
        tmp_path, HostName("unknown-no-history"), timestamp=100
    )
    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=2,
        ),
        host_names=[HostName("known")],
        now=101,
        logger=null_logger(),
    )
    assert (
        known_files.inventory_tree.path.exists(),
        known_files.inventory_tree_gz.path.exists(),
        known_files.status_data_tree.path.exists(),
        known_files.archive_tree_1.path.exists(),
        known_files.archive_tree_2.path.exists(),
        known_files.archive_tree_3.path.exists(),
        known_files.archive_tree_4.path.exists(),
        known_files.delta_cache_tree_None_1.path.exists(),
        known_files.delta_cache_tree_1_2.path.exists(),
        known_files.delta_cache_tree_2_3.path.exists(),
        known_files.delta_cache_tree_3_4.path.exists(),
        known_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files.inventory_tree.path.exists(),
        unknown_files.inventory_tree_gz.path.exists(),
        unknown_files.status_data_tree.path.exists(),
        unknown_files.archive_tree_1.path.exists(),
        unknown_files.archive_tree_2.path.exists(),
        unknown_files.archive_tree_3.path.exists(),
        unknown_files.archive_tree_4.path.exists(),
        unknown_files.delta_cache_tree_None_1.path.exists(),
        unknown_files.delta_cache_tree_1_2.path.exists(),
        unknown_files.delta_cache_tree_2_3.path.exists(),
        unknown_files.delta_cache_tree_3_4.path.exists(),
        unknown_files.delta_cache_tree_4_ts.path.exists(),
        unknown_files_no_history.inventory_tree.path.exists(),
        unknown_files_no_history.inventory_tree_gz.path.exists(),
        unknown_files_no_history.status_data_tree.path.exists(),
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )


def test_file_age_removes_an_archive_file_dated_at_the_epoch(tmp_path: Path) -> None:
    archive_tree = InventoryPaths(tmp_path).archive_tree(HostName("hostname"), 0)
    archive_tree.path.parent.mkdir(parents=True, exist_ok=True)
    archive_tree.path.touch()

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(
                    regex_or_explicit=["hostname"],
                    parameters=("file_age", 3),
                )
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=101,
        logger=null_logger(),
    )
    assert not archive_tree.path.exists()


def test_without_host_names_no_abandoned_file_is_removed(tmp_path: Path) -> None:
    abandoned_file_path = tmp_path / "var/check_mk/inventory/unknown-host.json"
    abandoned_file_path.parent.mkdir(parents=True)
    abandoned_file_path.touch()
    os.utime(abandoned_file_path, (0, 0))

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(for_hosts=[], default=None, abandoned_file_age=1),
        host_names=[],
        now=100,
        logger=null_logger(),
    )

    assert abandoned_file_path.exists()


@pytest.mark.parametrize(
    "file_name",
    [
        pytest.param("inventory_archive/hostname/not-a-timestamp", id="archive"),
        pytest.param("inventory_delta_cache/hostname/not-a-timestamp", id="delta-cache"),
    ],
)
def test_a_history_file_without_timestamps_is_kept(tmp_path: Path, file_name: str) -> None:
    file_path = tmp_path / "var/check_mk" / file_name
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    InventoryCleanup(tmp_path).run(
        InvCleanupParams(
            for_hosts=[
                InvCleanupParamsOfHosts(regex_or_explicit=["hostname"], parameters=("file_age", 1))
            ],
            default=None,
            abandoned_file_age=1,
        ),
        host_names=[HostName("hostname")],
        now=100,
        logger=null_logger(),
    )

    assert file_path.exists()
