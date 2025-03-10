#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from livestatus import SiteId

from cmk.gui.deprecations import (
    _filter_non_ok_ac_test_results,
    _find_ac_test_result_problems,
    _format_ac_test_result_problems,
    _MarkerFileStore,
)
from cmk.gui.watolib.analyze_configuration import ACResultState, ACTestResult

from cmk.mkp_tool import Manifest, PackageName, PackagePart, PackageVersion


def test__marker_file_store_save(tmp_path: Path) -> None:
    marker_file_store = _MarkerFileStore(tmp_path / "deprecations")
    marker_file_store.save(SiteId("site_id"), "2.4.0", [])
    assert marker_file_store.marker_file(SiteId("site_id"), "2.4.0").exists()


def test__marker_file_store_cleanup_site_dir(tmp_path: Path) -> None:
    marker_file_store = _MarkerFileStore(tmp_path / "deprecations")
    for idx in range(10):
        marker_file_store.save(SiteId("site_id"), str(idx), [])
    assert len(list((marker_file_store.folder / "site_id").iterdir())) == 10
    marker_file_store.cleanup_site_dir(SiteId("site_id"))
    assert len(list((marker_file_store.folder / "site_id").iterdir())) == 5


@pytest.mark.parametrize(
    "ac_test_results_by_site_id, result",
    [
        pytest.param(
            {},
            {},
            id="empty",
        ),
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.OK,
                        "text",
                        "test_id_1",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        None,
                    )
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.OK,
                        "text",
                        "test_id_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        None,
                    )
                ],
            },
            {},
            id="only-ok",
        ),
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.OK,
                        "text",
                        "test_id_1_1",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        None,
                    ),
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_1_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        None,
                    ),
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.OK,
                        "text",
                        "test_id_2_1",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        None,
                    ),
                    ACTestResult(
                        ACResultState.CRIT,
                        "text",
                        "test_id_2_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        None,
                    ),
                ],
            },
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_1_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        None,
                    ),
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.CRIT,
                        "text",
                        "test_id_2_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        None,
                    ),
                ],
            },
            id="all",
        ),
    ],
)
def test__filter_non_ok_ac_test_results(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
    result: Mapping[SiteId, Sequence[ACTestResult]],
) -> None:
    assert _filter_non_ok_ac_test_results(ac_test_results_by_site_id) == result


@pytest.mark.parametrize(
    "ac_test_results_by_site_id, manifests_by_path, result",
    [
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_1_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        None,
                    ),
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.CRIT,
                        "text",
                        "test_id_2_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        None,
                    ),
                ],
            },
            {},
            "text: sites: site_id_1, site_id_2",
            id="one-id",
        ),
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text_1",
                        "test_id_1_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        None,
                    ),
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.CRIT,
                        "text_2",
                        "test_id_2_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        None,
                    ),
                ],
            },
            {},
            "text_1: sites: site_id_1\ntext_2: sites: site_id_2",
            id="different-ids",
        ),
        pytest.param(
            {
                SiteId("site_id"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id"),
                        Path("/omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py"),
                    ),
                ],
            },
            {},
            "Unpackaged files: text (file: /omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py), sites: site_id",
            id="mkp",
        ),
        pytest.param(
            {
                SiteId("site_id"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id"),
                        Path("/omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py"),
                    ),
                ],
            },
            {
                Path("local/share/check_mk/web/plugins/metrics/file.py"): Manifest(
                    title="asd",
                    name=PackageName("asd"),
                    description="",
                    version=PackageVersion("1.0.0"),
                    version_packaged="2.4.0-2025.03.05",
                    version_min_required="2.4.0-2025.03.05",
                    version_usable_until=None,
                    author="cmkadmin",
                    download_url="",
                    files={PackagePart("web"): [Path("plugins/metrics/file.py")]},
                )
            },
            "MKP asd: text (file: /omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py), sites: site_id",
            id="mkp",
        ),
    ],
)
def test__format_ac_test_result_problems(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
    manifests_by_path: Mapping[Path, Manifest],
    result: str,
) -> None:
    assert (
        _format_ac_test_result_problems(
            _find_ac_test_result_problems(
                ac_test_results_by_site_id,
                manifests_by_path,
            )
        )
        == result
    )
