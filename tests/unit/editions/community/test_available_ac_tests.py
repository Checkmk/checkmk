#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.analyze_configuration import ac_test_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_ac_tests() -> None:
    expected_ac_tests = [
        "ACTestApacheNumberOfProcesses",
        "ACTestApacheProcessUsage",
        "ACTestAutomationUserSecret",
        "ACTestBackupConfigured",
        "ACTestBackupNotEncryptedConfigured",
        "ACTestBrokenGUIExtension",
        "ACTestCheckMKHelperUsage",
        "ACTestCheckMKFetcherUsage",
        "ACTestCheckMKCheckerNumber",
        "ACTestCheckMKCheckerUsage",
        "ACTestDeprecatedRuleSets",
        "ACTestUnknownCheckParameterRuleSets",
        "ACTestDeprecatedGUIExtensions",
        "ACTestDeprecatedLegacyGUIExtensions",
        "ACTestDeprecatedPNPTemplates",
        "ACTestEscapeHTMLDisabled",
        "ACTestGenericCheckHelperUsage",
        "ACTestHTTPSecured",
        "ACTestLDAPSecured",
        "ACTestLiveproxyd",
        "ACTestLivestatusUsage",
        "ACTestLivestatusSecured",
        "ACTestNumberOfUsers",
        "ACTestBakeryAPI",
        "ACTestHaSIAPI",
        "ACTestPasswordStoreAPI",
        "ACTestSpecialAgentsAPI",
        "ACTestPersistentConnections",
        "ACTestSizeOfExtensions",
        "ACTestTmpfs",
        "ACTestUnexpectedAllowedIPRanges",
    ]

    registered_plugins = sorted(ac_test_registry.keys())
    assert registered_plugins == sorted(expected_ac_tests)
