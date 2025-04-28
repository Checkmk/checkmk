#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args

import pytest

from cmk.plugins.aws.special_agent.agent_aws import AWSConfig, NamingConvention


@pytest.mark.parametrize(
    "sys_argv_1, sys_argv_2, expected_result",
    [
        (Args(), Args(), True),
        (Args(foo="Foo"), Args(), False),
        (Args(foo="Foo"), Args(bar="Bar"), False),
        (Args(foo="Foo", bar="Bar"), Args(bar="Bar", foo="Foo"), True),
        (Args(foo="Foo"), Args(foo="Foo", debug=True), True),
        (Args(foo="Foo"), Args(foo="Foo", verbose=True), True),
        (Args(foo="Foo"), Args(foo="Foo", no_cache=True), True),
    ],
)
def test_agent_aws_config_hash_names(
    sys_argv_1: Args, sys_argv_2: Args, expected_result: bool
) -> None:
    aws_config_1 = AWSConfig("heute1", sys_argv_1, ([], []), NamingConvention.ip_region_instance)
    aws_config_2 = AWSConfig("heute1", sys_argv_2, ([], []), NamingConvention.ip_region_instance)
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
            Args(foo="Foo"),
            "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
            True,
        ),
        # Generated hash: hashlib.sha256(b'--barBar').hexdigest()
        (
            Args(foo="Foo"),
            "3a852cfa8c5054d4c54685f9fab4b1213dfe05ab670f16445d0d41ec66628d0c",
            False,
        ),
    ],
)
def test_agent_aws_config_hash_processes(
    sys_argv: Args, hashed_val: str, expected_result: bool
) -> None:
    """Test whether the hash is the same across different python processes"""
    aws_config_1 = AWSConfig("heute1", sys_argv, ([], []), NamingConvention.ip_region_instance)
    assert bool(aws_config_1._compute_config_hash(sys_argv) == hashed_val) is expected_result
