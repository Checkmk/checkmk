#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import socket
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs

import pytest
import requests
import responses
import time_machine

from cmk.password_store.v1 import Secret
from cmk.plugins.veeam.special_agent.agent_veeam import (
    AccessDenied,
    create_session,
    empty_on_access_denied,
    fetch_list,
    fetch_list_piggyback,
    fetch_object,
    fetch_restore_points,
    main,
    TerminateAgent,
    VeeamApi,
    VeeamApiError,
    VeeamAuth,
    VeeamClient,
    write_sections,
)
from cmk.server_side_programs.v1 import Storage

URL = "https://veeam.example.com:9419"
TOKEN_URL = f"{URL}/api/oauth2/token"


@pytest.fixture(name="api")
def _api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as api:
        yield api


@pytest.fixture(name="storage")
def _storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Storage:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    return Storage("veeam", host="veeam.example.com")


def _veeam_api(cert_server_name: str | None = None) -> VeeamApi:
    return VeeamApi(
        create_session(URL, cert_server_name), URL, cert_server_name=cert_server_name, timeout=30
    )


def _auth(
    storage: Storage, cert_server_name: str | None = None, user: str = "monitoring"
) -> VeeamAuth:
    """The token handling as created by one run of the agent."""
    return VeeamAuth(
        _veeam_api(cert_server_name), storage=storage, user=user, password=Secret("top-secret")
    )


def _client(auth: VeeamAuth) -> VeeamClient:
    return VeeamClient(_veeam_api(), auth)


def _token(name: str) -> dict[str, object]:
    return {
        "access_token": f"{name}-access",
        "refresh_token": f"{name}-refresh",
        "token_type": "bearer",
        "expires_in": 900,
    }


def _token_requests(api: responses.RequestsMock) -> list[dict[str, list[str]]]:
    return [parse_qs(str(call.request.body)) for call in api.calls if call.request.url == TOKEN_URL]


def _bearer(api: responses.RequestsMock) -> str:
    return str(api.calls[-1].request.headers["Authorization"])


def test_authenticate_requests_a_token_with_the_credentials_and_api_version(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))

    _auth(storage).authenticate()

    (call,) = api.calls
    assert call.request.headers["x-api-version"] == "1.3-rev0"
    assert parse_qs(str(call.request.body)) == {
        "grant_type": ["password"],
        "username": ["monitoring"],
        "password": ["top-secret"],
    }


