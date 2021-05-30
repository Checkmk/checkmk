#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import State, Result

from cmk.base.plugins.agent_based.fuse_instance import (
    check_fuse_instance,
    FUSE_UP,
    FAILED_AUTH,
    NO_DATA,
    CONNECTION_FAILED
)

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('section,result', [
    (
        "up",
        [
            Result(
                state=State.OK,
                summary=FUSE_UP,
            )
        ]
    ),
    (
        "unauth",
        [
            Result(
                state=State.CRIT,
                summary=FAILED_AUTH,
            )
        ]
    ),
    (
        "empty",
        [
            Result(
                state=State.CRIT,
                summary=NO_DATA,
            )
        ]
    ),
    (
        "down",
        [
            Result(
                state=State.CRIT,
                summary=CONNECTION_FAILED,
            )
        ]
    ),
])
def test_check_fuse_instance(section, result):
    assert list(check_fuse_instance({}, section)) == result
