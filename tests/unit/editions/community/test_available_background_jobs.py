#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.background_job.job import job_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_background_jobs() -> None:
    assert set(job_registry) == {
        "ActivateChangesSchedulerBackgroundJob",
        "ParentScanBackgroundJob",
        "RenameHostsBackgroundJob",
        "RenameHostBackgroundJob",
        "FetchAgentOutputBackgroundJob",
        "OMDConfigChangeBackgroundJob",
        "BulkDiscoveryBackgroundJob",
        "UserSyncBackgroundJob",
        "ServiceDiscoveryBackgroundJob",
        "CheckmkAutomationBackgroundJob",
        "DiagnosticsDumpBackgroundJob",
        "SearchIndexBackgroundJob",
        "AutodiscoveryBackgroundJob",
        "QuickSetupStageActionBackgroundJob",
        "QuickSetupActionBackgroundJob",
        "ProfileReplicationBackgroundJob",
        "RelationDiscoveryBackgroundJob",
        "RelationScanBackgroundJob",
    }