def test_requests_after_authentication_use_the_token_as_bearer(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})
    auth = _auth(storage)
    auth.authenticate()

    write_sections(_client(auth), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert _bearer(api) == "Bearer first-access"


def test_the_token_of_the_previous_run_is_reused(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})
    _auth(storage).authenticate()

    auth = _auth(storage)
    auth.authenticate()
    write_sections(_client(auth), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert len(_token_requests(api)) == 1
    assert _bearer(api) == "Bearer first-access"


def test_a_token_about_to_expire_is_refreshed_at_start(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.post(TOKEN_URL, json=_token("second"))
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})
    with time_machine.travel(0, tick=False) as traveller:
        _auth(storage).authenticate()
        traveller.shift(900 - 30)

        auth = _auth(storage)
        auth.authenticate()
        write_sections(_client(auth), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert _token_requests(api)[-1] == {
        "grant_type": ["refresh_token"],
        "refresh_token": ["first-refresh"],
    }
    assert _bearer(api) == "Bearer second-access"


def test_a_rejected_refresh_token_falls_back_to_the_password(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.post(
        TOKEN_URL,
        status=HTTPStatus.UNAUTHORIZED,
        json={"errorCode": "AccessDenied", "message": "used"},
    )
    api.post(TOKEN_URL, json=_token("second"))
    with time_machine.travel(0, tick=False) as traveller:
        _auth(storage).authenticate()
        traveller.shift(900)

        _auth(storage).authenticate()

    assert [r["grant_type"] for r in _token_requests(api)] == [
        ["password"],
        ["refresh_token"],
        ["password"],
    ]


def test_the_token_of_another_user_is_not_reused(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    _auth(storage, user="monitoring").authenticate()

    _auth(storage, user="other").authenticate()

    assert [r["username"] for r in _token_requests(api)] == [["monitoring"], ["other"]]


def test_a_token_rejected_mid_run_is_renewed_and_the_request_retried(
    api: responses.RequestsMock, storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.post(TOKEN_URL, json=_token("second"))
    api.get(
        f"{URL}/api/v1/jobs",
        status=HTTPStatus.UNAUTHORIZED,
        json={"errorCode": "ExpiredToken", "message": "x"},
    )
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})
    auth = _auth(storage)
    auth.authenticate()

    write_sections(_client(auth), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert _token_requests(api)[-1]["grant_type"] == ["refresh_token"]
    assert _bearer(api) == "Bearer second-access"
    assert "<<<veeam_jobs:sep(0)>>>" in capsys.readouterr().out


def test_the_token_request_does_not_send_the_rejected_token(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.post(TOKEN_URL, json=_token("second"))
    api.get(
        f"{URL}/api/v1/jobs",
        status=HTTPStatus.UNAUTHORIZED,
        json={"errorCode": "ExpiredToken", "message": "x"},
    )
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})
    auth = _auth(storage)
    auth.authenticate()

    write_sections(_client(auth), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    refresh = [call.request for call in api.calls if call.request.url == TOKEN_URL][-1]
    assert "Authorization" not in refresh.headers


def test_failing_endpoint_does_stop_the_other_sections(
    api: responses.RequestsMock, storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(
        f"{URL}/api/v1/broken",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        json={"errorCode": "UnknownError", "message": "boom"},
    )
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})

    with pytest.raises(VeeamApiError, match="HTTP 500: boom"):
        write_sections(
            _client(_auth(storage)),
            [
                ("veeam_broken", fetch_list("/api/v1/broken")),
                ("veeam_jobs", fetch_list("/api/v1/jobs")),
            ],
        )

    captured = capsys.readouterr()
    assert "<<<veeam_jobs:sep(0)>>>" not in captured.out


def test_broken_response_on_a_data_endpoint_does_stop_the_other_sections(
    api: responses.RequestsMock, storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(f"{URL}/api/v1/broken", body=requests.exceptions.ChunkedEncodingError("cut off"))
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})

    with pytest.raises(requests.exceptions.ChunkedEncodingError, match="cut off"):
        write_sections(
            _client(_auth(storage)),
            [
                ("veeam_broken", fetch_list("/api/v1/broken")),
                ("veeam_jobs", fetch_list("/api/v1/jobs")),
            ],
        )

    captured = capsys.readouterr()
    assert "<<<veeam_jobs:sep(0)>>>" not in captured.out


def test_access_denied_on_a_role_restricted_endpoint_writes_an_empty_section(
    api: responses.RequestsMock, storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(
        f"{URL}/api/v1/replicas",
        status=HTTPStatus.FORBIDDEN,
        json={"errorCode": "Forbidden", "message": "denied"},
    )

    write_sections(
        _client(_auth(storage)),
        [("veeam_replicas", empty_on_access_denied(fetch_list("/api/v1/replicas")))],
    )

    captured = capsys.readouterr()
    assert captured.out == "<<<veeam_replicas:sep(0)>>>\n"
    assert captured.err == ""


def test_access_denied_on_an_unrestricted_endpoint_is_raised(
    api: responses.RequestsMock, storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(
        f"{URL}/api/v1/jobs",
        status=HTTPStatus.FORBIDDEN,
        json={"errorCode": "Forbidden", "message": "denied"},
    )

    with pytest.raises(AccessDenied, match="HTTP 403: denied"):
        write_sections(_client(_auth(storage)), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert capsys.readouterr().out == ""


def test_session_rejected_again_after_renewal_is_fatal(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.get(
        f"{URL}/api/v1/jobs",
        status=HTTPStatus.UNAUTHORIZED,
        json={"errorCode": "AccessDenied", "message": "x"},
    )
    auth = _auth(storage)
    auth.authenticate()

    with pytest.raises(TerminateAgent, match="rejected the session"):
        write_sections(_client(auth), [("veeam_jobs", fetch_list("/api/v1/jobs"))])


def test_list_section_pages_until_complete_and_writes_one_item_per_line(
    api: responses.RequestsMock,
    storage: Storage,
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

    write_sections(_client(_auth(storage)), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert capsys.readouterr().out == ('<<<veeam_jobs:sep(0)>>>\n{"id": 1}\n{"id": 2}\n{"id": 3}\n')
    assert api.calls[-2].request.url == f"{URL}/api/v1/jobs?skip=0"
    assert api.calls[-1].request.url == f"{URL}/api/v1/jobs?skip=2"


def test_empty_page_before_reaching_total_does_not_hang(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/jobs?skip=0",
        json={"data": [], "pagination": {"total": 3}},
    )

    with pytest.raises(RuntimeError, match="returned an empty page before reaching 3 total items"):
        write_sections(_client(_auth(storage)), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert capsys.readouterr().out == ""
    assert len(api.calls) == 1


def test_object_section_is_written_as_a_single_line(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(f"{URL}/api/v1/serverInfo", json={"name": "backup-server-01"})

    write_sections(
        _client(_auth(storage)), [("veeam_server_info", fetch_object("/api/v1/serverInfo"))]
    )

    assert (
        capsys.readouterr().out == '<<<veeam_server_info:sep(0)>>>\n{"name": "backup-server-01"}\n'
    )


def test_piggyback_section_groups_items_by_name(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/taskSessions?skip=0",
        json={
            "data": [
                {"name": "web-server-01", "jobName": "Daily"},
                {"name": "db-server-02", "jobName": "Daily"},
                {"name": "web-server-01", "jobName": "Weekly"},
            ],
            "pagination": {"total": 3},
        },
    )

    write_sections(
        _client(_auth(storage)), [("veeam_backups", fetch_list_piggyback("/api/v1/taskSessions"))]
    )

    assert capsys.readouterr().out == (
        "<<<<web-server-01>>>>\n"
        "<<<veeam_backups:sep(0)>>>\n"
        '{"name": "web-server-01", "jobName": "Daily"}\n'
        '{"name": "web-server-01", "jobName": "Weekly"}\n'
        "<<<<>>>>\n"
        "<<<<db-server-02>>>>\n"
        "<<<veeam_backups:sep(0)>>>\n"
        '{"name": "db-server-02", "jobName": "Daily"}\n'
        "<<<<>>>>\n"
    )


def test_piggyback_section_drops_items_with_no_name(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/taskSessions?skip=0",
        json={
            "data": [
                {"jobName": "Daily"},
                {"name": "web-server-01", "jobName": "Daily"},
            ],
            "pagination": {"total": 2},
        },
    )

    write_sections(
        _client(_auth(storage)), [("veeam_backups", fetch_list_piggyback("/api/v1/taskSessions"))]
    )

    assert capsys.readouterr().out == (
        "<<<<web-server-01>>>>\n"
        "<<<veeam_backups:sep(0)>>>\n"
        '{"name": "web-server-01", "jobName": "Daily"}\n'
        "<<<<>>>>\n"
    )


def _restore_point(**overrides: object) -> dict[str, object]:
    return {
        "name": "vm-1",
        "platformId": "p",
        "creationTime": "2026-10-01T09:00:00+00:00",
        "type": "Increment",
        "malwareStatus": "Clean",
    } | overrides


def _reduce_restore_points(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
    points: list[dict[str, object]],
) -> list[object]:
    api.get(
        f"{URL}/api/v1/backupObjects?skip=0&limit=500",
        json={
            "data": [
                {
                    "id": "obj-1",
                    "name": "vm-1",
                    "platformId": "p",
                    "platformName": "VMware",
                    "type": "VM",
                    "restorePointsCount": len(points),
                }
            ],
            "pagination": {"total": 1},
        },
    )
    api.get(
        f"{URL}/api/v1/restorePoints?skip=0&limit=500",
        json={"data": points, "pagination": {"total": len(points)}},
    )
    write_sections(_client(_auth(storage)), [("veeam_restore_points", fetch_restore_points())])
    header, *lines = capsys.readouterr().out.splitlines()
    assert header == "<<<veeam_restore_points:sep(0)>>>"
    return [json.loads(line) for line in lines]


def test_restore_points_are_reduced_to_one_record_per_backup_object(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _reduce_restore_points(
        api,
        storage,
        capsys,
        [_restore_point(type="Full"), _restore_point(creationTime="2026-10-01T10:00:00+00:00")],
    ) == [
        {
            "name": "vm-1",
            "platformName": "VMware",
            "type": "VM",
            "restorePointsCount": 2,
            "lastRestorePoint": {
                "creationTime": "2026-10-01T10:00:00+00:00",
                "type": "Increment",
                "malwareStatus": "Clean",
            },
            "malwareStatus": "Clean",
        }
    ]


def test_restore_points_newest_is_compared_across_utc_offsets(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _reduce_restore_points(
        api,
        storage,
        capsys,
        [
            _restore_point(creationTime="2026-10-01T10:00:00+02:00", type="Full"),
            _restore_point(creationTime="2026-10-01T09:00:00+00:00", type="Increment"),
        ],
    )
    assert isinstance(record, dict)
    assert record["lastRestorePoint"]["type"] == "Increment"


def test_restore_points_with_unparsable_time_are_not_the_newest(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _reduce_restore_points(
        api,
        storage,
        capsys,
        [_restore_point(creationTime="garbage", type="Full"), _restore_point(type="Increment")],
    )
    assert isinstance(record, dict)
    assert record["lastRestorePoint"]["type"] == "Increment"


def test_restore_points_on_another_platform_are_not_joined(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _reduce_restore_points(
        api, storage, capsys, [_restore_point(platformId="other-platform")]
    )
    assert isinstance(record, dict)
    assert record["lastRestorePoint"] is None
    assert record["malwareStatus"] is None


@pytest.mark.parametrize(
    "statuses, expected",
    [
        pytest.param(["Clean", "Infected", "Suspicious"], "Infected", id="worst wins"),
        pytest.param(["Infected", "SomethingNew"], "SomethingNew", id="unknown is worst"),
        pytest.param(["Infected", None], None, id="missing is worst"),
    ],
)
def test_restore_points_malware_status_rollup(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
    statuses: list[str | None],
    expected: str | None,
) -> None:
    (record,) = _reduce_restore_points(
        api, storage, capsys, [_restore_point(malwareStatus=status) for status in statuses]
    )
    assert isinstance(record, dict)
    assert record["malwareStatus"] == expected


def test_wrong_credentials_are_reported(api: responses.RequestsMock, storage: Storage) -> None:
    api.post(
        TOKEN_URL,
        status=HTTPStatus.UNAUTHORIZED,
        json={"errorCode": "AccessDenied", "message": "Authentication failed"},
    )

    with pytest.raises(TerminateAgent, match="Check the user name and password"):
        _auth(storage).authenticate()


def test_unsupported_api_version_names_the_supported_ones(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(
        TOKEN_URL,
        status=HTTPStatus.BAD_REQUEST,
        json={
            "errorCode": "NotImplemented",
            "message": "Unsupported RESTAPI version. The following versions are supported: 1.1-rev0",
        },
    )

    with pytest.raises(TerminateAgent, match="versions are supported: 1.1-rev0"):
        _auth(storage).authenticate()


def test_unexpected_login_answer_reports_the_http_status(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(
        TOKEN_URL,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        json={"errorCode": "UnknownError", "message": "boom"},
    )

    with pytest.raises(TerminateAgent, match="failed with HTTP 500: boom"):
        _auth(storage).authenticate()


@pytest.mark.parametrize(
    "timeout",
    [
        pytest.param(requests.exceptions.ConnectTimeout("timed out"), id="connect"),
        pytest.param(requests.exceptions.ReadTimeout("timed out"), id="read"),
    ],
)
def test_timeout_is_reported_as_unreachable(
    api: responses.RequestsMock, storage: Storage, timeout: requests.exceptions.Timeout
) -> None:
    api.post(TOKEN_URL, body=timeout)

    with pytest.raises(TerminateAgent, match="did not answer within 30 seconds"):
        _auth(storage).authenticate()


def test_rejected_certificate_names_the_expected_host_name(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, body=requests.exceptions.SSLError("certificate verify failed"))

    with pytest.raises(TerminateAgent, match="against the host name 'veeam-server'"):
        _auth(storage, cert_server_name="veeam-server").authenticate()


def test_tls_failure_without_verification_is_reported_as_handshake_failure(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, body=requests.exceptions.SSLError("unsupported protocol"))

    with pytest.raises(TerminateAgent, match="TLS handshake with the Veeam backup server"):
        _auth(storage).authenticate()


@pytest.mark.usefixtures("storage")
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
