#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {"disk": {"FailedSQLServerAgentJobsCount": 99}},
            [Service(item="disk")],
            id="For every disk in the section a Service with no item is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_rds_agent_jobs_discovery(
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_agent_jobs")]
    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_rds_agent_jobs_item_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_agent_jobs")]
    assert (
        list(
            check.check_function(
                item="disk",
                params={},
                section={},
            )
        )
        == []
    )


def test_check_aws_rds_agent_jobs_metric_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_agent_jobs")]
    with pytest.raises(KeyError):
        list(
            check.check_function(
                item="disk",
                params={},
                section={"disk": {"CPUUtilization": 1}},
            )
        )


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            {"disk": {"FailedSQLServerAgentJobsCount": 1}},
            [
                Result(state=State.WARN, summary="Rate of failing jobs: 1.000/s"),
            ],
            id="If there are any FailedSQLServerAgentJobs, the check state turn to WARN and provides a description with more information.",
        ),
        pytest.param(
            {"disk": {"FailedSQLServerAgentJobsCount": 0}},
            [
                Result(state=State.OK, summary="Rate of failing jobs: 0.000/s"),
            ],
            id="If there are no FailedSQLServerAgentJobs, the check state is OK.",
        ),
    ],
)
def test_check_aws_rds_agent_jobs(
    section: Mapping[str, Mapping[str, float]],
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_agent_jobs")]
    check_result = list(
        check.check_function(
            item="disk",
            params={},
            section=section,
        )
    )
    assert check_result == expected_check_result
