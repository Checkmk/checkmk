#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest  # type: ignore[import]

from cmk.special_agents.agent_aws import (
    AWSConfig,)


@pytest.mark.parametrize("sys_argv_1, sys_argv_2, expected_result", [
    ([], [], True),
    (['--foo', 'Foo'], [], False),
    (['--foo', 'Foo'], ['--bar', 'Bar'], False),
    (['--foo', 'Foo', '--bar', 'Bar'], ['--bar', 'Bar', '--foo', 'Foo'], True),
    (['--foo', 'Foo'], ['--foo', 'Foo', '--debug'], True),
    (['--foo', 'Foo'], ['--foo', 'Foo', '--verbose'], True),
    (['--foo', 'Foo'], ['--foo', 'Foo', '--no-cache'], True),
])
def test_agent_aws_config_hash_names(sys_argv_1, sys_argv_2, expected_result):
    aws_config_1 = AWSConfig('heute1', sys_argv_1, (None, None))
    aws_config_2 = AWSConfig('heute1', sys_argv_2, (None, None))
    assert bool(
        aws_config_1._compute_config_hash(sys_argv_1) == aws_config_2._compute_config_hash(
            sys_argv_2)) is expected_result
