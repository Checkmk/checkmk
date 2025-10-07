#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cmk.agent_receiver.middleware import B3RequestIDMiddleware


@pytest.fixture
def app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(B3RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"message": "test"}

    return app


@pytest.fixture
def client(app_with_middleware: FastAPI) -> TestClient:
    return TestClient(app_with_middleware)


@pytest.mark.parametrize(
    "header_name,trace_id,header_value,expected_preserved",
    [
        pytest.param(
            "b3",
            "80f198ee56343ba864fe8b2a57d3eff7",
            "80f198ee56343ba864fe8b2a57d3eff7-e457b5a2e4d86bd1-1",
            "b3",
            id="b3_single_header",
        ),
        pytest.param(
            "x-b3-traceid",
            "64fe8b2a57d3eff7",
            "64fe8b2a57d3eff7",
            "x-b3-traceid",
            id="b3_multi_header",
        ),
        pytest.param(
            "x-trace-id",
            "custom-trace-id-123",
            "custom-trace-id-123",
            "x-trace-id",
            id="x_trace_id_header",
        ),
        pytest.param(
            "x-request-id",
            "request-id-456",
            "request-id-456",
            "x-request-id",
            id="x_request_id_header",
        ),
    ],
)
def test_trace_header_extraction_and_propagation(
    client: TestClient, header_name: str, trace_id: str, header_value: str, expected_preserved: str
) -> None:
    response = client.get("/test", headers={header_name: header_value})
    assert response.headers["x-request-id"] == trace_id
    # Verify original header is preserved per B3 spec
    assert response.headers[expected_preserved] == header_value


@pytest.mark.parametrize(
    "headers,expected_trace_id",
    [
        pytest.param(
            {
                "b3": "80f198ee56343ba8-e457b5a2e4d86bd1-1",
                "x-b3-traceid": "64fe8b2a57d3eff7",
                "x-trace-id": "arbitrary-trace-id",
                "x-request-id": "arbitrary-request-id",
            },
            "80f198ee56343ba8",
            id="b3_single_takes_precedence",
        ),
        pytest.param(
            {
                "b3": "80f198ee56343ba864fe8b2a57d3eff7-e457b5a2e4d86bd1-1",
                "x-b3-traceid": "different-trace-id-value",
            },
            "80f198ee56343ba864fe8b2a57d3eff7",
            id="b3_single_precedence_over_multi",
        ),
        pytest.param(
            {
                "x-b3-traceid": "64fe8b2a57d3eff7",
                "x-trace-id": "arbitrary-trace-id",
                "x-request-id": "arbitrary-request-id",
            },
            "64fe8b2a57d3eff7",
            id="x_b3_traceid_precedence",
        ),
        pytest.param(
            {
                "x-trace-id": "arbitrary-trace-id",
                "x-request-id": "arbitrary-request-id",
            },
            "arbitrary-trace-id",
            id="x_trace_id_precedence",
        ),
        pytest.param(
            {
                "x-request-id": "arbitrary-request-id",
            },
            "arbitrary-request-id",
            id="x_request_id_fallback",
        ),
    ],
)
def test_header_precedence_order(
    client: TestClient, headers: dict[str, str], expected_trace_id: str
) -> None:
    response = client.get("/test", headers=headers)
    assert response.headers["x-request-id"] == expected_trace_id


def test_generates_otel_trace_id_when_no_headers(client: TestClient) -> None:
    response = client.get("/test")
    request_id = response.headers["x-request-id"]
    # Verify OpenTelemetry trace ID format: 32 lowercase hex characters
    assert len(request_id) == 32
    assert re.match(r"^[0-9a-f]{32}$", request_id), f"Invalid trace ID format: {request_id}"
    assert request_id != "0" * 32, "Trace ID cannot be all zeros per OpenTelemetry spec"


@pytest.mark.parametrize(
    "header_name,header_value",
    [
        pytest.param("b3", "malformed", id="b3_malformed_header"),
        pytest.param("x-trace-id", "any-custom-value", id="x_trace_id_custom_value"),
        pytest.param("x-request-id", "arbitrary-request-123", id="x_request_id_arbitrary_value"),
    ],
)
def test_trusts_client_provided_trace_values(
    client: TestClient, header_name: str, header_value: str
) -> None:
    response = client.get("/test", headers={header_name: header_value})
    assert response.headers["x-request-id"] == header_value


@pytest.mark.parametrize(
    "header_name",
    [
        pytest.param("b3", id="b3_empty"),
        pytest.param("x-b3-traceid", id="x_b3_traceid_empty"),
    ],
)
def test_generates_new_trace_id_for_empty_headers(client: TestClient, header_name: str) -> None:
    response = client.get("/test", headers={header_name: ""})
    request_id = response.headers["x-request-id"]
    # Should generate new OpenTelemetry-compliant trace ID
    assert len(request_id) == 32
    assert re.match(r"^[0-9a-f]{32}$", request_id)
    assert request_id != "0" * 32


@pytest.mark.parametrize(
    "primary_header,other_headers,expected_preserved_header",
    [
        pytest.param(
            ("b3", "80f198ee56343ba864fe8b2a57d3eff7-e457b5a2e4d86bd1-1"),
            {
                "x-b3-traceid": "different-trace-id",
                "x-b3-spanid": "e457b5a2e4d86bd1",
                "x-b3-sampled": "1",
            },
            "b3",
            id="b3_single_header_preserved",
        ),
        pytest.param(
            ("x-b3-traceid", "64fe8b2a57d3eff7"),
            {
                "x-b3-spanid": "e457b5a2e4d86bd1",
                "x-b3-sampled": "1",
            },
            "x-b3-traceid",
            id="x_b3_traceid_preserved",
        ),
        pytest.param(
            ("x-trace-id", "custom-trace-123"),
            {
                "x-custom": "ignored",
                "authorization": "Bearer token",
            },
            "x-trace-id",
            id="x_trace_id_preserved",
        ),
    ],
)
def test_header_preservation_only_uses_the_primary_trace_header(
    client: TestClient,
    primary_header: tuple[str, str],
    other_headers: dict[str, str],
    expected_preserved_header: str,
) -> None:
    header_name, header_value = primary_header
    all_headers = {header_name: header_value, **other_headers}
    response = client.get("/test", headers=all_headers)

    # Only the primary trace header should be preserved
    assert response.headers[expected_preserved_header] == header_value

    # Other headers should not be preserved (except x-request-id we add)
    for other_header in other_headers:
        if (
            other_header.startswith(("x-b3-", "x-trace-", "x-request-"))
            and other_header != expected_preserved_header
        ):
            assert other_header not in response.headers
