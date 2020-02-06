# -*- encoding: utf-8; py-indent-offset: 4 -*-
# pylint: disable=redefined-outer-name

import pytest  # type: ignore

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
