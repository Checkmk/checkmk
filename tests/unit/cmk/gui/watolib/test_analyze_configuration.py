#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.utils.version as cmk_version

import cmk.gui.wato  # noqa: F401 # pylint: disable=unused-import
import cmk.gui.watolib as watolib


def test_registered_ac_tests():
    expected_ac_tests = [
        "ACTestAlertHandlerEventTypes",
        "ACTestApacheNumberOfProcesses",
        "ACTestApacheProcessUsage",
        "ACTestBackupConfigured",
        "ACTestBackupNotEncryptedConfigured",
        "ACTestBrokenGUIExtension",
        "ACTestCheckMKHelperUsage",
        "ACTestCheckMKFetcherUsage",
        "ACTestCheckMKCheckerNumber",
        "ACTestCheckMKCheckerUsage",
        "ACTestConnectivity",
        "ACTestDeprecatedInventoryPlugins",
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
        "ACTestRulebasedNotifications",
        "ACTestSizeOfExtensions",
        "ACTestTmpfs",
        "ACTestUnexpectedAllowedIPRanges",
        "ACTestMknotifydCommunicationEncrypted",
    ]

    if not cmk_version.is_raw_edition():
        expected_ac_tests += [
            "ACTestSecureAgentUpdaterTransport",
        ]

    registered_plugins = sorted(watolib.ac_test_registry.keys())
    assert registered_plugins == sorted(expected_ac_tests)
