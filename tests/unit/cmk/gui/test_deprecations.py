#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.gui.deprecations import (
    _ACTestResultProblem,
    _ACTestResultProblemFile,
    _ACTestResultProblemMKP,
    _ACTestResultProblemUnsorted,
    _filter_non_ok_ac_test_results,
    _find_ac_test_result_problems,
    _find_problems_to_send,
    _MarkerFileStore,
    _NotifiableUser,
    _NotificationCategory,
    _ProblemToSend,
)
from cmk.gui.watolib.analyze_configuration import ACResultState, ACTestResult

from cmk.mkp_tool import Manifest, PackageName, PackagePart, PackageVersion


def test__marker_file_store_save(tmp_path: Path) -> None:
    marker_file_store = _MarkerFileStore(tmp_path / "deprecations")
    marker_file_store.save(SiteId("site_id"), "2.4.0", [])
    assert (tmp_path / "deprecations/site_id/2.4.0").exists()


def test__marker_file_store_cleanup_site_dir(tmp_path: Path) -> None:
    marker_file_store = _MarkerFileStore(tmp_path / "deprecations")
    for idx in range(10):
        marker_file_store.save(SiteId("site_id"), str(idx), [])
    assert len(list((tmp_path / "deprecations/site_id").iterdir())) == 10
    marker_file_store.cleanup_site_dir(SiteId("site_id"))
    assert len(list((tmp_path / "deprecations/site_id").iterdir())) == 5


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
    "ac_test_results_by_site_id, manifests_by_path, problems",
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
            [
                _ACTestResultProblemUnsorted(
                    ident="text",
                    notification_category=_NotificationCategory.log,
                    _ac_test_results={
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
                ),
            ],
            id="unsorted",
        ),
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_1",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        Path(
                            "/omd/sites/site_id_1/local/share/check_mk/web/plugins/metrics/file.py"
                        ),
                    ),
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        Path(
                            "/omd/sites/site_id_2/local/share/check_mk/web/plugins/metrics/file.py"
                        ),
                    ),
                ],
                SiteId("site_id_3"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_3",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_3"),
                        Path(
                            "/omd/sites/site_id_3/local/share/check_mk/web/plugins/metrics/file3.py"
                        ),
                    ),
                ],
            },
            {},
            [
                _ACTestResultProblemFile(
                    ident="local/share/check_mk/web/plugins/metrics/file.py",
                    notification_category=_NotificationCategory.manage_mkps,
                    _ac_test_results={
                        SiteId("site_id_1"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "text",
                                "test_id_1",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id_1"),
                                Path(
                                    "/omd/sites/site_id_1/local/share/check_mk/web/plugins/metrics/file.py"
                                ),
                            ),
                        ],
                        SiteId("site_id_2"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "text",
                                "test_id_2",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id_2"),
                                Path(
                                    "/omd/sites/site_id_2/local/share/check_mk/web/plugins/metrics/file.py"
                                ),
                            ),
                        ],
                    },
                ),
                _ACTestResultProblemFile(
                    ident="local/share/check_mk/web/plugins/metrics/file3.py",
                    notification_category=_NotificationCategory.manage_mkps,
                    _ac_test_results={
                        SiteId("site_id_3"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "text",
                                "test_id_3",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id_3"),
                                Path(
                                    "/omd/sites/site_id_3/local/share/check_mk/web/plugins/metrics/file3.py"
                                ),
                            ),
                        ],
                    },
                ),
            ],
            id="file",
        ),
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_1",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_1"),
                        Path(
                            "/omd/sites/site_id_1/local/share/check_mk/web/plugins/metrics/file.py"
                        ),
                    ),
                ],
                SiteId("site_id_2"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_2",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_2"),
                        Path(
                            "/omd/sites/site_id_2/local/share/check_mk/web/plugins/metrics/file.py"
                        ),
                    ),
                ],
                SiteId("site_id_3"): [
                    ACTestResult(
                        ACResultState.WARN,
                        "text",
                        "test_id_3",
                        "deprecations",
                        "Title",
                        "Help",
                        SiteId("site_id_3"),
                        Path(
                            "/omd/sites/site_id_3/local/share/check_mk/web/plugins/metrics/file3.py"
                        ),
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
                ),
                Path("local/share/check_mk/web/plugins/metrics/file3.py"): Manifest(
                    title="asd3",
                    name=PackageName("asd3"),
                    description="",
                    version=PackageVersion("1.0.0"),
                    version_packaged="2.4.0-2025.03.05",
                    version_min_required="2.4.0-2025.03.05",
                    version_usable_until=None,
                    author="cmkadmin",
                    download_url="",
                    files={PackagePart("web"): [Path("plugins/metrics/file3.py")]},
                ),
            },
            [
                _ACTestResultProblemMKP(
                    ident="asd",
                    notification_category=_NotificationCategory.manage_mkps,
                    _ac_test_results={
                        SiteId("site_id_1"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "text",
                                "test_id_1",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id_1"),
                                Path(
                                    "/omd/sites/site_id_1/local/share/check_mk/web/plugins/metrics/file.py"
                                ),
                            ),
                        ],
                        SiteId("site_id_2"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "text",
                                "test_id_2",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id_2"),
                                Path(
                                    "/omd/sites/site_id_2/local/share/check_mk/web/plugins/metrics/file.py"
                                ),
                            ),
                        ],
                    },
                ),
                _ACTestResultProblemMKP(
                    ident="asd3",
                    notification_category=_NotificationCategory.manage_mkps,
                    _ac_test_results={
                        SiteId("site_id_3"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "text",
                                "test_id_3",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id_3"),
                                Path(
                                    "/omd/sites/site_id_3/local/share/check_mk/web/plugins/metrics/file3.py"
                                ),
                            ),
                        ],
                    },
                ),
            ],
            id="mkp",
        ),
    ],
)
def test__find_ac_test_result_problems(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
    manifests_by_path: Mapping[Path, Manifest],
    problems: Sequence[_ACTestResultProblem],
) -> None:
    assert _find_ac_test_result_problems(ac_test_results_by_site_id, manifests_by_path) == problems


