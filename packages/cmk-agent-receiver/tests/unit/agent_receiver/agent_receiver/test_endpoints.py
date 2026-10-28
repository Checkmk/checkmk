#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io
import os
import stat
import zlib
from collections.abc import MutableMapping
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4
from zlib import compress

import httpx2
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import UUID4
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from cmk.agent_receiver.agent_receiver import decompression
from cmk.agent_receiver.agent_receiver.checkmk_rest_api import (
    CMKEdition,
    RegisterResponse,
)
from cmk.agent_receiver.agent_receiver.models import (
    ConnectionMode,
    R4RStatus,
    RequestForRegistration,
)
from cmk.agent_receiver.agent_receiver.utils import R4R
from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.lib.config import Config, get_config
from cmk.agent_receiver.lib.mtls_auth_validator import (
    INJECTED_ISSUER_HEADER,
    INJECTED_SERIAL_HEADER,
    INJECTED_UUID_HEADER,
)
from cmk.testlib.agent_receiver.certs import (
    agent_ca_common_name,
    generate_csr_pair,
    UNREVOKED_SERIAL_NUMBER,
)


@pytest.fixture(name="symlink_push_host")
def fixture_symlink_push_host(
    tmp_path: Path,
    uuid: UUID4,
    setup_site_context: Config,
) -> None:
    _symlink_push_host(setup_site_context, tmp_path, uuid)


def _symlink_push_host(
    config: Config,
    tmp_path: Path,
    uuid: UUID4,
) -> None:
    source = config.agent_output_dir / str(uuid)
    (target_dir := tmp_path / "push-agent" / "hostname").mkdir(parents=True)
    source.symlink_to(target_dir)


@pytest.fixture(name="serialized_csr", scope="session")
def fixture_serialized_csr(uuid: UUID4) -> str:
    _key, csr = generate_csr_pair(str(uuid), 1024)
    return serialize_to_pem(csr)


