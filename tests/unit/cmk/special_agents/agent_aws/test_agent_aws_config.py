#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

# pylint: disable=redefined-outer-name

from argparse import Namespace as Args
from pathlib import Path

import pytest

from cmk.special_agents import agent_aws
from cmk.special_agents.agent_aws import AWSConfig, NamingConvention, parse_arguments


@pytest.mark.parametrize(
    "sys_argv_1, sys_argv_2, expected_result",
    [
        (Args(), Args(), True),
        (Args(foo="Foo"), Args(), False),
        (Args(foo="Foo"), Args(foo="Bar"), False),
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
        # Generated hash: hashlib.sha256(b'{"foo": "Foo"}').hexdigest()
        (
            Args(foo="Foo"),
            "bc2bca1f8f015ef34df08e4b6b2ca771767c1f32bc691968bd75e4ac0bccaede",
            True,
        ),
        # Generated hash: hashlib.sha256(b'{"bar": "Bar"}').hexdigest()
        (
            Args(foo="Foo"),
            "42b074273b1b8fa2d1e8d07aff61d1670cf09262741d0ffd480c918a0a3b5f9a",
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


def test_config_hash_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Written config hash must round-trip correctly so the config is not
    considered changed on subsequent runs.
    """
    monkeypatch.setattr(agent_aws, "AWSCacheFilePath", tmp_path)
    args = Args(foo="Foo")
    cfg = AWSConfig("heute1", args, ([], []), NamingConvention.ip_region_instance)
    cfg._write_config_hash()
    assert cfg._load_config_hash() == cfg._current_config_hash


def test_changed_option_value_makes_the_config_out_of_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_aws, "AWSCacheFilePath", tmp_path)
    AWSConfig(
        "heute1", Args(regions=["eu-central-1"]), ([], []), NamingConvention.ip_region_instance
    ).is_up_to_date()  # first run stores the hash

    changed = AWSConfig(
        "heute1", Args(regions=["eu-west-1"]), ([], []), NamingConvention.ip_region_instance
    )

    assert not changed.is_up_to_date()


def test_unchanged_agent_command_line_keeps_the_config_up_to_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_aws, "AWSCacheFilePath", tmp_path)
    argv = [
        "--hostname",
        "aws-host",
        "--piggyback-naming-convention",
        "ip_region_instance",
        "--ignore-all-tags",
        "--access-key-id",
        "AKIAEXAMPLE",
        "--secret-access-key",
        "secret",
        "--regions",
        "eu-central-1",
        "--services",
        "ec2",
    ]
    AWSConfig(
        "heute1", parse_arguments(argv), ([], []), NamingConvention.ip_region_instance
    ).is_up_to_date()  # first run stores the hash

    rerun = AWSConfig(
        "heute1", parse_arguments(argv), ([], []), NamingConvention.ip_region_instance
    )

    assert rerun.is_up_to_date()
