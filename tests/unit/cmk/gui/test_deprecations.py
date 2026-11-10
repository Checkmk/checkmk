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
    _ACTestResultProblemGUIPluginFile,
    _ACTestResultProblemGUIPluginPackage,
    _ACTestResultProblemMKP,
    _ACTestResultProblemUnsorted,
    _filter_ac_test_results,
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
        pytest.param(
            {
                SiteId("site_id_1"): [
                    ACTestResult(
                        ACResultState.EXCEPTION,
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
                        ACResultState.EXCEPTION,
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
            id="exception",
        ),
    ],
)
def test__filter_ac_test_results(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
    result: Mapping[SiteId, Sequence[ACTestResult]],
) -> None:
    assert _filter_ac_test_results(ac_test_results_by_site_id) == result


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


def _gui_plugin_finding(state: ACResultState) -> ACTestResult:
    return ACTestResult(
        state,
        "text",
        "ACTestDeprecatedLegacyGUIExtensions",
        "deprecations",
        "Title",
        "Help",
        SiteId("site_id"),
        Path("/omd/sites/site_id/local/share/check_mk/web/plugins/views/file.py"),
    )


def test_gui_plugin_is_reported_by_its_file() -> None:
    finding = _gui_plugin_finding(ACResultState.WARN)
    assert _find_ac_test_result_problems({SiteId("site_id"): [finding]}, {}) == [
        _ACTestResultProblemGUIPluginFile(
            ident="local/share/check_mk/web/plugins/views/file.py",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


def test_broken_gui_extension_is_reported_as_gui_plug_in() -> None:
    finding = ACTestResult(
        ACResultState.CRIT,
        "text",
        "ACTestBrokenGUIExtension",
        "deprecations",
        "Title",
        "Help",
        SiteId("site_id"),
        Path("/omd/sites/site_id/local/share/check_mk/web/plugins/views/file.py"),
    )
    assert _find_ac_test_result_problems({SiteId("site_id"): [finding]}, {}) == [
        _ACTestResultProblemGUIPluginFile(
            ident="local/share/check_mk/web/plugins/views/file.py",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


def test_broken_gui_extension_without_its_file_goes_to_the_package_managers() -> None:
    finding = ACTestResult(
        ACResultState.CRIT,
        "text",
        "ACTestBrokenGUIExtension",
        "deprecations",
        "Title",
        "Help",
        SiteId("site_id"),
        None,
    )
    assert _find_ac_test_result_problems({SiteId("site_id"): [finding]}, {}) == [
        _ACTestResultProblemUnsorted(
            ident="text",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


def _deprecated_rule_set_problems(ruleset: str | None) -> Sequence[_ACTestResultProblem]:
    finding = ACTestResult(
        ACResultState.WARN,
        'Found rules of the rule set "Deprecated: Title".',
        "ACTestDeprecatedRuleSets",
        "deprecations",
        "Title",
        "Help",
        SiteId("site_id"),
        None,
        ruleset,
    )
    return _find_ac_test_result_problems({SiteId("site_id"): [finding]}, {})


def test_deprecated_rule_set_goes_to_the_rule_set_admins() -> None:
    [problem] = _deprecated_rule_set_problems("agent_config:classic_file_deployment")

    assert problem.notification_category is _NotificationCategory.rule_sets


def test_deprecated_rule_set_message() -> None:
    [problem] = _deprecated_rule_set_problems("agent_config:classic_file_deployment")

    assert (
        '<div class="warning">These rules work in Checkmk 2.3.0, but not after the update to the'
        " next major version.</div><p>Migrate the rules to the successor of the rule set or"
        " remove them before the update. The Werk which deprecated the rule set describes its"
        " successor.</p>"
    ) in str(problem.html("2.3.0"))


def test_deprecated_rule_set_message_links_the_rule_set() -> None:
    [problem] = _deprecated_rule_set_problems("agent_config:classic_file_deployment")

    assert (
        '<p><a href="wato.py?mode=edit_ruleset&varname=agent_config%3Aclassic_file_deployment">'
        "Show the rules of this rule set</a></p>"
    ) in str(problem.html("2.3.0"))


def test_deprecated_rule_set_message_of_an_older_remote_site_has_no_link() -> None:
    [problem] = _deprecated_rule_set_problems(None)

    assert "<a " not in str(problem.html("2.3.0"))


_PACKAGE_WITH_GUI_PLUGIN = Manifest(
    title="Package",
    name=PackageName("package"),
    description="",
    version=PackageVersion("1.0.0"),
    version_packaged="2.4.0-2025.03.05",
    version_min_required="2.4.0-2025.03.05",
    version_usable_until=None,
    author="cmkadmin",
    download_url="",
    files={
        PackagePart("web"): [Path("plugins/views/file.py")],
        PackagePart("cmk_addons_plugins"): [Path("family/server_side_calls/agent.py")],
    },
)


def test_gui_plugins_of_an_extension_package_are_grouped_by_the_package() -> None:
    finding = _gui_plugin_finding(ACResultState.CRIT)
    assert _find_ac_test_result_problems(
        {SiteId("site_id"): [finding]},
        {Path("local/share/check_mk/web/plugins/views/file.py"): _PACKAGE_WITH_GUI_PLUGIN},
    ) == [
        _ACTestResultProblemGUIPluginPackage(
            ident="package",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


def test_gui_plugins_and_other_findings_of_a_package_are_reported_apart() -> None:
    gui_plugin_finding = _gui_plugin_finding(ACResultState.CRIT)
    plugin_api_finding = ACTestResult(
        ACResultState.CRIT,
        "text",
        "ACTestSpecialAgentsAPI",
        "deprecations",
        "Title",
        "Help",
        SiteId("site_id"),
        Path(
            "/omd/sites/site_id/local/lib/python3/cmk_addons/plugins/family/server_side_calls/agent.py"
        ),
    )
    assert _find_ac_test_result_problems(
        {SiteId("site_id"): [gui_plugin_finding, plugin_api_finding]},
        {
            Path("local/share/check_mk/web/plugins/views/file.py"): _PACKAGE_WITH_GUI_PLUGIN,
            Path(
                "local/lib/python3/cmk_addons/plugins/family/server_side_calls/agent.py"
            ): _PACKAGE_WITH_GUI_PLUGIN,
        },
    ) == [
        _ACTestResultProblemGUIPluginPackage(
            ident="package",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [gui_plugin_finding]},
        ),
        _ACTestResultProblemMKP(
            ident="package",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [plugin_api_finding]},
        ),
    ]


@pytest.mark.parametrize(
    "problem, text",
    [
        pytest.param(
            _ACTestResultProblemGUIPluginFile(
                ident="ident",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={SiteId("site_id"): [_gui_plugin_finding(ACResultState.CRIT)]},
            ),
            "&#x27;ident&#x27; has no effect in Checkmk.",
            id="file-without-effect",
        ),
        pytest.param(
            _ACTestResultProblemGUIPluginFile(
                ident="ident",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={SiteId("site_id"): [_gui_plugin_finding(ACResultState.CRIT)]},
            ),
            "The details below give the reason.",
            id="file-refers-to-the-details",
        ),
        pytest.param(
            _ACTestResultProblemGUIPluginPackage(
                ident="package",
                notification_category=_NotificationCategory.manage_mkps,
                _ac_test_results={SiteId("site_id"): [_gui_plugin_finding(ACResultState.CRIT)]},
            ),
            "The extension package contains plug-ins which have no effect in Checkmk.",
            id="package-without-effect",
        ),
    ],
)
def test_gui_plugin_message(problem: _ACTestResultProblem, text: str) -> None:
    assert text in str(problem.html("2.3.0"))


def _site_gui_plugin_finding(
    test_id: str, site_id: SiteId, rel_path: str, state: ACResultState
) -> ACTestResult:
    return ACTestResult(
        state,
        "text",
        test_id,
        "deprecations",
        "Title",
        "Help",
        site_id,
        Path("/omd/sites", site_id, rel_path),
    )


def _rendered_messages(
    results_by_site: Mapping[SiteId, Sequence[ACTestResult]],
    manifests_by_path: Mapping[Path, Manifest],
) -> Sequence[str]:
    return [
        str(problem.html("2.3.0"))
        for problem in _find_ac_test_result_problems(results_by_site, manifests_by_path)
    ]


def test_gui_plugin_of_the_gui_plugins_test_is_reported_by_its_file() -> None:
    finding = _site_gui_plugin_finding(
        "ACTestDeprecatedGUIExtensions",
        SiteId("site_id"),
        "local/lib/python3/cmk/gui/plugins/views/file.py",
        ACResultState.WARN,
    )
    assert _find_ac_test_result_problems({SiteId("site_id"): [finding]}, {}) == [
        _ACTestResultProblemGUIPluginFile(
            ident="local/lib/python3/cmk/gui/plugins/views/file.py",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


def test_pnp_template_is_reported_as_a_plugin_without_effect() -> None:
    finding = _site_gui_plugin_finding(
        "ACTestDeprecatedPNPTemplates",
        SiteId("site_id"),
        "local/share/check_mk/pnp-templates/check_mk-my_check.php",
        ACResultState.CRIT,
    )
    assert _find_ac_test_result_problems({SiteId("site_id"): [finding]}, {}) == [
        _ACTestResultProblemGUIPluginFile(
            ident="local/share/check_mk/pnp-templates/check_mk-my_check.php",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


def test_gui_plugin_on_several_sites_is_one_problem() -> None:
    finding_a, finding_b = (
        _site_gui_plugin_finding(
            "ACTestDeprecatedLegacyGUIExtensions",
            site_id,
            "local/share/check_mk/web/plugins/views/file.py",
            ACResultState.WARN,
        )
        for site_id in (SiteId("site_a"), SiteId("site_b"))
    )
    assert _find_ac_test_result_problems(
        {SiteId("site_a"): [finding_a], SiteId("site_b"): [finding_b]}, {}
    ) == [
        _ACTestResultProblemGUIPluginFile(
            ident="local/share/check_mk/web/plugins/views/file.py",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_a"): [finding_a], SiteId("site_b"): [finding_b]},
        )
    ]


def test_gui_plugin_file_message() -> None:
    finding = _site_gui_plugin_finding(
        "ACTestDeprecatedLegacyGUIExtensions",
        SiteId("site_id"),
        "local/share/check_mk/web/plugins/views/file.py",
        ACResultState.WARN,
    )
    assert _rendered_messages({SiteId("site_id"): [finding]}, {}) == [
        (
            "<h2>Plug-in: local/share/check_mk/web/plugins/views/file.py</h2>"
            '<div class="warning">&#x27;local/share/check_mk/web/plugins/views/file.py&#x27; may'
            " break with any update of Checkmk.</div>"
            "<p>The details below give the reason.</p>"
            "<p>Affected sites: site_id</p>"
            "<p>Details:</p>"
            '<table class="data table"><tr class="data even0"><td>text</td>'
            '<td class="state svcstate state1"><span class="state_rounded_fill">WARN</span></td></tr></table>'
        )
    ]


def test_gui_plugin_package_message() -> None:
    finding = _site_gui_plugin_finding(
        "ACTestDeprecatedLegacyGUIExtensions",
        SiteId("site_id"),
        "local/share/check_mk/web/plugins/views/file.py",
        ACResultState.WARN,
    )
    assert _rendered_messages(
        {SiteId("site_id"): [finding]},
        {Path("local/share/check_mk/web/plugins/views/file.py"): _PACKAGE_WITH_GUI_PLUGIN},
    ) == [
        (
            "<h2>Extension package: package</h2>"
            '<div class="warning">The extension package contains plug-ins which may break with'
            " any update of Checkmk.</div>"
            "<p>The details below give the reason.</p>"
            "<p>Affected sites: site_id</p>"
            "<p>Details:</p>"
            '<table class="data table"><tr class="data even0"><td>text</td>'
            '<td class="state svcstate state1"><span class="state_rounded_fill">WARN</span></td></tr></table>'
        )
    ]


_PACKAGE_WITH_TWO_GUI_PLUGINS = Manifest(
    title="Package",
    name=PackageName("package"),
    description="",
    version=PackageVersion("1.0.0"),
    version_packaged="2.4.0-2025.03.05",
    version_min_required="2.4.0-2025.03.05",
    version_usable_until=None,
    author="cmkadmin",
    download_url="",
    files={PackagePart("web"): [Path("plugins/views/file.py"), Path("plugins/metrics/file.py")]},
)


def test_gui_plugin_package_message_describes_its_worst_plugin() -> None:
    findings = [
        _site_gui_plugin_finding(
            "ACTestDeprecatedLegacyGUIExtensions",
            SiteId("site_id"),
            f"local/share/check_mk/web/plugins/{folder}/file.py",
            state,
        )
        for folder, state in (("views", ACResultState.WARN), ("metrics", ACResultState.CRIT))
    ]
    [message] = _rendered_messages(
        {SiteId("site_id"): findings},
        {
            Path(f"local/share/check_mk/web/plugins/{folder}/file.py"): (
                _PACKAGE_WITH_TWO_GUI_PLUGINS
            )
            for folder in ("views", "metrics")
        },
    )
    assert (
        '<div class="error">The extension package contains plug-ins which have no effect in'
        " Checkmk.</div>"
    ) in message


def test_broken_gui_extension_of_an_extension_package_is_grouped_by_the_package() -> None:
    finding = _site_gui_plugin_finding(
        "ACTestBrokenGUIExtension",
        SiteId("site_id"),
        "local/share/check_mk/web/plugins/views/file.py",
        ACResultState.CRIT,
    )
    assert _find_ac_test_result_problems(
        {SiteId("site_id"): [finding]},
        {Path("local/share/check_mk/web/plugins/views/file.py"): _PACKAGE_WITH_GUI_PLUGIN},
    ) == [
        _ACTestResultProblemGUIPluginPackage(
            ident="package",
            notification_category=_NotificationCategory.manage_mkps,
            _ac_test_results={SiteId("site_id"): [finding]},
        )
    ]


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
            "This may partially work in Checkmk 2.3.0 but might not work from the next major version onwards.",
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
            "This may partially work in Checkmk 2.3.0 but might not work from the next major version onwards.",
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
            "This may partially work in Checkmk 2.3.0 but might not work from the next major version onwards.",
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
    "state, box_html",
    [
        pytest.param(ACResultState.CRIT, '<div class="error">', id="crit"),
        pytest.param(ACResultState.WARN, '<div class="warning">', id="warn"),
    ],
)
def test_render_problem_shows_the_box(state: ACResultState, box_html: str) -> None:
    problem = _ACTestResultProblemUnsorted(
        ident="A text",
        notification_category=_NotificationCategory.manage_mkps,
        _ac_test_results={
            SiteId("site_id"): [
                ACTestResult(
                    state,
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
    )
    assert box_html in str(problem.html("2.3.0"))


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
                    content='<h2>A text</h2><div class="warning">This may partially work in Checkmk 2.3.0 but might not work from the next major version onwards.</div><p>We highly recommend solving this issue already in your installation.</p><p>Affected sites: site_id</p><p>Details:</p><table class="data table"><tr class="data even0"><td>A text</td><td class="state svcstate state1"><span class="state_rounded_fill">WARN</span></td></tr></table>',
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
                    content='<h2>A text</h2><div class="warning">This may partially work in Checkmk 2.3.0 but might not work from the next major version onwards.</div><p>We highly recommend solving this issue already in your installation.</p><p>Affected sites: site_id</p><p>Details:</p><table class="data table"><tr class="data even0"><td>A text</td><td class="state svcstate state1"><span class="state_rounded_fill">WARN</span></td></tr></table>',
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
                    content='<h2>A text</h2><div class="warning">These rules have no effect in'
                    " Checkmk 2.3.0.</div><p>This configuration has no effect in the "
                    "current installation. It may be associated with an older "
                    "version of Checkmk or an unused extension package, in which "
                    "case it can be safely removed. Alternatively, it might belong "
                    "to a temporarily disabled extension package, so you may want "
                    "to retain it for now. You can use the <a "
                    'href="wato.py?mode=unknown_rulesets">unknown rule sets</a> '
                    "page in case you want to remove the rule.</p><p>Affected "
                    'sites: site_id</p><p>Details:</p><table class="data '
                    'table"><tr class="data even0"><td>A text</td><td class="state '
                    'svcstate state1"><span class="state_rounded_fill">WARN</span></td></tr></table>',
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
