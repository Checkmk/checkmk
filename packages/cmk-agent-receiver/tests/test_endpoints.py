#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import stat
from collections.abc import MutableMapping
from pathlib import Path
from uuid import uuid4
from zlib import compress

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import UUID4
from pytest_mock import MockerFixture

from cmk.agent_receiver import site_context
from cmk.agent_receiver.certs import serialize_to_pem
from cmk.agent_receiver.checkmk_rest_api import CMKEdition, HostConfiguration, RegisterResponse
from cmk.agent_receiver.models import ConnectionMode, R4RStatus, RequestForRegistration
from cmk.agent_receiver.utils import R4R

from .certs import generate_csr_pair


@pytest.fixture(name="symlink_push_host")
def fixture_symlink_push_host(
    tmp_path: Path,
    uuid: UUID4,
) -> None:
    _symlink_push_host(tmp_path, uuid)


def _symlink_push_host(
    tmp_path: Path,
    uuid: UUID4,
) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    (target_dir := tmp_path / "push-agent" / "hostname").mkdir(parents=True)
    source.symlink_to(target_dir)


@pytest.fixture(name="serialized_csr")
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
    def rest_api_register_mock(*_args: object, **_kwargs: object) -> RegisterResponse:
        _symlink_push_host(tmp_path, uuid)
        return RegisterResponse(connection_mode=ConnectionMode.PULL)

    mocker.patch(
        "cmk.agent_receiver.endpoints.register",
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
    assert response.status_code == 200
    assert set(response.json()) == {"root_cert", "agent_cert", "connection_mode"}


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
    assert response.status_code == 400
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
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid host name: 'my/../host'"}


def test_register_register_with_hostname_host_missing(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.host_configuration",
        side_effect=HTTPException(
            status_code=404,
            detail="N O T  F O U N D",
        ),
    )
    response = client.post(
        "/register_with_hostname",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "myhost",
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "N O T  F O U N D"}


def test_register_register_with_hostname_wrong_site(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.host_configuration",
        return_value=HostConfiguration(
            site="some-site",
            is_cluster=False,
        ),
    )
    response = client.post(
        "/register_with_hostname",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "myhost",
        },
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": (
            "This host is monitored on the site some-site, "
            "but you tried to register it at the site NO_SITE."
        )
    }


def test_register_register_with_hostname_cluster_host(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.host_configuration",
        return_value=HostConfiguration(
            site="NO_SITE",
            is_cluster=True,
        ),
    )
    response = client.post(
        "/register_with_hostname",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "myhost",
        },
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "This host is a cluster host. Register its nodes instead."}


def test_register_register_with_hostname_unauthorized(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.host_configuration",
        return_value=HostConfiguration(
            site="NO_SITE",
            is_cluster=False,
        ),
    )
    mocker.patch(
        "cmk.agent_receiver.endpoints.link_host_with_uuid",
        side_effect=HTTPException(
            status_code=403,
            detail="You do not have the permission for agent pairing.",
        ),
    )
    response = client.post(
        "/register_with_hostname",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "myhost",
        },
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "You do not have the permission for agent pairing."}


@pytest.mark.parametrize(
    "hostname,valid",
    [
        ("myhost", True),
        ("test.checkmk.com", True),
        ("127.0.0.1", True),
        ("93.184.216.34", True),
        ("0:0:0:0:0:0:0:1", True),
        ("2606:2800:220:1:248:1893:25c8:1946", True),
        ("::", True),
        ("::1", True),
        ("", False),
        ("...", False),
        ("my/../host", False),  # this is a regression test for CMK-11202
    ],
)
def test_register_register_with_hostname_hostname_validity(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    hostname: str,
    valid: bool,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.host_configuration",
        return_value=HostConfiguration(
            site="NO_SITE",
            is_cluster=False,
        ),
    )
    mocker.patch("cmk.agent_receiver.endpoints.link_host_with_uuid", return_value=None)

    response = client.post(
        "/register_with_hostname",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": hostname,
        },
    )

    if valid:
        assert response.status_code == 204
        assert not response.text
    else:
        assert response.status_code == 400
        assert response.json() == {"detail": f"Invalid host name: '{hostname}'"}


