#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import os
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from marcv.server import app  # type: ignore[import]


def test_agent_data_no_host() -> None:

    client = TestClient(app)
    mock_file = io.StringIO("mock file")
    response = client.post(
        "/agent-data",
        data={"uuid": 1234},
        files={"upload_file": ("filename", mock_file)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Host is not registered"}


def test_agent_data_success(tmp_path: Path) -> None:
    mock_file = io.StringIO("mock file")

    os.mkdir(tmp_path / "1234")
    with mock.patch("marcv.server.AGENT_OUTPUT_DIR", tmp_path):
        from marcv.server import app  # type: ignore[import]

        client = TestClient(app)
        response = client.post(
            "/agent-data",
            data={"uuid": 1234},
            files={"upload_file": ("filename", mock_file)},
        )

    assert response.status_code == 200
    assert response.json() == {"message": "Agent data saved."}
