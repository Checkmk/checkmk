#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import io
import json
from argparse import Namespace as Args
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from unittest import mock

import pytest

from cmk.plugins.aws_v2.special_agent.config import AWSConfig, NamingConvention
from cmk.plugins.aws_v2.special_agent.hosts import TargetHost
from cmk.plugins.aws_v2.special_agent.labels import AwsResource
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
                    piggyback_hostname=TargetHost("testconfig"),
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
        assert section_stdout.split("\n")[:2] == [
            "<<<<testconfig>>>>",
            "<<<aws_v2_costs_and_usage:cached(1606382471,38642)>>>",
        ]


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
                    "<<<<test-account>>>>",
                    "<<<labels:sep(0)>>>",
                    (
                        '{"cmk/aws/account": "test-account", "cmk/aws/resource_id": "test-account",'
                        ' "cmk/aws/entity": "account"}'
                    ),
                    "<<<<>>>>",
                ],
                id="standard_aws_host_label",
            ),
            pytest.param(
                {
                    ("costs_and_usage", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(
                            piggyback_hostname=TargetHost("test-account"), content=[{}]
                        )
                    ],
                },
                [
                    "<<<<test-account>>>>",
                    "<<<labels:sep(0)>>>",
                    (
                        '{"cmk/aws/account": "test-account", "cmk/aws/resource_id": "test-account",'
                        ' "cmk/aws/entity": "account"}'
                    ),
                    "<<<<>>>>",
                ],
                id="no_piggyback_label",
            ),
            pytest.param(
                {
                    ("costs_and_usage", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(
                            piggyback_hostname=TargetHost("test-account"), content=[{}]
                        )
                    ],
                    ("ec2", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(
                            piggyback_hostname=TargetHost("test-piggyback"),
                            content=[{}],
                            extra_labels={"cmk/aws/test-key": "test-value"},
                        )
                    ],
                },
                [
                    "<<<<test-account>>>>",
                    "<<<labels:sep(0)>>>",
                    (
                        '{"cmk/aws/account": "test-account", "cmk/aws/resource_id": "test-account",'
                        ' "cmk/aws/entity": "account"}'
                    ),
                    "<<<<>>>>",
                    "<<<<test-piggyback>>>>",
                    "<<<labels:sep(0)>>>",
                    '{"cmk/aws/account": "test-account", "cmk/aws/test-key": "test-value"}',
                    "<<<<>>>>",
                ],
                id="piggyback_ec2_label",
            ),
            pytest.param(
                {
                    ("wafv2_web_acl", 1606382471.693873, 38582.763184): [
                        AWSSectionResult(
                            piggyback_hostname=TargetHost("test-web-acl"), content=[{}]
                        )
                    ],
                },
                [
                    "<<<<test-account>>>>",
                    "<<<labels:sep(0)>>>",
                    (
                        '{"cmk/aws/account": "test-account", "cmk/aws/resource_id": "test-account",'
                        ' "cmk/aws/entity": "account"}'
                    ),
                    "<<<<>>>>",
                    "<<<<test-web-acl>>>>",
                    "<<<labels:sep(0)>>>",
                    '{"cmk/aws/account": "test-account"}',
                    "<<<<>>>>",
                ],
                id="piggyback_host_without_labels_of_its_own",
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


def test_account_name_labels_the_hosts_of_the_resources(capsys: pytest.CaptureFixture[str]) -> None:
    sections = AWSSectionsGeneric(
        hostname="", session=mock.Mock(), account_id="test-account", account_name="production"
    )
    results: Results = {
        ("ec2", 1606382471.693873, 38582.763184): [
            AWSSectionResult(
                piggyback_hostname=TargetHost("test-piggyback"),
                content=[{}],
                extra_labels={"cmk/aws/test-key": "test-value"},
            )
        ],
    }

    sections._write_host_labels(results)  # noqa: SLF001

    lines = capsys.readouterr().out.splitlines()
    assert json.loads(lines[lines.index("<<<<test-piggyback>>>>") + 2]) == {
        "cmk/aws/account": "test-account",
        "cmk/aws/account_name": "production",
        "cmk/aws/test-key": "test-value",
    }


def _account_host_sections() -> AWSSectionsUSEast:
    config = AWSConfig(
        "aws-org", Args(), ([], []), NamingConvention.ip_region_instance
    ).for_account("333333333333")
    sections = AWSSectionsUSEast(hostname="aws-org", session=mock.Mock(), account_id="333333333333")
    sections.init_sections([], "us-east-1", config, ResultDistributorS3Limits(None))
    return sections


@pytest.mark.parametrize(
    "piggyback_hostname",
    [
        pytest.param(TargetHost("aws-org"), id="named like the rule host"),
        pytest.param(TargetHost(""), id="empty name"),
    ],
)
def test_account_host_receives_results_without_a_piggyback_host(
    capsys: pytest.CaptureFixture[str], piggyback_hostname: TargetHost
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


def test_account_host_gets_its_labels_once(capsys: pytest.CaptureFixture[str]) -> None:
    results: Results = {
        ("ec2_limits", 1606382471.693873, 300.0): [
            AWSSectionResult(piggyback_hostname=TargetHost("333333333333"), content=[{}])
        ],
    }

    _account_host_sections()._write_host_labels(results)  # noqa: SLF001

    assert capsys.readouterr().out.splitlines() == [
        "<<<<333333333333>>>>",
        "<<<labels:sep(0)>>>",
        (
            '{"cmk/aws/account": "333333333333", "cmk/aws/resource_id": "333333333333",'
            ' "cmk/aws/entity": "account"}'
        ),
        "<<<<>>>>",
    ]


def test_account_host_receives_the_account_labels(capsys: pytest.CaptureFixture[str]) -> None:
    _account_host_sections()._write_host_labels({})  # noqa: SLF001

    host, header, labels, end = capsys.readouterr().out.splitlines()
    assert (host, header, end) == ("<<<<333333333333>>>>", "<<<labels:sep(0)>>>", "<<<<>>>>")
    assert json.loads(labels) == {
        "cmk/aws/account": "333333333333",
        "cmk/aws/resource_id": "333333333333",
        "cmk/aws/entity": "account",
    }


def test_run_writes_only_into_the_given_output(capsys: pytest.CaptureFixture[str]) -> None:
    output = io.StringIO()

    AWSSectionsGeneric(
        hostname="", session=mock.Mock(), account_id="333333333333", output=output
    ).run()

    assert (capsys.readouterr().out, output.getvalue().splitlines()[:3]) == (
        "",
        ["<<<<333333333333>>>>", "<<<aws_v2_exceptions>>>", "AWSSectionsGeneric: No exceptions"],
    )


def _metadata_by_host(output: str) -> dict[str, object]:
    """The metadata section of each host."""
    metadata: dict[str, object] = {}
    host = ""
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("<<<<"):
            host = line[4:-4]
        elif line == "<<<aws_v2_metadata:sep(0)>>>":
            metadata[host] = json.loads(lines[index + 1])
    return metadata


def test_account_host_gets_the_account_metadata() -> None:
    output = io.StringIO()
    sections = AWSSectionsGeneric(
        hostname="",
        session=mock.Mock(),
        account_id="test-account",
        output=output,
        account_name="production",
    )

    sections.run()

    assert _metadata_by_host(output.getvalue()) == {
        "test-account": {
            "cloud_provider": "AWS",
            "account_id": "test-account",
            "account_name": "production",
            "entity": "account",
            "name": "production",
            "resource_id": "test-account",
        }
    }


def _bucket_result(resource: AwsResource) -> AWSSectionResult:
    return AWSSectionResult(TargetHost("bucket-host"), [{}], resource)


def test_resource_host_gets_the_account_and_resource_metadata() -> None:
    output = io.StringIO()
    sections = AWSSectionsGeneric(
        hostname="", session=mock.Mock(), account_id="test-account", output=output
    )
    bucket = AwsResource(
        service="s3", name="bucket", resource_id="bucket", region="eu-central-1", tags={"a:b": "c"}
    )

    sections._write_host_metadata(  # noqa: SLF001
        {("s3", 1606382471.693873, 300.0): [_bucket_result(bucket)]}
    )

    assert _metadata_by_host(output.getvalue())["bucket-host"] == {
        "cloud_provider": "AWS",
        "account_id": "test-account",
        "entity": "resource",
        "service": "s3",
        "name": "bucket",
        "resource_id": "bucket",
        "region": "eu-central-1",
        "tags": {"a:b": "c"},
    }


@pytest.mark.parametrize(
    "section_names",
    [
        pytest.param(("s3", "s3_requests"), id="known resource first"),
        pytest.param(("s3_requests", "s3"), id="known resource last"),
    ],
)
def test_resource_known_only_by_its_service_does_not_hide_the_known_resource(
    section_names: tuple[str, str],
) -> None:
    output = io.StringIO()
    sections = AWSSectionsGeneric(
        hostname="", session=mock.Mock(), account_id="test-account", output=output
    )
    known, by_service = section_names
    results: Results = {
        (known, 1606382471.693873, 300.0): [
            _bucket_result(AwsResource(service="s3", name="bucket", resource_id="id"))
        ],
        # The cached metrics of this section outlived the bucket in the summary.
        (by_service, 1606382471.693873, 300.0): [_bucket_result(AwsResource(service="s3"))],
    }

    sections._write_host_metadata(results)  # noqa: SLF001

    metadata = _metadata_by_host(output.getvalue())["bucket-host"]
    assert isinstance(metadata, dict) and metadata["resource_id"] == "id"
