#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
import stat
from pathlib import Path
from typing import Mapping
from unittest import mock
from uuid import UUID
from zlib import compress

import pytest
from agent_receiver import site_context
from agent_receiver.checkmk_rest_api import CMKEdition, HostConfiguration
from agent_receiver.models import HostTypeEnum
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from cmk.utils.misc import typeshed_issue_7724


@pytest.fixture(autouse=True)
def deactivate_certificate_validation(mocker: MockerFixture) -> None:
    mocker.patch(
        "agent_receiver.certificates._invalid_certificate_response",
        lambda _h: None,
    )


@pytest.fixture(name="symlink_push_host")
def fixture_symlink_push_host(
    tmp_path: Path,
    uuid: UUID,
) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    (target_dir := tmp_path / "hostname").mkdir()
    source.symlink_to(target_dir)


def test_register_register_with_hostname_host_missing(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.host_configuration",
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
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.host_configuration",
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
        "detail": "This host is monitored on the site some-site, but you tried to register it at the site NO_SITE."
    }


def test_register_register_with_hostname_cluster_host(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.host_configuration",
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
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.host_configuration",
        return_value=HostConfiguration(
            site="NO_SITE",
            is_cluster=False,
        ),
    )
    mocker.patch(
        "agent_receiver.endpoints.link_host_with_uuid",
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


def test_register_register_with_hostname_ok(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.host_configuration",
        return_value=HostConfiguration(
            site="NO_SITE",
            is_cluster=False,
        ),
    )
    mocker.patch(
        "agent_receiver.endpoints.link_host_with_uuid",
        return_value=None,
    )
    response = client.post(
        "/register_with_hostname",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "host_name": "myhost",
        },
    )
    assert response.status_code == 204
    assert not response.text


def test_register_with_labels_unauthenticated(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.cmk_edition",
        side_effect=HTTPException(
            status_code=401,
            detail="User authentication failed",
        ),
    )
    response = client.post(
        "/register_with_labels",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "agent_labels": {},
        },
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "User authentication failed"}


def test_register_with_labels_cre(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.cmk_edition",
        lambda _c: CMKEdition["cre"],
    )
    response = client.post(
        "/register_with_labels",
        auth=("herbert", "joergl"),
        json={
            "uuid": str(uuid),
            "agent_labels": {"a": "b"},
        },
    )
    assert response.status_code == 501
    assert response.json() == {
        "detail": "The Checkmk Raw edition does not support registration with agent labels"
    }