@pytest.mark.parametrize(
    "problem, title, box",
    [
        pytest.param(
            _ACTestResultProblemUnsorted(
                ident="A text",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={
                    SiteId("site_id"): [
                        ACTestResult(
                            ACResultState.WARN,
                            "A text",
                            "test_id",
                            "deprecations",
                            "Title",
                            "Help",
                            SiteId("site_id"),
                            None,
                        ),
                    ],
                },
            ),
            "A text",
            "This may partially work in Checkmk 2.3.0 but will stop working from the next major version onwards.",
            id="unsorted-warn",
        ),
        pytest.param(
            _ACTestResultProblemUnsorted(
                ident="A text",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={
                    SiteId("site_id"): [
                        ACTestResult(
                            ACResultState.CRIT,
                            "A text",
                            "test_id",
                            "deprecations",
                            "Title",
                            "Help",
                            SiteId("site_id"),
                            None,
                        ),
                    ],
                },
            ),
            "A text",
            "This does not work in Checkmk 2.3.0.",
            id="unsorted-crit",
        ),
        pytest.param(
            _ACTestResultProblemFile(
                ident="ident",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={
                    SiteId("site_id"): [
                        ACTestResult(
                            ACResultState.WARN,
                            "text",
                            "test_id",
                            "deprecations",
                            "Title",
                            "Help",
                            SiteId("site_id"),
                            Path(
                                "/omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py"
                            ),
                        ),
                    ],
                },
            ),
            "Deprecated plug-in: ident",
            "This may partially work in Checkmk 2.3.0 but will stop working from the next major version onwards.",
            id="file-warn",
        ),
        pytest.param(
            _ACTestResultProblemFile(
                ident="ident",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={
                    SiteId("site_id"): [
                        ACTestResult(
                            ACResultState.CRIT,
                            "text",
                            "test_id",
                            "deprecations",
                            "Title",
                            "Help",
                            SiteId("site_id"),
                            Path(
                                "/omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py"
                            ),
                        ),
                    ],
                },
            ),
            "Deprecated plug-in: ident",
            "This does not work in Checkmk 2.3.0.",
            id="file-crit",
        ),
        pytest.param(
            _ACTestResultProblemMKP(
                ident="ident",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={
                    SiteId("site_id"): [
                        ACTestResult(
                            ACResultState.WARN,
                            "text",
                            "test_id",
                            "deprecations",
                            "Title",
                            "Help",
                            SiteId("site_id"),
                            Path(
                                "/omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py"
                            ),
                        ),
                    ],
                },
            ),
            "Deprecated extension package: ident",
            "This may partially work in Checkmk 2.3.0 but will stop working from the next major version onwards.",
            id="mkp-warn",
        ),
        pytest.param(
            _ACTestResultProblemMKP(
                ident="ident",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={
                    SiteId("site_id"): [
                        ACTestResult(
                            ACResultState.CRIT,
                            "text",
                            "test_id",
                            "deprecations",
                            "Title",
                            "Help",
                            SiteId("site_id"),
                            Path(
                                "/omd/sites/site_id/local/share/check_mk/web/plugins/metrics/file.py"
                            ),
                        ),
                    ],
                },
            ),
            "Deprecated extension package: ident",
            "This does not work in Checkmk 2.3.0.",
            id="mkp-crit",
        ),
    ],
)
def test_render_problem(problem: _ACTestResultProblem, title: str, box: str) -> None:
    rendered_problem = str(problem.html("2.3.0"))
    assert title in rendered_problem
    assert box in rendered_problem


