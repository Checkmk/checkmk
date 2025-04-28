#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from unittest import mock

import pytest

from cmk.plugins.aws.special_agent.agent_aws import AWSSectionResult, AWSSectionsGeneric, Results


class TestAWSSections:
    @pytest.fixture
    def services(self):
        return "testservice"

    @pytest.fixture
    def region(self):
        return "testregion"

    @pytest.fixture
    def config(self):
        return "testconfig"

    @pytest.fixture
    def generic_section(self, services, region, config):
        return AWSSectionsGeneric(services, region, config)

    def test_section_header(
        self, generic_section: AWSSectionsGeneric, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cached_data: Results = {
            ("costs_and_usage", 1606382471.693873, 38582.763184): [
                AWSSectionResult(
                    piggyback_hostname="",
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
        generic_section._write_section_results(cached_data)
        section_stdout = capsys.readouterr().out
        assert section_stdout.split("\n")[0] == "<<<aws_costs_and_usage:cached(1606382471,38642)>>>"


class TestAWSHostLabelSections:
    @pytest.fixture
    def account_id(self):
        return "test-account"

    @pytest.fixture
    def generic_section(self, account_id):
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
                        AWSSectionResult(piggyback_hostname="", content=[{}])
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
                        AWSSectionResult(piggyback_hostname="", content=[{}])
                    ],
                    ("ec2", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(
                            piggyback_hostname="test-piggyback",
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
    def test_label_section_header(
        self,
        generic_section: AWSSectionsGeneric,
        capsys: pytest.CaptureFixture[str],
        cached_data: Results,
        expected_lines: Sequence[str],
    ) -> None:
        generic_section._write_host_labels(cached_data)
        section_stdout = capsys.readouterr().out
        assert section_stdout.strip().split("\n") == expected_lines