def test_register_new_unauthenticated(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.cmk_edition",
        side_effect=HTTPException(
            status_code=401,
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
    assert response.status_code == 401
    assert response.json() == {"detail": "User authentication failed"}


def test_register_new_cre(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.cre,
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
    assert response.status_code == 501
    assert response.json() == {
        "detail": "The Checkmk Raw edition does not support registration of new hosts"
    }


def test_register_new_uuid_csr_mismatch(
    mocker: MockerFixture,
    client: TestClient,
    serialized_csr: str,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.cce,
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
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def _test_register_new(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    edition: CMKEdition,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.cmk_edition",
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
    assert response.status_code == 200
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
    assert not (site_context.r4r_dir() / "NEW").exists()
    _test_register_new(mocker, client, uuid, serialized_csr, CMKEdition.cce)
    assert oct(stat.S_IMODE((site_context.r4r_dir() / "NEW").stat().st_mode)) == "0o770"


def test_register_new_folder_missing_cse(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    assert not (site_context.r4r_dir() / "NEW").exists()
    _test_register_new(mocker, client, uuid, serialized_csr, CMKEdition.cse)
    assert oct(stat.S_IMODE((site_context.r4r_dir() / "NEW").stat().st_mode)) == "0o770"


def test_register_new_folder_exists(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
) -> None:
    (site_context.r4r_dir() / "NEW").mkdir(parents=True)
    _test_register_new(mocker, client, uuid, serialized_csr, CMKEdition.cce)


def test_register_new_ongoing_cre(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> None:
    mocker.patch(
        "cmk.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.cre,
    )
    response = client.post(
        f"/register_new_ongoing/{uuid}",
        auth=("herbert", "joergl"),
    )
    assert response.status_code == 501
    assert response.json() == {
        "detail": "The Checkmk Raw edition does not support registration of new hosts"
    }


def _call_register_new_ongoing_cce(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID4,
) -> httpx.Response:
    mocker.patch(
        "cmk.agent_receiver.endpoints.cmk_edition",
        return_value=CMKEdition.cce,
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
    response = _call_register_new_ongoing_cce(mocker, client, uuid)
    assert response.status_code == 404
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
    response = _call_register_new_ongoing_cce(mocker, client, uuid)
    assert response.status_code == 403
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
    response = _call_register_new_ongoing_cce(mocker, client, uuid)
    assert response.status_code == 200
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
    response = _call_register_new_ongoing_cce(mocker, client, uuid)
    assert response.status_code == 200
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
    response = _call_register_new_ongoing_cce(mocker, client, uuid)
    assert response.status_code == 200
    assert response.json() == {
        "status": "Success",
        "agent_cert": "cert",
        "connection_mode": "push-agent",
    }


@pytest.fixture(name="agent_data_headers")
def fixture_agent_data_headers(uuid: UUID4) -> dict[str, str]:
    return {
        "compression": "zlib",
        "verified-uuid": str(uuid),
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
    assert response.status_code == 400
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
    assert response.status_code == 403
    assert response.json() == {"detail": "Host is not registered"}


def test_agent_data_pull_host(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    agent_data_headers: MutableMapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    source = site_context.agent_output_dir() / str(uuid)
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
    assert response.status_code == 403
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
    assert response.status_code == 400
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
    assert response.status_code == 400
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

    assert response.status_code == 204


@pytest.fixture(name="registration_status_headers")
def fixture_registration_status_headers(uuid: UUID4) -> dict[str, str]:
    return {
        "verified-uuid": str(uuid),
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

    assert response.status_code == 400
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

    assert response.status_code == 200
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

    assert response.status_code == 404
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

    assert response.status_code == 200
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
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.get(
        f"/registration_status/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == 200
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

    assert response.status_code == 400
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

    assert response.status_code == 200
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

    assert response.status_code == 200
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
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.get(
        f"/registration_status_v2/{uuid}",
        headers=registration_status_headers,
    )

    assert response.status_code == 200
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

    assert response.status_code == 400
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

    assert response.status_code == 403
    assert "Host is not registered" in response.json()["detail"]


def test_renew_certificate_ok(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID4,
    serialized_csr: str,
    registration_status_headers: MutableMapping[str, str],
) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.post(
        f"/renew_certificate/{uuid}",
        headers=registration_status_headers,
        json={"csr": serialized_csr},
    )

    assert response.status_code == 200
    assert response.json()["agent_cert"].startswith("-----BEGIN CERTIFICATE-----")