@pytest.mark.parametrize(
    "problems, users, result",
    [
        pytest.param(
            [],
            [
                _NotifiableUser(
                    UserId("user-id"),
                    [_NotificationCategory.manage_mkps, _NotificationCategory.rule_sets],
                    [],
                ),
            ],
            [],
            id="empty",
        ),
        pytest.param(
            [
                _ACTestResultProblemUnsorted(
                    ident="A text",
                    notification_category=_NotificationCategory.manage_mkps,
                    _ac_test_results={
                        SiteId("site_id"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "A text",
                                "test_id",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id"),
                                None,
                            ),
                        ],
                    },
                ),
            ],
            [
                _NotifiableUser(
                    UserId("user-id-1"),
                    [_NotificationCategory.manage_mkps],
                    [],
                ),
                _NotifiableUser(
                    UserId("user-id-2"),
                    [_NotificationCategory.rule_sets],
                    [],
                ),
            ],
            [
                _ProblemToSend(
                    users=[
                        _NotifiableUser(
                            UserId("user-id-1"),
                            [_NotificationCategory.manage_mkps],
                            [],
                        ),
                    ],
                    content='<h2>A text</h2><div class="error">This may partially work in Checkmk 2.3.0 but will stop working from the next major version onwards.</div><p>We highly recommend solving this issue already in your installation.</p><p>Affected sites: site_id</p><p>Details:</p><table class="data table"><tr class="even0"><td>A text</td><td class="state svcstate"><b class="stmark state1">WARN</b></td></tr></table>',
                ),
            ],
            id="manage-mkps",
        ),
        pytest.param(
            [
                _ACTestResultProblemUnsorted(
                    ident="A text",
                    notification_category=_NotificationCategory.rule_sets,
                    _ac_test_results={
                        SiteId("site_id"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "A text",
                                "",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id"),
                                None,
                            ),
                        ],
                    },
                ),
            ],
            [
                _NotifiableUser(
                    UserId("user-id-1"),
                    [_NotificationCategory.manage_mkps],
                    [],
                ),
                _NotifiableUser(
                    UserId("user-id-2"),
                    [_NotificationCategory.rule_sets],
                    [],
                ),
            ],
            [
                _ProblemToSend(
                    users=[
                        _NotifiableUser(
                            UserId("user-id-2"),
                            [_NotificationCategory.rule_sets],
                            [],
                        ),
                    ],
                    content='<h2>A text</h2><div class="error">This may partially work in Checkmk 2.3.0 but will stop working from the next major version onwards.</div><p>We highly recommend solving this issue already in your installation.</p><p>Affected sites: site_id</p><p>Details:</p><table class="data table"><tr class="even0"><td>A text</td><td class="state svcstate"><b class="stmark state1">WARN</b></td></tr></table>',
                ),
            ],
            id="unsorted",
        ),
        pytest.param(
            [
                _ACTestResultProblemUnsorted(
                    ident="A text",
                    notification_category=_NotificationCategory.rule_sets,
                    _ac_test_results={
                        SiteId("site_id"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "A text",
                                "ACTestUnknownCheckParameterRuleSets",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id"),
                                None,
                            ),
                        ],
                    },
                ),
            ],
            [
                _NotifiableUser(
                    UserId("user-id-1"),
                    [_NotificationCategory.manage_mkps],
                    [],
                ),
                _NotifiableUser(
                    UserId("user-id-2"),
                    [_NotificationCategory.rule_sets],
                    [],
                ),
            ],
            [
                _ProblemToSend(
                    users=[
                        _NotifiableUser(
                            user_id=UserId("user-id-2"),
                            notification_categories=[_NotificationCategory.rule_sets],
                            sent_messages=[],
                        ),
                    ],
                    content="<h2>A text</h2><p>This configuration has no effect in the "
                    "current installation. It may be associated with an older "
                    "version of Checkmk or an unused extension package, in which "
                    "case it can be safely removed. Alternatively, it might belong "
                    "to a temporarily disabled extension package, so you may want "
                    "to retain it for now. You can use the <a "
                    'href="wato.py?mode=unknown_rulesets">unknown rulesets</a> '
                    "page in case you want to remove the rule.</p><p>Affected "
                    'sites: site_id</p><p>Details:</p><table class="data '
                    'table"><tr class="even0"><td>A text</td><td class="state '
                    'svcstate"><b class="stmark state1">WARN</b></td></tr></table>',
                ),
            ],
            id="rule-sets",
        ),
        pytest.param(
            [
                _ACTestResultProblemUnsorted(
                    ident="A text",
                    notification_category=_NotificationCategory.log,
                    _ac_test_results={
                        SiteId("site_id"): [
                            ACTestResult(
                                ACResultState.WARN,
                                "A text",
                                "test_id",
                                "deprecations",
                                "Title",
                                "Help",
                                SiteId("site_id"),
                                None,
                            ),
                        ],
                    },
                ),
            ],
            [
                _NotifiableUser(
                    UserId("user-id"),
                    [_NotificationCategory.manage_mkps, _NotificationCategory.rule_sets],
                    [],
                ),
            ],
            [
                (
                    "Analyze configuration problem notification could not be sent to any user "
                    "(Test: A text, Result: '[WARN] Result: A text')"
                ),
            ],
            id="fallback",
        ),
    ],
)
def test__find_unsorted_problems_to_send(
    problems: Sequence[_ACTestResultProblemUnsorted],
    users: Sequence[_NotifiableUser],
    result: Sequence[_ProblemToSend | str],
) -> None:
    assert list(_find_problems_to_send("2.3.0", problems, users)) == result
