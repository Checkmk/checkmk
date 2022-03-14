#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.aws_route53 import (
    _DEFAULT_PARAMETERS,
    check_aws_route53,
    discover_aws_route53,
    HealthCheckConfig,
    parse_aws_route53_cloudwatch,
    parse_aws_route53_health_checks,
    Route53CloudwatchMetrics,
    Route53CloudwatchSection,
    Route53HealthCheckSection,
    Route53Parameters,
)

ROUTE53_HEALTH_CHECK_STRING_TABLE = [
    [
        '[{"Id":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"CallerReference":',
        '"8eb4447e-dfe4-4443-940f-fe70bdb66c20",',
        '"HealthCheckConfig":',
        '{"Port":',
        "80,",
        '"Type":',
        '"HTTP",',
        '"FullyQualifiedDomainName":',
        '"tribe29.com",',
        '"RequestInterval":',
        "30,",
        '"FailureThreshold":',
        "3,",
        '"MeasureLatency":',
        "true,",
        '"Inverted":',
        "false,",
        '"Disabled":',
        "false,",
        '"EnableSNI":',
        "false},",
        '"HealthCheckVersion":',
        "1},",
        '{"Id":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"CallerReference":',
        '"f2cc4a60-2eb6-498d-8351-43c5837c7caa",',
        '"HealthCheckConfig":',
        '{"IPAddress":',
        '"45.133.11.14",',
        '"Port":',
        "80,",
        '"Type":',
        '"HTTP",',
        '"RequestInterval":',
        "30,",
        '"FailureThreshold":',
        "3,",
        '"MeasureLatency":',
        "true,",
        '"Inverted":',
        "false,",
        '"Disabled":',
        "false,",
        '"EnableSNI":',
        "false},",
        '"HealthCheckVersion":',
        "1},",
        '{"Id":',
        '"ad21015b-1502-4dfd-a48a-e9cd4d66bc3b",',
        '"CallerReference":',
        '"31ef13d7-4a0c-47dc-9239-3498b88bcdfb",',
        '"HealthCheckConfig":',
        '{"Type":',
        '"CALCULATED",',
        '"Inverted":',
        "false,",
        '"Disabled":',
        "false,",
        '"HealthThreshold":',
        "1,",
        '"ChildHealthChecks":',
        '["94b5c9da-0755-4e02-a135-a3cc45d391d2",',
        '"e07d46a0-50c2-4f45-8165-cd4e39215c7e"]},',
        '"HealthCheckVersion":',
        "1}]",
    ]
]

ROUTE53_CLOUDWATCH_STRING_TABLE = [
    [
        '[{"Id":',
        '"id_0_ChildHealthCheckHealthyCount",',
        '"Label":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_0_ConnectionTime",',
        '"Label":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[167.475,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_0_HealthCheckPercentageHealthy",',
        '"Label":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[100.0,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_0_HealthCheckStatus",',
        '"Label":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[1.0,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_0_SSLHandshakeTime",',
        '"Label":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[335.44375,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_0_TimeToFirstByte",',
        '"Label":',
        '"1756ee96-de4f-4137-b7c3-c9daab1c4a9f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[335.44375,",
        "null]],",
        '"StatusCode":',
        '"Complete"}]',
    ],
    [
        '[{"Id":',
        '"id_1_ChildHealthCheckHealthyCount",',
        '"Label":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_1_ConnectionTime",',
        '"Label":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[168.55625,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_1_HealthCheckPercentageHealthy",',
        '"Label":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[100.0,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_1_HealthCheckStatus",',
        '"Label":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[1.0,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_1_SSLHandshakeTime",',
        '"Label":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_1_TimeToFirstByte",',
        '"Label":',
        '"4f101cb3-ee16-490b-a49d-a354957c315f",',
        '"Timestamps":',
        '["2021-09-27',
        '13:31:00+00:00"],',
        '"Values":',
        "[[383.775,",
        "null]],",
        '"StatusCode":',
        '"Complete"}]',
    ],
]
SECTION_AWS_ROUTE53_CLOUDWATCH = {
    "1756ee96-de4f-4137-b7c3-c9daab1c4a9f": Route53CloudwatchMetrics(
        HealthCheckStatus=1,
        ChildHealthCheckHealthyCount=None,
        ConnectionTime=167.475,
        HealthCheckPercentageHealthy=100.0,
        SSLHandshakeTime=335.44375,
        TimeToFirstByte=335.44375,
    ),
    "4f101cb3-ee16-490b-a49d-a354957c315f": Route53CloudwatchMetrics(
        HealthCheckStatus=1,
        ChildHealthCheckHealthyCount=None,
        ConnectionTime=168.55625,
        HealthCheckPercentageHealthy=100.0,
        SSLHandshakeTime=None,
        TimeToFirstByte=383.775,
    ),
}


