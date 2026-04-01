#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: SLF001  # Private member accessed

import ssl

import pytest
import requests
import urllib3

from cmk.plugins.kube import prometheus_api, query
from cmk.plugins.kube.schemata import section
from tests.cmk.plugins.kube.agent_kube.factory import (
    ResponseErrorFactory,
    ResponseSuccessFactory,
    SampleFactory,
    VectorFactory,
)

RESPONSEERROR = ResponseErrorFactory.build()
SSLERROR = requests.exceptions.SSLError(
    urllib3.exceptions.MaxRetryError(
        pool=urllib3.HTTPConnectionPool(host="expired.badssl.com", port=443),
        url="/",
        reason=urllib3.exceptions.SSLError(
            ssl.SSLCertVerificationError(
                1,
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)",
            )
        ),
    ),
)
PROXYERROR = requests.exceptions.ProxyError(
    urllib3.exceptions.MaxRetryError(
        pool=urllib3.HTTPConnectionPool(host="expired.badssl.com", port=443),
        url="/",
        reason=urllib3.exceptions.ProxyError(
            "Cannot connect to proxy.",
            OSError("Tunnel connection failed: 404 Not Found"),
        ),
    )
)
CONNECTIONERROR = requests.exceptions.ConnectionError(
    urllib3.exceptions.MaxRetryError(
        pool=urllib3.HTTPConnectionPool(host="abc.com", port=80),
        url="/",
        reason=urllib3.exceptions.NewConnectionError(
            urllib3.connection.HTTPConnection(host="abc.com"),
            "Failed to establish a new connection: [Errno -2] Name or service not known",
        ),
    )
)
VALIDATIONERROR = prometheus_api.parse_raw_response("{}")
EMPTY_DATA = ResponseSuccessFactory.build(data=VectorFactory.build(result=[]))
SUCCESS = ResponseSuccessFactory.build(data=VectorFactory.build(result=SampleFactory.batch(size=3)))


@pytest.mark.parametrize(
    "result, expected_details, expected_type",
    [
        pytest.param(
            SSLERROR,
            "SSLError",
            section.ResultType.request_exception,
            id="ssl error",
        ),
        pytest.param(
            PROXYERROR,
            "ProxyError",
            section.ResultType.request_exception,
            id="proxy error",
        ),
        pytest.param(
            CONNECTIONERROR,
            "ConnectionError",
            section.ResultType.request_exception,
            id="connection error",
        ),
        pytest.param(
            VALIDATIONERROR,
            None,
            section.ResultType.validation_error,
            id="validation error",
        ),
        pytest.param(
            EMPTY_DATA,
            None,
            section.ResultType.response_empty_result,
            id="empty data",
        ),
        pytest.param(
            SUCCESS,
            None,
            section.ResultType.success,
            id="success",
        ),
        pytest.param(
            RESPONSEERROR,
            f"{RESPONSEERROR.error_type}: {RESPONSEERROR.error}",
            section.ResultType.response_error,
            id="response error",
        ),
    ],
)
def test_prometheus__from_result(
    result: query.HTTPResult, expected_details: str, expected_type: section.ResultType
) -> None:
    # Act
    type_, details = section.PrometheusResult._from_result(result)

    # Assert
    assert details == expected_details
    assert type_ == expected_type


@pytest.mark.parametrize(
    "result",
    [SSLERROR, PROXYERROR, CONNECTIONERROR, VALIDATIONERROR, EMPTY_DATA, SUCCESS],
)
def test_prometheus_result_from_response(result: query.HTTPResult) -> None:
    # Assemble
    query_ = query.Query.sum_container_memory_working_set_bytes

    # Act
    error = section.PrometheusResult.from_response((query_, result))

    # Assert
    assert error.query_ == query_
