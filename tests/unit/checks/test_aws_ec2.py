#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.check_api import MKCounterWrapped
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

METRICS = {
    "StatusCheckFailed_Instance": 0.0,
    "StatusCheckFailed_System": 0.0,
}


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            METRICS,
            [Service()],
            id="For every disk in the section a Service with no item is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_ec2_discovery(
    section: Mapping[str, float],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2")]

    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_ec2_state_ok(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2")]
    check_result = list(
        check.check_function(
            item="",
            params={},
            section=METRICS,
        )
    )
    assert check_result == [
        Result(state=State.OK, summary="System: passed"),
        Result(state=State.OK, summary="Instance: passed"),
    ]


def test_check_aws_ec2_state_crit(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ec2")]
    check_result = list(
        check.check_function(
            item="",
            params={},
            section={
                "StatusCheckFailed_Instance": 1.0,
                "StatusCheckFailed_System": 2.0,
            },
        )
    )
    assert check_result == [
        Result(state=State.CRIT, summary="System: failed"),
        Result(state=State.CRIT, summary="Instance: failed"),
    ]


def test_check_aws_ec2_raise_error(fix_register: FixRegister) -> None:
    # If both of the fields are missing, the check raises a MKCounterWrapped error
    check = fix_register.check_plugins[CheckPluginName("aws_ec2")]
    with pytest.raises(MKCounterWrapped):
        list(
            check.check_function(
                item="",
                params={},
                section={},
            )
        )