SECTION_AWS_ROUTE53_HEALTH_CHECK = {
    "1756ee96-de4f-4137-b7c3-c9daab1c4a9f": HealthCheckConfig(
        Type="HTTP", Port=80, FullyQualifiedDomainName="tribe29.com", IPAddress=None
    ),
    "4f101cb3-ee16-490b-a49d-a354957c315f": HealthCheckConfig(
        Type="HTTP", Port=80, FullyQualifiedDomainName=None, IPAddress="45.133.11.14"
    ),
    "ad21015b-1502-4dfd-a48a-e9cd4d66bc3b": HealthCheckConfig(
        Type="CALCULATED", Port=None, FullyQualifiedDomainName=None, IPAddress=None
    ),
}


@pytest.mark.parametrize(
    "string_table, results",
    [
        (
            [],
            {},
        ),
        (
            ROUTE53_HEALTH_CHECK_STRING_TABLE,
            SECTION_AWS_ROUTE53_HEALTH_CHECK,
        ),
    ],
)
def test_parse_aws_route53_health_checks(
    string_table: StringTable, results: Route53HealthCheckSection
) -> None:
    assert parse_aws_route53_health_checks(string_table) == results


@pytest.mark.parametrize(
    "string_table, results",
    [
        (
            [],
            {},
        ),
        (
            ROUTE53_CLOUDWATCH_STRING_TABLE,
            SECTION_AWS_ROUTE53_CLOUDWATCH,
        ),
    ],
)
def test_parse_aws_route53_cloudwatch(
    string_table: StringTable, results: Route53CloudwatchSection
) -> None:
    assert parse_aws_route53_cloudwatch(string_table) == results


@pytest.mark.parametrize(
    "item, params, section_aws_route53_health_checks, section_aws_route53_cloudwatch, results",
    [
        (
            "1756ee96-de4f-4137-b7c3-c9daab1c4a9f",
            _DEFAULT_PARAMETERS,
            SECTION_AWS_ROUTE53_HEALTH_CHECK,
            SECTION_AWS_ROUTE53_CLOUDWATCH,
            [
                Result(state=State.OK, summary="tribe29.com:80"),
                Result(state=State.OK, summary="Connection time: 167 milliseconds"),
                Metric("aws_route53_connection_time", 0.16747499999999998, levels=(200.0, 500.0)),
                Result(state=State.OK, summary="Health check status: OK"),
                Result(state=State.OK, summary="Health check percentage healthy: 100.00%"),
                Metric("aws_route53_health_check_percentage_healthy", 100.0),
                Result(state=State.OK, summary="SSL handshake time: 335 milliseconds"),
                Metric(
                    "aws_route53_ssl_handshake_time", 0.33544375000000004, levels=(400.0, 1000.0)
                ),
                Result(state=State.OK, summary="Time to first byte: 335 milliseconds"),
                Metric(
                    "aws_route53_time_to_first_byte", 0.33544375000000004, levels=(400.0, 1000.0)
                ),
            ],
        ),
    ],
)
def test_check_aws_route53(
    item: str,
    params: Route53Parameters,
    section_aws_route53_health_checks: Optional[Route53HealthCheckSection],
    section_aws_route53_cloudwatch: Optional[Route53CloudwatchSection],
    results: CheckResult,
) -> None:
    assert (
        list(
            check_aws_route53(
                item,
                params,
                section_aws_route53_health_checks,
                section_aws_route53_cloudwatch,
            )
        )
        == results
    )


@pytest.mark.parametrize(
    "section_aws_route53_health_checks, section_aws_route53_cloudwatch, results",
    [
        (
            None,
            None,
            [],
        ),
        (
            SECTION_AWS_ROUTE53_HEALTH_CHECK,
            SECTION_AWS_ROUTE53_CLOUDWATCH,
            [
                Service(item="1756ee96-de4f-4137-b7c3-c9daab1c4a9f"),
                Service(item="4f101cb3-ee16-490b-a49d-a354957c315f"),
                Service(item="ad21015b-1502-4dfd-a48a-e9cd4d66bc3b"),
            ],
        ),
    ],
)
def test_discover_aws_route53(
    section_aws_route53_health_checks: Optional[Route53HealthCheckSection],
    section_aws_route53_cloudwatch: Optional[Route53CloudwatchSection],
    results: DiscoveryResult,
) -> None:
    assert (
        list(
            discover_aws_route53(
                section_aws_route53_health_checks,
                section_aws_route53_cloudwatch,
            )
        )
        == results
    )
