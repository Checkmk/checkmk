#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Iterator
from urllib.parse import parse_qs

import pytest
import requests
import responses

from cmk.plugins.veeam.special_agent.agent_veeam import (
    AuthenticationFailed,
    CertificateRejected,
    create_session,
    FatalError,
    fetch_list,
    fetch_object,
    main,
    ServerUnreachable,
    UnsupportedApiVersion,
    VeeamClient,
    write_sections,
)

URL = "https://veeam.example.com:9419"
TOKEN_URL = f"{URL}/api/oauth2/token"


@pytest.fixture(name="api")
def _api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as api:
        yield api


def _client(cert_server_name: str | None = None) -> VeeamClient:
    return VeeamClient(
        create_session(URL, cert_server_name), URL, cert_server_name=cert_server_name, timeout=30
    )


def _logged_in_client(api: responses.RequestsMock) -> VeeamClient:
    api.post(TOKEN_URL, json={"access_token": "the-token", "token_type": "bearer"})
    client = _client()
    client.login("monitoring", "top-secret")
    return client


def test_login_requests_a_token_with_the_credentials_and_api_version(
    api: responses.RequestsMock,
) -> None:
    _logged_in_client(api)

    (call,) = api.calls
    assert call.request.headers["x-api-version"] == "1.3-rev0"
    assert parse_qs(str(call.request.body)) == {
        "grant_type": ["password"],
        "username": ["monitoring"],
        "password": ["top-secret"],
    }


def test_requests_after_login_use_the_token_as_bearer(api: responses.RequestsMock) -> None:
    client = _logged_in_client(api)
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})

    write_sections(client, [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert api.calls[-1].request.headers["Authorization"] == "Bearer the-token"


def test_failing_endpoint_does_not_stop_the_other_sections(
    api: responses.RequestsMock, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(
        f"{URL}/api/v1/broken", status=500, json={"errorCode": "UnknownError", "message": "boom"}
    )
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})

    write_sections(
        _client(),
        [
            ("veeam_broken", fetch_list("/api/v1/broken")),
            ("veeam_jobs", fetch_list("/api/v1/jobs")),
        ],
    )

    captured = capsys.readouterr()
    assert captured.out == "<<<veeam_jobs:sep(0)>>>\n"
    assert "HTTP 500: boom" in captured.err


def test_broken_response_on_a_data_endpoint_does_not_stop_the_other_sections(
    api: responses.RequestsMock, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(f"{URL}/api/v1/broken", body=requests.exceptions.ChunkedEncodingError("cut off"))
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})

    write_sections(
        _client(),
        [
            ("veeam_broken", fetch_list("/api/v1/broken")),
            ("veeam_jobs", fetch_list("/api/v1/jobs")),
        ],
    )

    captured = capsys.readouterr()
    assert captured.out == "<<<veeam_jobs:sep(0)>>>\n"
    assert "cut off" in captured.err


def test_rejected_session_on_a_data_endpoint_is_fatal(api: responses.RequestsMock) -> None:
    api.get(f"{URL}/api/v1/jobs", status=401, json={"errorCode": "AccessDenied", "message": "x"})

    with pytest.raises(AuthenticationFailed):
        write_sections(_client(), [("veeam_jobs", fetch_list("/api/v1/jobs"))])


def test_list_section_pages_until_complete_and_writes_one_item_per_line(
    api: responses.RequestsMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/jobs?skip=0",
        json={"data": [{"id": 1}, {"id": 2}], "pagination": {"total": 3}},
    )
    api.get(
        f"{URL}/api/v1/jobs?skip=2",
        json={"data": [{"id": 3}], "pagination": {"total": 3}},
    )

    write_sections(_client(), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert capsys.readouterr().out == ('<<<veeam_jobs:sep(0)>>>\n{"id": 1}\n{"id": 2}\n{"id": 3}\n')
    assert api.calls[-2].request.url == f"{URL}/api/v1/jobs?skip=0"
    assert api.calls[-1].request.url == f"{URL}/api/v1/jobs?skip=2"


def test_empty_page_before_reaching_total_does_not_hang(
    api: responses.RequestsMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/jobs?skip=0",
        json={"data": [], "pagination": {"total": 3}},
    )

    write_sections(_client(), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "returned an empty page before reaching 3 total items" in captured.err
    assert len(api.calls) == 1


def test_object_section_is_written_as_a_single_line(
    api: responses.RequestsMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(f"{URL}/api/v1/serverInfo", json={"name": "backup-server-01"})

    write_sections(_client(), [("veeam_vbr_server_info", fetch_object("/api/v1/serverInfo"))])

    assert (
        capsys.readouterr().out
        == '<<<veeam_vbr_server_info:sep(0)>>>\n{"name": "backup-server-01"}\n'
    )


def test_wrong_credentials_are_reported(api: responses.RequestsMock) -> None:
    api.post(
        TOKEN_URL,
        status=401,
        json={"errorCode": "AccessDenied", "message": "Authentication failed"},
    )

    with pytest.raises(AuthenticationFailed, match="Check the user name and password"):
        _client().login("monitoring", "wrong")


def test_unsupported_api_version_names_the_supported_ones(api: responses.RequestsMock) -> None:
    api.post(
        TOKEN_URL,
        status=400,
        json={
            "errorCode": "NotImplemented",
            "message": "Unsupported RESTAPI version. The following versions are supported: 1.1-rev0",
        },
    )

    with pytest.raises(UnsupportedApiVersion, match="versions are supported: 1.1-rev0"):
        _client().login("monitoring", "top-secret")


def test_unexpected_login_answer_reports_the_http_status(api: responses.RequestsMock) -> None:
    api.post(TOKEN_URL, status=500, json={"errorCode": "UnknownError", "message": "boom"})

    with pytest.raises(FatalError, match="failed with HTTP 500: boom"):
        _client().login("monitoring", "top-secret")


@pytest.mark.parametrize(
    "timeout",
    [
        pytest.param(requests.exceptions.ConnectTimeout("timed out"), id="connect"),
        pytest.param(requests.exceptions.ReadTimeout("timed out"), id="read"),
    ],
)
def test_timeout_is_reported_as_unreachable(
    api: responses.RequestsMock, timeout: requests.exceptions.Timeout
) -> None:
    api.post(TOKEN_URL, body=timeout)

    with pytest.raises(ServerUnreachable, match="did not answer within 30 seconds"):
        _client().login("monitoring", "top-secret")


def test_rejected_certificate_names_the_expected_host_name(api: responses.RequestsMock) -> None:
    api.post(TOKEN_URL, body=requests.exceptions.SSLError("certificate verify failed"))

    with pytest.raises(CertificateRejected, match="against the host name 'veeam-server'"):
        _client(cert_server_name="veeam-server").login("monitoring", "top-secret")


def test_tls_failure_without_verification_is_reported_as_handshake_failure(
    api: responses.RequestsMock,
) -> None:
    api.post(TOKEN_URL, body=requests.exceptions.SSLError("unsupported protocol"))

    with pytest.raises(CertificateRejected, match="TLS handshake with the Veeam backup server"):
        _client().login("monitoring", "top-secret")


def test_unreachable_server_is_reported_with_a_non_zero_exit_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        closed_port = sock.getsockname()[1]

    exit_code = main(
        [
            "--user",
            "monitoring",
            "--password",
            "top-secret",
            "--disable-cert-verification",
            "--port",
            str(closed_port),
            "127.0.0.1",
        ]
    )

    assert exit_code == 1
    assert "is unreachable" in capsys.readouterr().err
