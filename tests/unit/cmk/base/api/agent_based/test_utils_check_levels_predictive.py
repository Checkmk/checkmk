#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest_mock import MockerFixture

from cmk.utils.type_defs import HostName

from cmk.base.api.agent_based import utils
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.plugin_contexts import current_host, current_service


def test_check_levels_predictive_default_render_func(mocker: MockerFixture) -> None:
    mocker.patch(
        "cmk.base.check_api._prediction.get_levels", return_value=(None, (2.2, 4.2, None, None))
    )

    with current_host(HostName("unittest")), current_service(
        CheckPluginName("test_check"), "unittest-service-description"
    ):
        result = next(utils.check_levels_predictive(42.42, metric_name="metric_name", levels={}))

    assert isinstance(result, Result)
    assert result.summary.startswith("42.42")
