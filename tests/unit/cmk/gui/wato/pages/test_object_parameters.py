#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import MagicMock

import pytest

from cmk.automations.results import AnalyseServiceResult, ServiceInfo
from cmk.ccc.hostaddress import HostName
from cmk.gui.wato.pages.object_parameters import ModeObjectParameters
from cmk.gui.watolib.rulespecs import AllowAll, rulespec_registry
from cmk.utils.rulesets.definition import RuleGroup


def test_handle_auto_origin_no_keyerror_for_unknown_checkgroup() -> None:
    # Regression test for crash report 0caf1f60-fd07-11f0-a9cc-4e6947623c97:
    # _handle_auto_origin used to crash with KeyError when a discovered check's
    # checkgroup had no registered rulespec (e.g. third-party checks like infortend_chassis1).
    checkgroup = "infortend_chassis1"  # third-party check, not in registry
    if RuleGroup.StaticChecks(checkgroup) in rulespec_registry:
        pytest.skip("checkgroup is now registered; test precondition no longer holds")
    if RuleGroup.CheckgroupParameters(checkgroup) in rulespec_registry:
        pytest.skip("checkgroup is now registered; test precondition no longer holds")

    serviceinfo: ServiceInfo = {
        "origin": "auto",
        "checkgroup": checkgroup,
        "checktype": checkgroup,
        "item": None,
        "parameters": {},
    }
    service_result = AnalyseServiceResult(
        service_info=serviceinfo,
        labels={},
        label_sources={},
    )

    mock_self = MagicMock(spec=ModeObjectParameters)
    mock_self._service = "Test Service"
    mock_self._hostname = HostName("testhost")

    ModeObjectParameters._handle_auto_origin(
        mock_self,
        serviceinfo,
        MagicMock(),  # all_rulesets
        AllowAll(),
        service_result,
        lambda: None,  # render_labels
        debug=False,
    )

    mock_self._render_rule_reason.assert_called_once()
