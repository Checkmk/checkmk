#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import socket
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, quote

import pytest
import requests
import responses
import time_machine

from cmk.password_store.v1 import Secret
from cmk.plugins.veeam.special_agent.agent_veeam import (
    create_session,
    fetch_backups,
    fetch_list,
    fetch_object,
    fetch_restore_points,
    Fetched,
    FetchStrategy,
    JOB_OBJECT_NAMES_STORAGE_KEY,
    main,
    parse_arguments,
    SECTIONS,
    TerminateAgent,
    VeeamApi,
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


def _client(auth: VeeamAuth, storage: Storage) -> VeeamClient:
    return VeeamClient(_veeam_api(), auth, storage)


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
    assert call.request.headers["x-api-version"] == "1.3-rev1"
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

    write_sections(_client(auth, storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

    assert _bearer(api) == "Bearer first-access"


def test_the_token_of_the_previous_run_is_reused(
    api: responses.RequestsMock, storage: Storage
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.get(f"{URL}/api/v1/jobs", json={"data": [], "pagination": {"total": 0}})
    _auth(storage).authenticate()

    auth = _auth(storage)
    auth.authenticate()
    write_sections(_client(auth, storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

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
        write_sections(_client(auth, storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

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

    write_sections(_client(auth, storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

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

    write_sections(_client(auth, storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

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

    with pytest.raises(TerminateAgent, match="HTTP 500: boom"):
        write_sections(
            _client(_auth(storage), storage),
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
            _client(_auth(storage), storage),
            [
                ("veeam_broken", fetch_list("/api/v1/broken")),
                ("veeam_jobs", fetch_list("/api/v1/jobs")),
            ],
        )

    captured = capsys.readouterr()
    assert "<<<veeam_jobs:sep(0)>>>" not in captured.out


def test_access_denied_is_fatal(
    api: responses.RequestsMock, storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    # The API message ends with a period; the appended note must not double it up.
    api.get(
        f"{URL}/api/v1/replicas",
        status=HTTPStatus.FORBIDDEN,
        json={"errorCode": "Forbidden", "message": "Access denied."},
    )

    with pytest.raises(TerminateAgent) as excinfo:
        write_sections(
            _client(_auth(storage), storage), [("veeam_replicas", fetch_list("/api/v1/replicas"))]
        )

    message = str(excinfo.value)
    assert "HTTP 403" in message
    assert "lacks a role" in message
    assert ".." not in message
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
        write_sections(_client(auth, storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])


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

    write_sections(_client(_auth(storage), storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))])

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

    with pytest.raises(
        TerminateAgent, match="returned an empty page before reaching 3 total items"
    ):
        write_sections(
            _client(_auth(storage), storage), [("veeam_jobs", fetch_list("/api/v1/jobs"))]
        )

    assert capsys.readouterr().out == ""
    assert len(api.calls) == 1


def test_object_section_is_written_as_a_single_line(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(f"{URL}/api/v1/serverInfo", json={"name": "backup-server-01"})

    write_sections(
        _client(_auth(storage), storage),
        [("veeam_server_info", fetch_object("/api/v1/serverInfo"))],
    )

    assert (
        capsys.readouterr().out == '<<<veeam_server_info:sep(0)>>>\n{"name": "backup-server-01"}\n'
    )


def _piggyback_on(*hosts: str) -> FetchStrategy:
    def _fetch(_client: VeeamClient, name: str) -> Fetched:
        return Fetched(
            own=f"<<<{name}:sep(0)>>>\n",
            piggyback=dict.fromkeys(hosts, f"<<<{name}:sep(0)>>>\n{{}}\n"),
        )

    return _fetch


def test_write_sections_writes_each_piggyback_host_once(
    storage: Storage, capsys: pytest.CaptureFixture[str]
) -> None:
    write_sections(
        _client(_auth(storage), storage),
        [("section_a", _piggyback_on("host-1", "host-2")), ("section_b", _piggyback_on("host-1"))],
    )

    assert capsys.readouterr().out == (
        "<<<section_a:sep(0)>>>\n"
        "<<<section_b:sep(0)>>>\n"
        "<<<<host-1>>>>\n"
        "<<<section_a:sep(0)>>>\n{}\n"
        "<<<section_b:sep(0)>>>\n{}\n"
        "<<<<>>>>\n"
        "<<<<host-2>>>>\n"
        "<<<section_a:sep(0)>>>\n{}\n"
        "<<<<>>>>\n"
    )


def _restore_point(**overrides: object) -> dict[str, object]:
    return {
        "name": "ip-vm-1",
        "backupId": "backup-1",
        "creationTime": "2026-10-01T09:00:00+00:00",
        "type": "Increment",
        "malwareStatus": "Clean",
    } | overrides


def _restore_points_by_host(out: str) -> dict[str, dict[str, object]]:
    """The restore point record piggybacked onto each host."""
    records: dict[str, dict[str, object]] = {}
    lines = iter(out.splitlines())
    for line in lines:
        host = line.removeprefix("<<<<").removesuffix(">>>>")
        assert host and line == f"<<<<{host}>>>>"
        assert next(lines) == "<<<veeam_restore_points:sep(0)>>>"
        records[host] = json.loads(next(lines))
        assert next(lines) == "<<<<>>>>"
    return records


def _mock_backups(api: responses.RequestsMock, backup_ids: list[str]) -> None:
    api.get(
        f"{URL}/api/v1/backups?skip=0&limit=500",
        json={"data": [{"id": i} for i in backup_ids], "pagination": {"total": len(backup_ids)}},
    )


def _reduce_restore_points(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
    points: list[dict[str, object]],
    object_id_by_backup_id: dict[str, str] | None = None,
) -> list[object]:
    api.get(
        f"{URL}/api/v1/backupObjects?skip=0&limit=500",
        json={
            "data": [
                {
                    "id": "obj-1",
                    "name": "vm-1",
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
    backup_ids = {bid for p in points if isinstance(bid := p.get("backupId"), str)}
    resolved = object_id_by_backup_id or dict.fromkeys(backup_ids, "obj-1")
    _mock_backups(api, list(resolved))
    for backup_id, object_id in resolved.items():
        api.get(
            f"{URL}/api/v1/backups/{backup_id}/objects?skip=0&limit=500",
            json={"data": [{"id": object_id}], "pagination": {"total": 1}},
        )
    write_sections(
        _client(_auth(storage), storage), [("veeam_restore_points", fetch_restore_points())]
    )
    return list(_restore_points_by_host(capsys.readouterr().out).values())


def test_restore_points_are_reduced_to_one_record_per_machine(
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


def test_restore_points_with_unresolved_backup_id_are_not_joined(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _reduce_restore_points(
        api,
        storage,
        capsys,
        [_restore_point(backupId="other-backup")],
        object_id_by_backup_id={"other-backup": "some-other-object"},
    )
    assert isinstance(record, dict)
    assert record["lastRestorePoint"] is None
    assert record["malwareStatus"] is None


def test_restore_points_unsupported_backup_platform_is_not_joined(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/backupObjects?skip=0&limit=500",
        json={
            "data": [
                {
                    "id": "obj-1",
                    "name": "vm-1",
                    "platformName": "UnstructuredData",
                    "type": "Directory",
                    "restorePointsCount": 1,
                }
            ],
            "pagination": {"total": 1},
        },
    )
    points = [_restore_point(backupId="backup-1")]
    api.get(
        f"{URL}/api/v1/restorePoints?skip=0&limit=500",
        json={"data": points, "pagination": {"total": len(points)}},
    )
    _mock_backups(api, ["backup-1"])
    api.get(
        f"{URL}/api/v1/backups/backup-1/objects?skip=0&limit=500",
        status=HTTPStatus.BAD_REQUEST,
        json={"message": "Backup platform or job type are not supported"},
    )

    write_sections(
        _client(_auth(storage), storage), [("veeam_restore_points", fetch_restore_points())]
    )

    record = _restore_points_by_host(capsys.readouterr().out)["vm-1"]
    assert record["lastRestorePoint"] is None
    assert record["malwareStatus"] is None


def test_restore_points_multi_object_chain_matched_by_suffixed_name(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api.get(
        f"{URL}/api/v1/backupObjects?skip=0&limit=500",
        json={
            "data": [
                {
                    "id": "obj-1",
                    "name": "vm-1",
                    "platformName": "UnstructuredData",
                    "type": "Directory",
                    "restorePointsCount": 1,
                },
                {
                    "id": "obj-2",
                    "name": "vm-2",
                    "platformName": "UnstructuredData",
                    "type": "Directory",
                    "restorePointsCount": 1,
                },
            ],
            "pagination": {"total": 2},
        },
    )
    points = [
        _restore_point(
            name="vm-1 Id: 0",
            backupId="shared-backup",
        ),
        _restore_point(
            name="vm-2 Id: 0",
            backupId="shared-backup",
            creationTime="2026-10-01T10:00:00+00:00",
        ),
    ]
    api.get(
        f"{URL}/api/v1/restorePoints?skip=0&limit=500",
        json={"data": points, "pagination": {"total": len(points)}},
    )
    _mock_backups(api, ["shared-backup"])
    api.get(
        f"{URL}/api/v1/backups/shared-backup/objects?skip=0&limit=500",
        json={
            "data": [{"id": "obj-1", "name": "vm-1"}, {"id": "obj-2", "name": "vm-2"}],
            "pagination": {"total": 2},
        },
    )

    write_sections(
        _client(_auth(storage), storage), [("veeam_restore_points", fetch_restore_points())]
    )

    records = _restore_points_by_host(capsys.readouterr().out)
    assert records["vm-1"]["lastRestorePoint"] == {
        "creationTime": "2026-10-01T09:00:00+00:00",
        "type": "Increment",
        "malwareStatus": "Clean",
    }
    assert records["vm-2"]["lastRestorePoint"] == {
        "creationTime": "2026-10-01T10:00:00+00:00",
        "type": "Increment",
        "malwareStatus": "Clean",
    }


def _backup_object(
    object_id: str, points_count: int | None, **overrides: object
) -> dict[str, object]:
    return {
        "id": object_id,
        "name": "vm-1",
        "platformName": "VMware",
        "type": "VM",
        "restorePointsCount": points_count,
    } | overrides


def _run_restore_points(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
    backup_objects: list[dict[str, object]],
    points_by_object: dict[str, list[dict[str, object]]],
    chain_names: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    """Each object gets its own backup chain, named after the object's id. The object's
    name in its chain is taken from `chain_names`, if given."""
    _mock_backups(api, [str(o["id"]) for o in backup_objects])
    api.get(
        f"{URL}/api/v1/backupObjects?skip=0&limit=500",
        json={"data": backup_objects, "pagination": {"total": len(backup_objects)}},
    )
    points = [
        point | {"backupId": object_id}
        for object_id, object_points in points_by_object.items()
        for point in object_points
    ]
    api.get(
        f"{URL}/api/v1/restorePoints?skip=0&limit=500",
        json={"data": points, "pagination": {"total": len(points)}},
    )
    for object_id in (str(o["id"]) for o in backup_objects):
        name = (chain_names or {}).get(object_id)
        api.get(
            f"{URL}/api/v1/backups/{object_id}/objects?skip=0&limit=500",
            json={
                "data": [{"id": object_id} | ({} if name is None else {"name": name})],
                "pagination": {"total": 1},
            },
        )
    write_sections(
        _client(_auth(storage), storage), [("veeam_restore_points", fetch_restore_points())]
    )
    return _restore_points_by_host(capsys.readouterr().out)


def test_restore_points_of_one_machine_in_several_jobs_are_merged(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _run_restore_points(
        api,
        storage,
        capsys,
        [_backup_object("obj-1", 1), _backup_object("obj-2", 2)],
        {
            "obj-1": [_restore_point(type="Full", malwareStatus="Suspicious")],
            "obj-2": [
                _restore_point(type="Full"),
                _restore_point(creationTime="2026-10-01T10:00:00+00:00"),
            ],
        },
    ).values()
    assert record["restorePointsCount"] == 3
    assert isinstance(last := record["lastRestorePoint"], dict)
    assert last["creationTime"] == "2026-10-01T10:00:00+00:00"
    assert record["malwareStatus"] == "Suspicious"


def test_restore_points_are_piggybacked_onto_the_object_name_in_its_chain(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    records = _run_restore_points(
        api,
        storage,
        capsys,
        [_backup_object("obj-1", 1, name="172.31.26.65")],
        {"obj-1": [_restore_point()]},
        chain_names={"obj-1": "ip-172-31-26-65"},
    )
    assert list(records) == ["ip-172-31-26-65"]


def test_restore_points_object_without_points_lands_on_its_chain_host(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    records = _run_restore_points(
        api,
        storage,
        capsys,
        [
            _backup_object("obj-1", 1, name="172.31.26.65"),
            _backup_object("obj-2", 0, name="172.31.26.65"),
        ],
        {"obj-1": [_restore_point()]},
        chain_names={"obj-1": "ip-172-31-26-65", "obj-2": "ip-172-31-26-65"},
    )
    assert list(records) == ["ip-172-31-26-65"]
    assert records["ip-172-31-26-65"]["restorePointsCount"] == 1


def test_restore_points_without_host_name_are_dropped(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not _run_restore_points(
        api, storage, capsys, [_backup_object("obj-1", 1, name="")], {"obj-1": [_restore_point()]}
    )


def test_restore_points_type_is_taken_from_the_object_with_the_newest_point(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _run_restore_points(
        api,
        storage,
        capsys,
        [_backup_object("obj-1", 1, type="VM"), _backup_object("obj-2", 1, type="Directory")],
        {
            "obj-1": [_restore_point()],
            "obj-2": [_restore_point(creationTime="2026-10-01T10:00:00+00:00")],
        },
    ).values()
    assert record["type"] == "Directory"


def test_restore_points_count_is_unknown_if_one_merged_object_lacks_it(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (record,) = _run_restore_points(
        api,
        storage,
        capsys,
        [_backup_object("obj-1", 1), _backup_object("obj-2", None)],
        {"obj-1": [_restore_point()], "obj-2": [_restore_point()]},
    ).values()
    assert record["restorePointsCount"] is None


@pytest.mark.parametrize(
    "statuses, expected",
    [
        pytest.param(["Clean", "Infected", "Suspicious"], "Infected", id="worst wins"),
        pytest.param(["Infected", "SomethingNew"], "SomethingNew", id="unknown is worst"),
        pytest.param(["Infected", None], "Infected", id="missing is ignored"),
        pytest.param([None, None], None, id="none scanned"),
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


def _job(**overrides: object) -> dict[str, object]:
    job: dict[str, object] = {
        "id": "job-id-1",
        "name": "Daily_VM_Backup",
        "status": "Enabled",
        "sessionId": "session-1",
        "lastRun": "2026-09-29T00:00:00+00:00",
    }
    job.update(overrides)
    return job


def _task(**overrides: object) -> dict[str, object]:
    task: dict[str, object] = {
        "name": "vm-1",
        "sessionId": "session-1",
        "sessionType": "BackupJob",
        "creationTime": "2026-09-29T01:00:00+00:00",
        "state": "Stopped",
        "result": {"result": "Success"},
    }
    task.update(overrides)
    return task


def _mock_jobs(
    api: responses.RequestsMock,
    jobs: list[dict[str, object]],
) -> None:
    api.get(
        f"{URL}/api/v1/jobs/states?skip=0",
        json={"data": jobs, "pagination": {"total": len(jobs)}},
    )


def _mock_tasks(
    api: responses.RequestsMock,
    created_after: str,
    tasks: list[dict[str, object]],
) -> None:
    query = f"skip=0&typeFilter=Backup&createdAfterFilter={quote(created_after)}"
    api.get(
        f"{URL}/api/v1/taskSessions?{query}",
        json={"data": tasks, "pagination": {"total": len(tasks)}},
    )


def _mock_session_with_no_objects(api: responses.RequestsMock, session_id: str) -> None:
    """A session with no `resourceId`: `_resolve_job_object_names` resolves no
    object for its job, so it never triggers the single-object session fallback."""
    api.get(f"{URL}/api/v1/sessions/{session_id}", json={})


def _mock_session_and_objects(
    api: responses.RequestsMock,
    session_id: str,
    object_names: list[str],
    resource_id: str = "resource-1",
) -> None:
    api.get(
        f"{URL}/api/v1/sessions/{session_id}",
        json={"resourceId": resource_id, "state": "Stopped"},
    )
    api.get(
        f"{URL}/api/v1/backups/{resource_id}/objects?skip=0",
        json={
            "data": [{"id": f"object-{n}", "name": n} for n in object_names],
            "pagination": {"total": len(object_names)},
        },
    )


def test_fetch_backups_resolves_the_job_name_via_the_session_join(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["vm-1"])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task()])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    header, *lines = capsys.readouterr().out.splitlines()
    assert header == "<<<<vm-1>>>>"
    assert lines[0] == "<<<veeam_backups:sep(0)>>>"
    (record,) = (json.loads(line) for line in lines[1:-1])
    assert record["jobName"] == "Daily_VM_Backup"
    assert lines[-1] == "<<<<>>>>"


def test_fetch_backups_window_uses_the_earliest_last_run_across_jobs(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(
        api,
        [
            _job(
                name="Daily_VM_Backup", sessionId="session-1", lastRun="2026-09-29T00:00:00+00:00"
            ),
            _job(
                name="Weekly_VM_Backup",
                sessionId="session-2",
                lastRun="2026-09-20T00:00:00+00:00",
            ),
        ],
    )
    _mock_session_with_no_objects(api, "session-1")
    _mock_session_with_no_objects(api, "session-2")
    _mock_tasks(api, "2026-09-20T00:00:00+00:00", [])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""


def test_fetch_backups_no_job_has_ever_run_skips_the_task_fetch_entirely(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job(lastRun=None)])
    _mock_session_with_no_objects(api, "session-1")

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""
    assert all("taskSessions" not in str(call.request.url) for call in api.calls)


def test_fetch_backups_ignores_disabled_jobs(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(
        api,
        [
            _job(),
            _job(
                id="job-id-2",
                name="Disabled_VM_Backup",
                status="Disabled",
                sessionId="session-2",
                lastRun="2026-09-01T00:00:00+00:00",
            ),
        ],
    )
    _mock_session_and_objects(api, "session-1", ["vm-1"])
    # The window starts at the enabled job's last run, not at the disabled job's.
    _mock_tasks(
        api,
        "2026-09-29T00:00:00+00:00",
        [_task(), _task(name="vm-2", sessionId="session-2")],
    )

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    output = capsys.readouterr().out
    assert "<<<<vm-1>>>>" in output
    assert "vm-2" not in output


def test_fetch_backups_task_with_unmatched_session_is_dropped(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job(sessionId="session-current")])
    _mock_session_with_no_objects(api, "session-current")
    _mock_tasks(
        api,
        "2026-09-29T00:00:00+00:00",
        [_task(sessionId="session-old")],
    )

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""


def test_fetch_backups_task_with_non_backupjob_session_type_is_dropped(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # sessionTypeFilter=BackupJob is not sent server-side (it silently matches
    # nothing on VBR 13.0.3.63); this is filtered client-side instead.
    _mock_jobs(api, [_job()])
    _mock_session_with_no_objects(api, "session-1")
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task(sessionType="AgentDiscovery")])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""


def test_fetch_backups_relabels_a_single_object_job_task_to_the_resolved_name(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The task's own `name` uses a different naming convention than the resolved
    # object name for some platforms (e.g. a Linux agent's raw IP vs. its hostname).
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["ip-172-31-26-65"])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task(name="172.31.26.65")])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    header, *_lines = capsys.readouterr().out.splitlines()
    assert header == "<<<<ip-172-31-26-65>>>>"


def test_fetch_backups_multi_object_job_matches_by_name_and_drops_the_rest(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["vm-1", "vm-2"])
    _mock_tasks(
        api,
        "2026-09-29T00:00:00+00:00",
        [_task(name="vm-1"), _task(name="vm-3", id="unmatched")],
    )

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    output = capsys.readouterr().out
    assert "<<<<vm-1>>>>" in output
    assert "vm-2" not in output
    assert "vm-3" not in output
    assert "unmatched" not in output


def test_fetch_backups_falls_back_to_the_session_for_a_single_object_job_with_no_task(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    api.get(
        f"{URL}/api/v1/sessions/session-1",
        json={
            "resourceId": "resource-1",
            # 1 day, 1 hour, 2 minutes, 3 seconds: exercises the days component too.
            "creationTime": "2026-09-29T00:00:00+00:00",
            "endTime": "2026-09-30T01:02:03+00:00",
            "state": "Stopped",
            "result": {"result": "Success"},
        },
    )
    api.get(
        f"{URL}/api/v1/backups/resource-1/objects?skip=0",
        json={"data": [{"id": "object-vm-1", "name": "vm-1"}], "pagination": {"total": 1}},
    )
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    header, *lines = capsys.readouterr().out.splitlines()
    assert header == "<<<<vm-1>>>>"
    (record,) = (json.loads(line) for line in lines[1:-1])
    assert record["jobName"] == "Daily_VM_Backup"
    assert record["state"] == "Stopped"
    assert record["result"] == {"result": "Success"}
    assert record["progress"]["duration"] == "1.01:02:03"


def test_fetch_backups_session_404_skips_just_that_job(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    api.get(
        f"{URL}/api/v1/sessions/session-1",
        status=HTTPStatus.NOT_FOUND,
        json={"message": "Session not found"},
    )
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""


def test_fetch_backups_objects_400_skips_just_that_job(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    api.get(
        f"{URL}/api/v1/sessions/session-1",
        json={"resourceId": "resource-1", "state": "Stopped"},
    )
    api.get(
        f"{URL}/api/v1/backups/resource-1/objects?skip=0",
        status=HTTPStatus.BAD_REQUEST,
        json={"message": "Backup platform or job type are not supported"},
    )
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""


def test_fetch_backups_session_missing_state_keeps_the_jobs_tasks(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    api.get(f"{URL}/api/v1/sessions/session-1", json={"resourceId": "resource-1"})
    api.get(
        f"{URL}/api/v1/backups/resource-1/objects?skip=0",
        json={"data": [{"id": "object-vm-1", "name": "vm-1"}], "pagination": {"total": 1}},
    )
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task()])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    header, *lines = capsys.readouterr().out.splitlines()
    assert header == "<<<<vm-1>>>>"
    (record,) = (json.loads(line) for line in lines[1:-1])
    assert record["state"] == "Stopped"
    assert record["result"] == {"result": "Success"}


def test_fetch_backups_session_missing_state_writes_no_fallback_record(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    api.get(f"{URL}/api/v1/sessions/session-1", json={"resourceId": "resource-1"})
    api.get(
        f"{URL}/api/v1/backups/resource-1/objects?skip=0",
        json={"data": [{"id": "object-vm-1", "name": "vm-1"}], "pagination": {"total": 1}},
    )
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    assert capsys.readouterr().out == ""


def test_fetch_backups_cached_session_feeds_the_fallback_task_on_a_later_run(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    api.get(
        f"{URL}/api/v1/sessions/session-1",
        json={
            "resourceId": "resource-1",
            "creationTime": "2026-09-29T00:00:00+00:00",
            "endTime": "2026-09-29T01:02:03+00:00",
            "state": "Stopped",
            "result": {"result": "Success"},
        },
    )
    api.get(
        f"{URL}/api/v1/backups/resource-1/objects?skip=0",
        json={"data": [{"id": "object-vm-1", "name": "vm-1"}], "pagination": {"total": 1}},
    )
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task()])
    client = _client(_auth(storage), storage)
    write_sections(client, [("veeam_backups", fetch_backups)])
    capsys.readouterr()

    # Second run: the job's session is unchanged (cache hit), but it now has no
    # task, so `_session_fallback_task` must build its record from the cached
    # `_SessionInfo`, round-tripped through `model_dump()`/`populate_by_name`.
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])
    write_sections(client, [("veeam_backups", fetch_backups)])
    output = capsys.readouterr().out

    header, *lines = output.splitlines()
    assert header == "<<<<vm-1>>>>"
    (record,) = (json.loads(line) for line in lines[1:-1])
    assert record["endTime"] == "2026-09-29T01:02:03+00:00"
    assert record["result"] == {"result": "Success"}


def test_fetch_backups_reuses_cached_object_names_for_an_unchanged_session(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["vm-1"])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task()])
    client = _client(_auth(storage), storage)

    write_sections(client, [("veeam_backups", fetch_backups)])
    capsys.readouterr()
    calls_before_second_run = len(api.calls)

    write_sections(client, [("veeam_backups", fetch_backups)])
    output = capsys.readouterr().out

    assert "<<<<vm-1>>>>" in output
    new_calls = api.calls[calls_before_second_run:]
    assert not any(
        "/api/v1/sessions/" in (call.request.url or "")
        or "/api/v1/backups/resource" in (call.request.url or "")
        for call in new_calls
    )


def test_fetch_backups_refetches_object_names_when_the_session_changes(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["vm-1"])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task()])
    client = _client(_auth(storage), storage)

    write_sections(client, [("veeam_backups", fetch_backups)])
    capsys.readouterr()

    # The job ran again: a new sessionId, resolving to a different object name.
    _mock_jobs(api, [_job(sessionId="session-2")])
    _mock_session_and_objects(api, "session-2", ["vm-1-renamed"])
    _mock_tasks(
        api,
        "2026-09-29T00:00:00+00:00",
        [_task(sessionId="session-2", name="vm-1-renamed")],
    )

    write_sections(client, [("veeam_backups", fetch_backups)])
    output = capsys.readouterr().out

    assert "<<<<vm-1-renamed>>>>" in output
    assert "<<<<vm-1>>>>" not in output


def test_fetch_backups_drops_a_job_no_longer_present_from_the_cache(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["vm-1"])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [_task()])
    client = _client(_auth(storage), storage)

    write_sections(client, [("veeam_backups", fetch_backups)])
    capsys.readouterr()
    assert "job-id-1" in storage.read(JOB_OBJECT_NAMES_STORAGE_KEY, "{}")

    _mock_jobs(api, [])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])

    write_sections(client, [("veeam_backups", fetch_backups)])
    capsys.readouterr()

    assert storage.read(JOB_OBJECT_NAMES_STORAGE_KEY, "{}") == "{}"


def test_fetch_backups_only_caches_a_session_once_it_has_stopped(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The first run catches the job mid-backup; the session is cached only once
    # it later shows up as "Stopped" under the same sessionId, not before.
    api.get(
        f"{URL}/api/v1/sessions/session-1",
        json={"resourceId": "resource-1", "state": "Working"},
    )
    api.get(
        f"{URL}/api/v1/sessions/session-1",
        json={
            "resourceId": "resource-1",
            "state": "Stopped",
            "endTime": "2026-09-29T01:02:03+00:00",
            "result": {"result": "Success"},
        },
    )
    api.get(
        f"{URL}/api/v1/backups/resource-1/objects?skip=0",
        json={"data": [{"id": "object-vm-1", "name": "vm-1"}], "pagination": {"total": 1}},
    )
    _mock_jobs(api, [_job()])
    _mock_tasks(api, "2026-09-29T00:00:00+00:00", [])
    client = _client(_auth(storage), storage)

    write_sections(client, [("veeam_backups", fetch_backups)])
    capsys.readouterr()
    assert storage.read(JOB_OBJECT_NAMES_STORAGE_KEY, "{}") == "{}"

    write_sections(client, [("veeam_backups", fetch_backups)])
    output = capsys.readouterr().out

    header, *lines = output.splitlines()
    assert header == "<<<<vm-1>>>>"
    (record,) = (json.loads(line) for line in lines[1:-1])
    assert record["state"] == "Stopped"
    assert record["result"] == {"result": "Success"}


def test_fetch_backups_keeps_the_newest_task_per_object_and_job(
    api: responses.RequestsMock,
    storage: Storage,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_jobs(api, [_job()])
    _mock_session_and_objects(api, "session-1", ["vm-1"])
    _mock_tasks(
        api,
        "2026-09-29T00:00:00+00:00",
        [
            _task(id="older", creationTime="2026-09-29T01:00:00+00:00"),
            _task(id="newer", creationTime="2026-09-29T02:00:00+00:00"),
        ],
    )

    write_sections(_client(_auth(storage), storage), [("veeam_backups", fetch_backups)])

    output = capsys.readouterr().out
    assert '"id": "newer"' in output
    assert '"id": "older"' not in output


def test_wrong_credentials_are_reported(api: responses.RequestsMock, storage: Storage) -> None:
    api.post(
        TOKEN_URL,
        status=HTTPStatus.UNAUTHORIZED,
        json={"errorCode": "AccessDenied", "message": "Authentication failed"},
    )

    with pytest.raises(TerminateAgent, match="Check the user name and password"):
        _auth(storage).authenticate()


def test_unsupported_api_version_names_the_required_and_the_supported_versions(
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

    with pytest.raises(
        TerminateAgent,
        match=r"13\.0\.1\.180 or later is required .*versions are supported: 1\.1-rev0",
    ):
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


_MINIMAL_ARGV = ["--user", "u", "--password", "p", "--disable-cert-verification"]


def test_sections_default_to_every_known_section() -> None:
    args = parse_arguments([*_MINIMAL_ARGV, "veeam.example.com"])

    assert args.sections == [name for name, _ in SECTIONS]


def test_sections_can_be_restricted_to_a_comma_separated_subset() -> None:
    args = parse_arguments(
        [*_MINIMAL_ARGV, "--sections", "veeam_license,veeam_proxies", "veeam.example.com"]
    )

    assert args.sections == ["veeam_license", "veeam_proxies"]


def test_an_unknown_section_is_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_arguments([*_MINIMAL_ARGV, "--sections", "veeam_does_not_exist", "veeam.example.com"])


@pytest.mark.usefixtures("storage")
def test_main_fetches_only_the_selected_sections(
    api: responses.RequestsMock, capsys: pytest.CaptureFixture[str]
) -> None:
    api.post(TOKEN_URL, json=_token("first"))
    api.get(f"{URL}/api/v1/jobs/states", json={"data": [], "pagination": {"total": 0}})

    exit_code = main([*_MINIMAL_ARGV, "--sections", "veeam_backup_jobs", "veeam.example.com"])

    assert exit_code == 0
    assert capsys.readouterr().out == "<<<veeam_backup_jobs:sep(0)>>>\n"
    assert all(call.request.url != f"{URL}/api/v1/serverInfo" for call in api.calls)
