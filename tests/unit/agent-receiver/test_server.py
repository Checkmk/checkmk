#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import os
from pathlib import Path
from unittest import mock

import pytest
from agent_receiver.server import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_paths(tmp_path: Path):
    with mock.patch("agent_receiver.server.AGENT_OUTPUT_DIR", tmp_path), mock.patch(
        "agent_receiver.server.REGISTRATION_REQUESTS", tmp_path
    ):
        yield


def test_agent_data_no_host() -> None:

    client = TestClient(app)
    mock_file = io.StringIO("mock file")
    response = client.post(
        "/agent_data",
        data={"uuid": 1234},
        files={"upload_file": ("filename", mock_file)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Host is not registered"}


def test_agent_data_success(tmp_path: Path) -> None:
    mock_file = io.StringIO("mock file")

    source = tmp_path / "1234"
    target_dir = tmp_path / "hostname"
    os.mkdir(target_dir)
    source.symlink_to(target_dir)

    client = TestClient(app)
    response = client.post(
        "/agent_data",
        data={"uuid": 1234},
        files={"upload_file": ("filename", mock_file)},
    )

    file_path = tmp_path / "hostname" / "received-output"
    assert file_path.exists()

    assert response.status_code == 200
    assert response.json() == {"message": "Agent data saved."}


def test_agent_data_move_error(tmp_path: Path, caplog) -> None:
    mock_file = io.StringIO("mock file")

    os.mkdir(tmp_path / "READY")
    Path(tmp_path / "READY" / "1234.json").touch()
    os.mkdir(tmp_path / "DISCOVERABLE")

    source = tmp_path / "1234"
    target_dir = tmp_path / "hostname"
    os.mkdir(target_dir)
    source.symlink_to(target_dir)

    with mock.patch("agent_receiver.server.Path.rename") as move_mock:

        move_mock.side_effect = FileNotFoundError()

        client = TestClient(app)
        response = client.post(
            "/agent_data",
            data={"uuid": 1234},
            files={"upload_file": ("filename", mock_file)},
        )

    assert response.status_code == 200
    assert caplog.records[0].message == "uuid=1234 Agent data saved"


def test_agent_data_move_ready(tmp_path: Path) -> None:
    mock_file = io.StringIO("mock file")

    os.mkdir(tmp_path / "READY")
    Path(tmp_path / "READY" / "1234.json").touch()
    os.mkdir(tmp_path / "DISCOVERABLE")

    source = tmp_path / "1234"
    target_dir = tmp_path / "hostname"
    os.mkdir(target_dir)
    source.symlink_to(target_dir)

    client = TestClient(app)
    client.post(
        "/agent_data",
        data={"uuid": 1234},
        files={"upload_file": ("filename", mock_file)},
    )

    registration_request = tmp_path / "DISCOVERABLE" / "1234.json"
    assert registration_request.exists()
