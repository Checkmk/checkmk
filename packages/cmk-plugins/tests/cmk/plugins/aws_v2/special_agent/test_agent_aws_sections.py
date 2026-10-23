#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from argparse import Namespace as Args
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from unittest import mock

import pytest

from cmk.plugins.aws_v2.special_agent.config import AWSConfig, NamingConvention
from cmk.plugins.aws_v2.special_agent.hosts import SOURCE_HOST, TargetHost
from cmk.plugins.aws_v2.special_agent.runner import (
    AWSSectionsGeneric,
    AWSSectionsUSEast,
    Results,
)
from cmk.plugins.aws_v2.special_agent.sections.core import (
    AWSSectionResult,
    get_seconds_since_midnight,
)
from cmk.plugins.aws_v2.special_agent.sections.s3 import ResultDistributorS3Limits


@pytest.mark.parametrize(
    "now, result",
    [
        ("2020-07-24 00:00:16.0", 16.0),
        ("2020-07-13 00:01:00.194", 60.194),
    ],
)
def test_get_seconds_since_midnight(now: str, result: float) -> None:
    assert get_seconds_since_midnight(datetime.strptime(now, "%Y-%m-%d %H:%M:%S.%f")) == result


class TestAWSSections:
    @pytest.fixture
    def services(self) -> Any:
        return "testservice"

    @pytest.fixture
    def region(self) -> Any:
        return "testregion"

    @pytest.fixture
    def config(self) -> Any:
        return "testconfig"

    @pytest.fixture
    def generic_section(self, services: Any, region: Any, config: Any) -> AWSSectionsGeneric:
        return AWSSectionsGeneric(services, region, config)

    def test_section_header(
        self, generic_section: AWSSectionsGeneric, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cached_data: Results = {
            ("costs_and_usage", 1606382471.693873, 38582.763184): [
                AWSSectionResult(
                    piggyback_hostname=SOURCE_HOST,
                    content=[
                        {
                            "TimePeriod": {
                                "Start": "2020-11-25",
                                "End": "2020-11-26",
                            },
                            "Total": {
                                "UnblendedCost": {
                                    "Amount": "0",
                                    "Unit": "USD",
                                }
                            },
                            "Groups": [],
                            "Estimated": True,
                        },
                    ],
                )
            ],
        }
        generic_section._write_section_results(cached_data)  # noqa: SLF001
        section_stdout = capsys.readouterr().out
        assert (
            section_stdout.split("\n")[0] == "<<<aws_v2_costs_and_usage:cached(1606382471,38642)>>>"
        )


class TestAWSHostLabelSections:
    @pytest.fixture
    def account_id(self) -> str:
        return "test-account"

    @pytest.fixture
    def generic_section(self, account_id: str) -> AWSSectionsGeneric:
        return AWSSectionsGeneric(hostname="", session=mock.Mock(), account_id=account_id)

    @pytest.mark.parametrize(
        "cached_data,expected_lines",
        [
            pytest.param(
                {},
                [
                    "<<<labels:sep(0)>>>",
                    '{"cmk/aws/account": "test-account"}',
                ],
                id="standard_aws_host_label",
            ),
            pytest.param(
                {
                    ("costs_and_usage", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(piggyback_hostname=SOURCE_HOST, content=[{}])
                    ],
                },
                [
                    "<<<labels:sep(0)>>>",
                    '{"cmk/aws/account": "test-account"}',
                ],
                id="no_piggyback_label",
            ),
            pytest.param(
                {
                    ("costs_and_usage", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(piggyback_hostname=SOURCE_HOST, content=[{}])
                    ],
                    ("ec2", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(
                            piggyback_hostname=TargetHost("test-piggyback"),
                            content=[{}],
                            piggyback_host_labels={"cmk/aws/test-key": "test-value"},
                        )
                    ],
                },
                [
                    "<<<labels:sep(0)>>>",
                    '{"cmk/aws/account": "test-account"}',
                    "<<<<test-piggyback>>>>",
                    "<<<labels:sep(0)>>>",
                    '{"cmk/aws/account": "test-account", "cmk/aws/test-key": "test-value"}',
                    "<<<<>>>>",
                ],
                id="piggyback_ec2_label",
            ),
        ],
    )
    def test_label_section_header(  # type: ignore[misc]
        self,
        generic_section: AWSSectionsGeneric,
        capsys: pytest.CaptureFixture[str],
        cached_data: Results,
        expected_lines: Sequence[str],
    ) -> None:
        generic_section._write_host_labels(cached_data)  # noqa: SLF001
        section_stdout = capsys.readouterr().out
        assert section_stdout.strip().split("\n") == expected_lines


def _account_host_sections() -> AWSSectionsUSEast:
    config = AWSConfig(
        "aws-org", Args(), ([], []), NamingConvention.ip_region_instance
    ).for_account("333333333333", host="333333333333")
    sections = AWSSectionsUSEast(hostname="aws-org", session=mock.Mock(), account_id="333333333333")
    sections.init_sections([], "us-east-1", config, ResultDistributorS3Limits())
    return sections


@pytest.mark.parametrize(
    "piggyback_hostname",
    [
        pytest.param(SOURCE_HOST, id="source host"),
        pytest.param(TargetHost("aws-org"), id="named like the rule host"),
        pytest.param(TargetHost(""), id="empty name"),
    ],
)
def test_account_host_receives_results_without_a_piggyback_host(
    capsys: pytest.CaptureFixture[str], piggyback_hostname: TargetHost | None
) -> None:
    results: Results = {
        ("ec2_limits", 1606382471.693873, 300.0): [
            AWSSectionResult(piggyback_hostname=piggyback_hostname, content=[{"limit": 1}])
        ],
    }

    _account_host_sections()._write_section_results(results)  # noqa: SLF001

    assert capsys.readouterr().out.splitlines() == [
        "<<<<333333333333>>>>",
        "<<<aws_v2_ec2_limits:cached(1606382471,360)>>>",
        '[{"limit": 1}]',
        "<<<<>>>>",
    ]


def test_account_host_keeps_resource_piggyback_hosts(capsys: pytest.CaptureFixture[str]) -> None:
    results: Results = {
        ("ec2", 1606382471.693873, 300.0): [
            AWSSectionResult(
                piggyback_hostname=TargetHost("10.0.0.1-eu-central-1-i-1"), content=[{}]
            )
        ],
    }

    _account_host_sections()._write_section_results(results)  # noqa: SLF001

    assert capsys.readouterr().out.splitlines()[0] == "<<<<10.0.0.1-eu-central-1-i-1>>>>"


def test_account_host_receives_the_labels(capsys: pytest.CaptureFixture[str]) -> None:
    _account_host_sections()._write_host_labels({})  # noqa: SLF001

    assert capsys.readouterr().out.splitlines() == [
        "<<<<333333333333>>>>",
        "<<<labels:sep(0)>>>",
        '{"cmk/aws/account": "333333333333"}',
        "<<<<>>>>",
    ]