def test_register_existing_ok(
    tmp_path: Path,
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    async def rest_api_register_mock(*_args: object, **_kwargs: object) -> RegisterResponse:
        _symlink_push_host(get_config(), tmp_path, uuid)
        return RegisterResponse(connection_mode=ConnectionMode.PULL)

    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.register",
        rest_api_register_mock,
    )
    response = client.post(
        "/register_existing",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "myhost",
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert set(response.json()) == {
        "root_cert",
        "agent_cert",
        "connection_mode",
        "agent_update_authorization",
    }


async def _register_permitting_updates_at_the_site(tmp_path: Path, uuid: UUID4) -> RegisterResponse:
    config = get_config()
    _symlink_push_host(config, tmp_path, uuid)
    config.registrations_dir.mkdir(parents=True, exist_ok=True)
    (config.registrations_dir / f"{uuid}.json").write_text(
        '{"agent_updates_permitted": true, "subject": "herbert",'
        ' "registration_route": "register", "registered_at": 1760000000.0}'
    )
    return RegisterResponse(connection_mode=ConnectionMode.PULL)


def test_register_existing_reports_the_update_permission_of_the_registration(
    tmp_path: Path,
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    """CMK-39504 AC1, AC6"""
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.register",
        lambda *_args, **_kwargs: _register_permitting_updates_at_the_site(tmp_path, uuid),
    )

    response = client.post(
        "/register_existing",
        auth=("herbert", "joergl"),
        json={"uuid": str(uuid), "host_name": "myhost", "csr": serialized_csr},
    )

    assert response.json()["agent_update_authorization"] == "authorized"


def test_register_existing_token_reports_the_update_permission_of_the_registration(
    tmp_path: Path,
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    """CMK-39504 AC6"""
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.register_token",
        lambda *_args, **_kwargs: _register_permitting_updates_at_the_site(tmp_path, uuid),
    )

    response = client.post(
        "/register_existing_token",
        headers={"Authorization": f"CMK-TOKEN 0:{uuid4()}"},
        json={"uuid": str(uuid), "host_name": "myhost", "csr": serialized_csr},
    )

    assert response.json()["agent_update_authorization"] == "authorized"


def test_register_existing_uuid_csr_mismatch(
    client: TestClient,
    serialized_csr: str,
) -> None:
    response = client.post(
        "/register_existing",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid4()),
            "host_name": "myhost",
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "does not match" in response.json()["detail"]


# this is a regression test for CMK-11202
def test_register_existing_hostname_invalid(
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    response = client.post(
        "/register_existing",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "my/../host",
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Invalid host name: 'my/../host'"}


@pytest.mark.parametrize(
    "host_name",
    [
        pytest.param("test.checkmk.com", id="FQDN"),
        pytest.param("127.0.0.1", id="IPv4 loopback"),
        pytest.param("93.184.216.34", id="IPv4"),
        pytest.param("0:0:0:0:0:0:0:1", id="IPv6 uncompressed"),
        pytest.param("2606:2800:220:1:248:1893:25c8:1946", id="IPv6"),
        pytest.param("::", id="IPv6 unspecified"),
        pytest.param("::1", id="IPv6 loopback"),
    ],
)
def test_register_existing_accepts_host_name(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    host_name: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.register",
        return_value=RegisterResponse(connection_mode=ConnectionMode.PULL),
    )

    response = client.post(
        "/register_existing",
        auth=("herbert", "joergl"),
        json={"uuid": str(uuid), "host_name": host_name, "csr": serialized_csr},
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "host_name",
    [
        pytest.param("", id="empty"),
        pytest.param("...", id="dots only"),
    ],
)
def test_register_existing_rejects_host_name(
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    host_name: str,
) -> None:
    response = client.post(
        "/register_existing",
        auth=("herbert", "joergl"),
        json={"uuid": str(uuid), "host_name": host_name, "csr": serialized_csr},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": f"Invalid host name: '{host_name}'"}


def test_register_new_unauthenticated(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.cmk_edition",
        side_effect=HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="User authentication failed",
        ),
    )
    response = client.post(
        "/register_new",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "agent_labels": {},
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "User authentication failed"}


def test_register_new_community(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.community,
    )
    response = client.post(
        "/register_new",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "agent_labels": {"a": "b"},
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.NOT_IMPLEMENTED
    assert response.json() == {
        "detail": "The Checkmk Community edition does not support registration of new hosts"
    }


def test_register_new_uuid_csr_mismatch(
    mocker: MockerFixture,
    client: TestClient,
    serialized_csr: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.ultimate,
    )
    response = client.post(
        "/register_new",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid4()),
            "agent_labels": {},
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "does not match" in response.json()["detail"]


def _test_register_new(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    edition: CMKEdition,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.cmk_edition",
        return_value=edition,
    )
    response = client.post(
        "/register_new",
        auth=("monitoring", "supersafe"),
        json={
            "uuid": str(uuid),
            "agent_labels": {
                "a": "b",
                "c": "d",
            },
            "csr": serialized_csr,
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert set(response.json()) == {"root_cert"}

    triggered_r4r = R4R.read(uuid)
    assert triggered_r4r.status is R4RStatus.NEW
    assert triggered_r4r.request.uuid == uuid
    assert triggered_r4r.request.username == "monitoring"
    assert triggered_r4r.request.agent_labels == {
        "a": "b",
        "c": "d",
    }
    assert triggered_r4r.request.agent_cert.startswith("-----BEGIN CERTIFICATE-----")


def test_register_new_folder_missing(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    config = get_config()
    assert not (config.r4r_dir / "NEW").exists()
    _test_register_new(mocker, client, uuid, serialized_csr, CMKEdition.ultimate)
    assert oct(stat.S_IMODE((config.r4r_dir / "NEW").stat().st_mode)) == "0o770"


def test_register_new_folder_missing_cse(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    config = get_config()
    assert not (config.r4r_dir / "NEW").exists()
    _test_register_new(mocker, client, uuid, serialized_csr, CMKEdition.cloud)
    assert oct(stat.S_IMODE((config.r4r_dir / "NEW").stat().st_mode)) == "0o770"


def test_register_new_folder_exists(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    config = get_config()
    (config.r4r_dir / "NEW").mkdir(parents=True)
    _test_register_new(mocker, client, uuid, serialized_csr, CMKEdition.ultimate)


def test_register_new_ongoing_community(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.community,
    )
    response = client.post(
        f"/register_new_ongoing/{uuid}",
        auth=("herbert", "joergl"),
    )
    assert response.status_code == HTTPStatus.NOT_IMPLEMENTED
    assert response.json() == {
        "detail": "The Checkmk Community edition does not support registration of new hosts"
    }


def _call_register_new_ongoing_ultimate(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> httpx2.Response:
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.ultimate,
    )
    return client.post(
        f"/register_new_ongoing/{uuid}",
        auth=("user", "password"),
    )


def test_register_new_ongoing_not_found(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    R4R(
        status=R4RStatus.DECLINED,
        request=RequestForRegistration(
            uuid=uuid4(),
            username="user",
            agent_labels={},
            agent_cert="cert",
        ),
    ).write()
    response = _call_register_new_ongoing_ultimate(mocker, client, uuid)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "No registration with this UUID in progress"}


def test_register_new_ongoing_username_mismatch(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    R4R(
        status=R4RStatus.DECLINED,
        request=RequestForRegistration(
            uuid=uuid,
            username="user2",
            agent_labels={},
            agent_cert="cert",
        ),
    ).write()
    response = _call_register_new_ongoing_ultimate(mocker, client, uuid)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {
        "detail": "A registration is in progress, but it was triggered by a different user"
    }


@pytest.mark.parametrize(
    "status",
    (R4RStatus.NEW, R4RStatus.PENDING),
)
def test_register_new_ongoing_in_progress(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    status: R4RStatus,
) -> None:
    R4R(
        status=status,
        request=RequestForRegistration(
            uuid=uuid,
            username="user",
            agent_labels={},
            agent_cert="cert",
        ),
    ).write()
    response = _call_register_new_ongoing_ultimate(mocker, client, uuid)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "InProgress"}


def test_register_new_ongoing_in_declined(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    R4R(
        status=R4RStatus.DECLINED,
        request=RequestForRegistration(
            uuid=uuid,
            username="user",
            agent_labels={},
            agent_cert="cert",
            state={
                "type": "FOO",
                "value": "BAR",
                "readable": "Registration request declined",
            },
        ),
    ).write()
    response = _call_register_new_ongoing_ultimate(mocker, client, uuid)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "Declined", "reason": "Registration request declined"}


@pytest.mark.usefixtures("symlink_push_host")
def test_register_new_ongoing_success(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    R4R(
        status=R4RStatus.DISCOVERABLE,
        request=RequestForRegistration(
            uuid=uuid,
            username="user",
            agent_labels={},
            agent_cert="cert",
        ),
    ).write()
    response = _call_register_new_ongoing_ultimate(mocker, client, uuid)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "status": "Success",
        "agent_cert": "cert",
        "connection_mode": "push-agent",
        "agent_update_authorization": "unavailable",
    }


@pytest.mark.usefixtures("symlink_push_host")
def test_register_new_ongoing_reports_the_update_permission_of_the_registration(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    """CMK-39504 AC1, AC6"""
    R4R(
        status=R4RStatus.DISCOVERABLE,
        request=RequestForRegistration(
            uuid=uuid,
            username="user",
            agent_labels={},
            agent_cert="cert",
        ),
    ).write()
    (registrations_dir := get_config().registrations_dir).mkdir(parents=True, exist_ok=True)
    (registrations_dir / f"{uuid}.json").write_text(
        '{"agent_updates_permitted": false, "subject": "user",'
        ' "registration_route": "register_new", "registered_at": 1760000000.0}'
    )

    response = _call_register_new_ongoing_ultimate(mocker, client, uuid)

    assert response.json()["agent_update_authorization"] == "not_permitted"


def _agent_ca_common_name() -> str:
    return agent_ca_common_name(get_config().site_name)


@pytest.fixture(name="agent_data_headers")
def fixture_agent_data_headers(uuid: UUID4) -> dict[str, str]:
    return {
        "compression": "zlib",
        INJECTED_UUID_HEADER: str(uuid),
        INJECTED_ISSUER_HEADER: _agent_ca_common_name(),
        INJECTED_SERIAL_HEADER: UNREVOKED_SERIAL_NUMBER,
    }


@pytest.fixture(name="compressed_agent_data")
def fixture_compressed_agent_data() -> io.BytesIO:
    return io.BytesIO(compress(b"mock file"))


def test_agent_data_uuid_mismatch(
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    response = client.post(
        "/agent_data/123",
        headers=dict(agent_data_headers),
        files={"monitoring_data": ("filename", compressed_agent_data)},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "detail": f"Verified client UUID ({uuid}) does not match UUID in URL (123)"
    }


def test_agent_data_no_host(
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers=agent_data_headers,
        files={"monitoring_data": ("filename", compressed_agent_data)},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "Host is not registered"}


def test_agent_data_pull_host(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    config = get_config()
    source = config.agent_output_dir / str(uuid)
    source.symlink_to(tmp_path / "hostname")

    response = client.post(
        f"/agent_data/{uuid}",
        headers=agent_data_headers,
        files={
            "monitoring_data": (
                "filename",
                compressed_agent_data,
            )
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "Host is not a push host"}


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_invalid_compression(
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers={
            **agent_data_headers,
            "compression": "gzip",
        },
        files={"monitoring_data": ("filename", io.BytesIO(b"certainly invalid"))},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Unsupported compression algorithm: gzip"}


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_invalid_data(
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers=agent_data_headers,
        files={"monitoring_data": ("filename", io.BytesIO(b"certainly invalid"))},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Decompression of agent data failed"}


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_decompression_size(
    monkeypatch: MonkeyPatch,
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
) -> None:
    monkeypatch.setattr(decompression, "MAX_SIZE_AGENT_DATA", 1024)
    response = client.post(
        f"/agent_data/{uuid}",
        headers=agent_data_headers,
        files={"monitoring_data": ("filename", io.BytesIO(zlib.compress(b"\x00" * 1025, level=1)))},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Decompression of agent data failed"}


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_success(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers=agent_data_headers,
        files={"monitoring_data": ("filename", compressed_agent_data)},
    )

    file_path = tmp_path / "push-agent" / "hostname" / "agent_output"
    assert file_path.read_text() == "mock file"

    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.usefixtures("symlink_push_host")
@pytest.mark.parametrize("size", [10_000, 100_000])
def test_agent_data_is_complete_when_it_becomes_visible(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
    size: int,
) -> None:
    """CMK-41491: The fetcher may read agent_output right after the rename."""
    payload = b"x" * size
    file_path = tmp_path / "push-agent" / "hostname" / "agent_output"
    visible_sizes = []
    rename = os.rename

    def rename_and_record_visible_size(src: str, dst: str) -> None:
        rename(src, dst)
        visible_sizes.append(file_path.stat().st_size)

    monkeypatch.setattr(os, "rename", rename_and_record_visible_size)

    client.post(
        f"/agent_data/{uuid}",
        headers=agent_data_headers,
        files={"monitoring_data": ("filename", io.BytesIO(compress(payload)))},
    )

    assert visible_sizes == [size]


@pytest.fixture(name="registration_status_headers")
def fixture_registration_status_headers(uuid: UUID4) -> dict[str, str]:
    return {
        INJECTED_UUID_HEADER: str(uuid),
        INJECTED_ISSUER_HEADER: _agent_ca_common_name(),
        INJECTED_SERIAL_HEADER: UNREVOKED_SERIAL_NUMBER,
    }


def test_registration_status_uuid_mismtach(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    response = client.get(
        "/registration_status/123",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "detail": f"Verified client UUID ({uuid}) does not match UUID in URL (123)"
    }


def test_registration_status_declined(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    R4R(
        status=R4RStatus.DECLINED,
        request=RequestForRegistration(
            uuid=uuid,
            username="harry",
            agent_labels={},
            state={
                "type": "FOO",
                "value": "BAR",
                "readable": "Registration request declined",
            },
            agent_cert="cert",
        ),
    ).write()

    response = client.get(
        f"/registration_status/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "hostname": None,
        "status": "declined",
        "connection_mode": None,
        "message": "Registration request declined",
        "type": None,
    }


def test_registration_status_host_not_registered(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    response = client.get(
        f"/registration_status/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Host is not registered"}


@pytest.mark.usefixtures("symlink_push_host")
def test_registration_status_push_host(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    R4R(
        status=R4RStatus.DISCOVERABLE,
        request=RequestForRegistration(
            uuid=uuid,
            username="harry",
            agent_labels={},
            agent_cert="cert",
        ),
    ).write()

    response = client.get(
        f"/registration_status/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "hostname": "hostname",
        "status": "discoverable",
        "connection_mode": ConnectionMode.PUSH.value,
        "message": "Host registered",
        "type": ConnectionMode.PUSH.value,
    }


def test_registration_status_pull_host(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    config = get_config()
    source = config.agent_output_dir / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.get(
        f"/registration_status/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "hostname": "hostname",
        "status": None,
        "connection_mode": ConnectionMode.PULL.value,
        "message": "Host registered",
        "type": ConnectionMode.PULL.value,
    }


def test_registration_status_v2_uuid_mismtach(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    response = client.get(
        "/registration_status_v2/123",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "detail": f"Verified client UUID ({uuid}) does not match UUID in URL (123)"
    }


def test_registration_status_v2_host_not_registered(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    response = client.get(
        f"/registration_status_v2/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "NotRegistered"}


@pytest.mark.usefixtures("symlink_push_host")
def test_registration_status_v2_push_host(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    response = client.get(
        f"/registration_status_v2/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "status": "Registered",
        "hostname": "hostname",
        "connection_mode": ConnectionMode.PUSH.value,
    }


def test_registration_status_v2_pull_host(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    config = get_config()
    source = config.agent_output_dir / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.get(
        f"/registration_status_v2/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "status": "Registered",
        "hostname": "hostname",
        "connection_mode": ConnectionMode.PULL.value,
    }


def test_renew_certificate_uuid_csr_mismatch(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    _key, wrong_csr = generate_csr_pair(str(uuid4()), 1024)
    response = client.post(
        f"/renew_certificate/{uuid}",
        headers=registration_status_headers,
        json={"csr": serialize_to_pem(wrong_csr)},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "does not match" in response.json()["detail"]


def test_renew_certificate_not_registered(
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    response = client.post(
        f"/renew_certificate/{uuid}",
        headers=registration_status_headers,
        json={"csr": serialized_csr},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert "Host is not registered" in response.json()["detail"]


def test_renew_certificate_ok(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    config = get_config()
    source = config.agent_output_dir / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.post(
        f"/renew_certificate/{uuid}",
        headers=registration_status_headers,
        json={"csr": serialized_csr},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["agent_cert"].startswith("-----BEGIN CERTIFICATE-----")


# fmt: off
AGENT_UPDATE_REQUESTS = [
    pytest.param("agent_update/status", {"platform": "linux_deb", "installed_aghash": "fedcba9876543210"}, id="status"),
    pytest.param("agent_update/agent", {"platform": "linux_deb", "aghash": "0123456789abcdef"}, id="agent"),
]
# fmt: on


@pytest.mark.parametrize("endpoint, body", AGENT_UPDATE_REQUESTS)
def test_agent_update_of_another_uuid_is_rejected(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
    endpoint: str,
    body: dict[str, str],
) -> None:
    other_uuid = uuid4()

    response = client.post(
        f"/{endpoint}/{other_uuid}",
        headers=registration_status_headers,
        json=body,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "detail": f"Verified client UUID ({uuid}) does not match UUID in URL ({other_uuid})"
    }


@pytest.mark.parametrize("endpoint, body", AGENT_UPDATE_REQUESTS)
def test_agent_update_of_an_unregistered_host_is_forbidden(
    client: TestClient,
    uuid: UUID4,
    registration_status_headers: MutableMapping[str, str],
    endpoint: str,
    body: dict[str, str],
) -> None:
    response = client.post(
        f"/{endpoint}/{uuid}",
        headers=registration_status_headers,
        json=body,
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "Host is not registered"}
