#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import sys
from pathlib import Path
from typing import assert_never

import requests
from pydantic import BaseModel, RootModel
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool

from cmk.utils.paths import omd_root

from cmk.base.automation_helper._app import AutomationPayload

_BASE_URL = "http://aut-helper"


class HealthMode(BaseModel, frozen=True): ...


class AutomationMode(BaseModel, frozen=True):
    payload: AutomationPayload


class _Mode(RootModel, frozen=True):
    root: AutomationMode | HealthMode


class _LocalAutomationConnection(HTTPConnection):
    def __init__(self, socket_path: Path) -> None:
        super().__init__("localhost")
        self._socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(self._socket_path))


class _LocalAutomationConnectionPool(HTTPConnectionPool):
    def __init__(self, socket_path: Path) -> None:
        super().__init__("localhost")
        self._socket_path = socket_path

    def _new_conn(self) -> _LocalAutomationConnection:
        return _LocalAutomationConnection(self._socket_path)


class _LocalAutomationAdapter(HTTPAdapter):
    def __init__(self, socket_path: Path) -> None:
        super().__init__()
        self._socket_path = socket_path

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        return _LocalAutomationConnectionPool(self._socket_path)


def main() -> None:
    mode = _Mode.model_validate_json(sys.stdin.read()).root
    session = requests.Session()
    session.mount(_BASE_URL, _LocalAutomationAdapter(omd_root / "tmp/run/automation-helper.sock"))

    match mode:
        case AutomationMode(payload=payload):
            response = session.post(f"{_BASE_URL}/automation", json=payload.model_dump())
        case HealthMode():
            response = session.get(f"{_BASE_URL}/health")
        case _:
            assert_never(mode)

    response.raise_for_status()
    sys.stdout.write(response.text)


if __name__ == "__main__":
    main()
