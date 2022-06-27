#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest

from cmk.special_agents.agent_aws import AWSConfig


@pytest.mark.parametrize(
    "sys_argv_1, sys_argv_2, expected_result",
    [
        ([], [], True),
        (["--foo", "Foo"], [], False),
        (["--foo", "Foo"], ["--bar", "Bar"], False),
        (["--foo", "Foo", "--bar", "Bar"], ["--bar", "Bar", "--foo", "Foo"], True),
        (["--foo", "Foo"], ["--foo", "Foo", "--debug"], True),
        (["--foo", "Foo"], ["--foo", "Foo", "--verbose"], True),
        (["--foo", "Foo"], ["--foo", "Foo", "--no-cache"], True),
    ],
)
def test_agent_aws_config_hash_names(sys_argv_1, sys_argv_2, expected_result) -> None:
    aws_config_1 = AWSConfig("heute1", sys_argv_1, (None, None))
    aws_config_2 = AWSConfig("heute1", sys_argv_2, (None, None))
    assert (
        bool(
            aws_config_1._compute_config_hash(sys_argv_1)
            == aws_config_2._compute_config_hash(sys_argv_2)
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "sys_argv, hashed_val, expected_result",
    [
        # Generated hash: hashlib.sha256(b'--fooFoo').hexdigest()
        (
            ["--foo", "Foo"],
            "690d85a83cb4f3c81540ce013e3e23db1a7ded3b596e8f59b2809b8b1c91ebf9",
            True,
        ),
        # Generated hash: hashlib.sha256(b'--barBar').hexdigest()
        (
            ["--foo", "Foo"],
            "3a852cfa8c5054d4c54685f9fab4b1213dfe05ab670f16445d0d41ec66628d0c",
            False,
        ),
    ],
)
def test_agent_aws_config_hash_processes(sys_argv, hashed_val, expected_result) -> None:
    """Test whether the hash is the same across different python processes"""
    aws_config_1 = AWSConfig("heute1", sys_argv, (None, None))
    assert bool(aws_config_1._compute_config_hash(sys_argv) == hashed_val) is expected_result
