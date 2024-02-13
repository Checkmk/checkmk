#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_status import check_netapp_ontap_status
from cmk.plugins.netapp.models import AlertModel


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