def _test_register_with_labels(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    mocker.patch(
        "agent_receiver.endpoints.cmk_edition",
        lambda _c: CMKEdition["cpe"],
    )
    response = client.post(
        "/register_with_labels",
        auth=("monitoring", "supersafe"),
        json={
            "uuid": str(uuid),
            "agent_labels": {
                "a": "b",
                "c": "d",
            },
        },
    )
    assert response.status_code == 204
    assert json.loads((site_context.r4r_dir() / "NEW" / f"{uuid}.json").read_text()) == {
        "uuid": str(uuid),
        "username": "monitoring",
        "agent_labels": {
            "a": "b",
            "c": "d",
        },
    }
    assert (
        oct(stat.S_IMODE((site_context.r4r_dir() / "NEW" / f"{uuid}.json").stat().st_mode))
        == "0o660"
    )


def test_register_with_labels_folder_missing(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    assert not (site_context.r4r_dir() / "NEW").exists()
    _test_register_with_labels(
        mocker,
        client,
        uuid,
    )
    assert oct(stat.S_IMODE((site_context.r4r_dir() / "NEW").stat().st_mode)) == "0o770"


def test_register_with_labels_folder_exists(
    mocker: MockerFixture,
    client: TestClient,
    uuid: UUID,
) -> None:
    (site_context.r4r_dir() / "NEW").mkdir(parents=True)
    _test_register_with_labels(
        mocker,
        client,
        uuid,
    )


@pytest.fixture(name="agent_data_headers")
def fixture_agent_data_headers() -> Mapping[str, str]:
    return {
        "certificate": "irrelevant",
        "compression": "zlib",
    }


@pytest.fixture(name="compressed_agent_data")
def fixture_compressed_agent_data() -> io.BytesIO:
    return io.BytesIO(compress(b"mock file"))


def test_agent_data_no_host(
    client: TestClient,
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers=typeshed_issue_7724(agent_data_headers),
        files={"monitoring_data": ("filename", compressed_agent_data)},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Host is not registered"}


def test_agent_data_pull_host(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    source.symlink_to(tmp_path / "hostname")

    response = client.post(
        f"/agent_data/{uuid}",
        headers=typeshed_issue_7724(agent_data_headers),
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
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
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
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers=typeshed_issue_7724(agent_data_headers),
        files={"monitoring_data": ("filename", io.BytesIO(b"certainly invalid"))},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Decompression of agent data failed"}


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_success(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    response = client.post(
        f"/agent_data/{uuid}",
        headers=typeshed_issue_7724(agent_data_headers),
        files={"monitoring_data": ("filename", compressed_agent_data)},
    )

    file_path = tmp_path / "hostname" / "agent_output"
    assert file_path.read_text() == "mock file"

    assert response.status_code == 204


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_move_error(
    caplog,
    client: TestClient,
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    with mock.patch("agent_receiver.endpoints.Path.rename") as move_mock:
        move_mock.side_effect = FileNotFoundError()
        response = client.post(
            f"/agent_data/{uuid}",
            headers=typeshed_issue_7724(agent_data_headers),
            files={"monitoring_data": ("filename", compressed_agent_data)},
        )

    assert response.status_code == 204
    assert caplog.records[0].message == f"uuid={uuid} Agent data saved"


@pytest.mark.usefixtures("symlink_push_host")
def test_agent_data_move_ready(
    client: TestClient,
    uuid: UUID,
    agent_data_headers: Mapping[str, str],
    compressed_agent_data: io.BytesIO,
) -> None:
    (path_ready := site_context.r4r_dir() / "READY").mkdir()
    (path_ready / f"{uuid}.json").touch()

    client.post(
        f"/agent_data/{uuid}",
        headers=typeshed_issue_7724(agent_data_headers),
        files={"monitoring_data": ("filename", compressed_agent_data)},
    )

    assert (site_context.r4r_dir() / "DISCOVERABLE" / f"{uuid}.json").exists()


def test_registration_status_declined(
    client: TestClient,
    uuid: UUID,
) -> None:
    (path_declined := site_context.r4r_dir() / "DECLINED").mkdir()
    (path_declined / f"{uuid}.json").write_text(
        json.dumps({"message": "Registration request declined"})
    )

    response = client.get(
        f"/registration_status/{uuid}",
        headers={"certificate": "cert", "authentication": "auth"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "hostname": None,
        "status": "declined",
        "type": None,
        "message": "Registration request declined",
    }


def test_registration_status_host_not_registered(
    client: TestClient,
    uuid: UUID,
) -> None:
    response = client.get(
        f"/registration_status/{uuid}",
        headers={"certificate": "cert", "authentication": "auth"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Host is not registered"}


@pytest.mark.usefixtures("symlink_push_host")
def test_registration_status_push_host(
    client: TestClient,
    uuid: UUID,
) -> None:
    (path_discoverable := site_context.r4r_dir() / "DISCOVERABLE").mkdir()
    (path_discoverable / f"{uuid}.json").touch()

    response = client.get(
        f"/registration_status/{uuid}",
        headers={"certificate": "cert", "authentication": "auth"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "hostname": "hostname",
        "status": "discoverable",
        "type": HostTypeEnum.PUSH.value,
        "message": "Host registered",
    }


def test_registration_status_pull_host(
    tmp_path: Path,
    client: TestClient,
    uuid: UUID,
) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    response = client.get(
        f"/registration_status/{uuid}",
        headers={"certificate": "cert", "authentication": "auth"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "hostname": "hostname",
        "status": None,
        "type": HostTypeEnum.PULL.value,
        "message": "Host registered",
    }
