#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.netapp_ontap_status import check_netapp_ontap_status
from cmk.base.plugins.agent_based.utils.netapp_ontap_models import AlertModel


class AlertModelFactory(ModelFactory):
    __model__ = AlertModel


@pytest.mark.parametrize(
    "alerts_models, expected_result",
    [
        pytest.param(
            [AlertModelFactory.build(name="alert1"), AlertModelFactory.build(name="alert2")],
            [Result(state=State.CRIT, summary="Status: Alerts present")],
            id="alerts present",
        ),
        pytest.param(
            [],
            [Result(state=State.OK, summary="Status: OK")],
            id="no alerts present",
        ),
    ],
)
def test_check_netapp_ontap_status(
    alerts_models: Sequence[AlertModel], expected_result: CheckResult
) -> None:
    result = list(check_netapp_ontap_status(alerts_models))

    assert result == expected_result
