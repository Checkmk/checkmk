#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

import cmk.ccc.version as cmk_version
from cmk.ccc.site import SiteId
from cmk.gui.watolib.analyze_configuration import (
    ac_test_registry,
    ACResultState,
    ACSingleResult,
    ACTest,
    ACTestResult,
    merge_tests,
)
from cmk.utils import paths


def test_registered_ac_tests() -> None:
    expected_ac_tests = [
        "ACTestApacheNumberOfProcesses",
        "ACTestApacheProcessUsage",
        "ACTestBackupConfigured",
        "ACTestBackupNotEncryptedConfigured",
        "ACTestBrokenGUIExtension",
        "ACTestCheckMKHelperUsage",
        "ACTestCheckMKFetcherUsage",
        "ACTestCheckMKCheckerNumber",
        "ACTestCheckMKCheckerUsage",
        "ACTestDeprecatedRuleSets",
        "ACTestUnknownCheckParameterRuleSets",
        "ACTestDeprecatedV1CheckPlugins",
        "ACTestDeprecatedCheckPlugins",
        "ACTestDeprecatedInventoryPlugins",
        "ACTestDeprecatedCheckManpages",
        "ACTestDeprecatedGUIExtensions",
        "ACTestDeprecatedLegacyGUIExtensions",
        "ACTestDeprecatedPNPTemplates",
        "ACTestESXDatasources",
        "ACTestEscapeHTMLDisabled",
        "ACTestGenericCheckHelperUsage",
        "ACTestHTTPSecured",
        "ACTestLDAPSecured",
        "ACTestLiveproxyd",
        "ACTestLivestatusUsage",
        "ACTestLivestatusSecured",
        "ACTestNumberOfUsers",
        "ACTestOldDefaultCredentials",
        "ACTestPersistentConnections",
        "ACTestSizeOfExtensions",
        "ACTestTmpfs",
        "ACTestUnexpectedAllowedIPRanges",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected_ac_tests += [
            "ACTestAlertHandlerEventTypes",
            "ACTestSecureAgentUpdaterTransport",
            "ACTestMknotifydCommunicationEncrypted",
        ]

    registered_plugins = sorted(ac_test_registry.keys())
    assert registered_plugins == sorted(expected_ac_tests)


class _FakeACTestSingleSite(ACTest):
    def category(self) -> str:
        return "category"

    def title(self) -> str:
        return "Fake AC test"

    def help(self) -> str:
        return "Help"

    def is_relevant(self) -> bool:
        return False

    def execute(self) -> Iterator[ACSingleResult]:
        yield ACSingleResult(
            state=ACResultState.OK,
            text="single result 1",
            site_id=SiteId("site_id"),
        )
        yield ACSingleResult(
            state=ACResultState.WARN,
            text="single result 2",
            site_id=SiteId("site_id"),
        )


class _FakeACTestMultiSite(ACTest):
    def category(self) -> str:
        return "category"

    def title(self) -> str:
        return "Fake AC test"

    def help(self) -> str:
        return "Help"

    def is_relevant(self) -> bool:
        return False

    def execute(self) -> Iterator[ACSingleResult]:
        yield ACSingleResult(
            state=ACResultState.OK,
            text="single result 1 1",
            site_id=SiteId("site_id_1"),
        )
        yield ACSingleResult(
            state=ACResultState.WARN,
            text="single result 1 2",
            site_id=SiteId("site_id_1"),
        )
        yield ACSingleResult(
            state=ACResultState.OK,
            text="single result 2 1",
            site_id=SiteId("site_id_2"),
        )
        yield ACSingleResult(
            state=ACResultState.CRIT,
            text="single result 2 2",
            site_id=SiteId("site_id_2"),
        )


@pytest.mark.parametrize(
    "ac_test, test_result",
    [
        pytest.param(
            _FakeACTestSingleSite,
            [
                ACTestResult(
                    state=ACResultState.WARN,
                    text="single result 1, single result 2 (!)",
                    site_id=SiteId("site_id"),
                    test_id="_FakeACTestSingleSite",
                    category="category",
                    title="Fake AC test",
                    help="Help",
                    path=None,
                )
            ],
            id="single-site",
        ),
        pytest.param(
            _FakeACTestMultiSite,
            [
                ACTestResult(
                    state=ACResultState.OK,
                    text="single result 1 1",
                    site_id=SiteId("site_id_1"),
                    test_id="_FakeACTestMultiSite",
                    category="category",
                    title="Fake AC test",
                    help="Help",
                    path=None,
                ),
                ACTestResult(
                    state=ACResultState.WARN,
                    text="single result 1 2",
                    site_id=SiteId("site_id_1"),
                    test_id="_FakeACTestMultiSite",
                    category="category",
                    title="Fake AC test",
                    help="Help",
                    path=None,
                ),
                ACTestResult(
                    state=ACResultState.OK,
                    text="single result 2 1",
                    site_id=SiteId("site_id_2"),
                    test_id="_FakeACTestMultiSite",
                    category="category",
                    title="Fake AC test",
                    help="Help",
                    path=None,
                ),
                ACTestResult(
                    state=ACResultState.CRIT,
                    text="single result 2 2",
                    site_id=SiteId("site_id_2"),
                    test_id="_FakeACTestMultiSite",
                    category="category",
                    title="Fake AC test",
                    help="Help",
                    path=None,
                ),
            ],
            id="multi-sites",
        ),
    ],
)
def test_ac_test_run(ac_test: type[ACTest], test_result: Sequence[ACTestResult]) -> None:
    assert merge_tests({SiteId("site_id"): list(ac_test().run())}) == {
        SiteId("site_id"): test_result
    }


@pytest.mark.parametrize(
    "ac_test_result",
    [
        pytest.param(
            ACTestResult(
                state=ACResultState.OK,
                text="Text",
                site_id=SiteId("NO_SITE"),
                test_id="test_id",
                category="category",
                title="Title",
                help="Help",
                path=Path("/path/to/file"),
            ),
            id="with-path",
        ),
        pytest.param(
            ACTestResult(
                state=ACResultState.OK,
                text="Text",
                site_id=SiteId("NO_SITE"),
                test_id="test_id",
                category="category",
                title="Title",
                help="Help",
                path=None,
            ),
            id="without-path",
        ),
    ],
)
def test_ac_test_result_repr(ac_test_result: ACTestResult) -> None:
    assert ACTestResult.from_repr(ast.literal_eval(repr(ac_test_result))) == ac_test_result
