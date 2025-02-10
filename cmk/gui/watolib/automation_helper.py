#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provide an interface to the automation helper"""

import logging
import socket
from collections.abc import Sequence
from typing import Final

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool

from cmk.utils import paths

from cmk.automations.helper_api import AutomationPayload, AutomationResponse

from .automation_executor import arguments_with_timeout, AutomationExecutor, LocalAutomationResult

AUTOMATION_HELPER_HOST: Final = "localhost"
AUTOMATION_HELPER_BASE_URL: Final = "http://local-automation"
AUTOMATION_HELPER_ENDPOINT: Final = f"{AUTOMATION_HELPER_BASE_URL}/automation"
AUTOMATION_HELPER_SOCKET: Final = "tmp/run/automation-helper.sock"


class HelperExecutor(AutomationExecutor):
    def execute(
        self,
        command: str,
        args: Sequence[str],
        stdin: str,
        logger: logging.Logger,
        timeout: int | None,
    ) -> LocalAutomationResult:
        session = requests.Session()
        session.mount(AUTOMATION_HELPER_BASE_URL, _LocalAutomationAdapter())

        payload = AutomationPayload(
            name=command,
            args=arguments_with_timeout(args, timeout),
            stdin=stdin,
            log_level=logger.getEffectiveLevel(),
        ).model_dump(mode="json")

        response = session.post(AUTOMATION_HELPER_ENDPOINT, json=payload)
        response.raise_for_status()
        response_data = AutomationResponse.model_validate(response.json())

        return LocalAutomationResult(
            exit_code=response_data.exit_code,
            output=response_data.output,
            command_description=self.command_description(command, args, logger, timeout),
            error=response_data.error,
        )

    def command_description(
        self, command: str, args: Sequence[str], logger: logging.Logger, timeout: int | None
    ) -> str:
        return repr({"command": command, "args": arguments_with_timeout(args, timeout)})


class _LocalAutomationConnection(HTTPConnection):
    def __init__(self) -> None:
        super().__init__(AUTOMATION_HELPER_HOST)

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(paths.omd_root.joinpath(AUTOMATION_HELPER_SOCKET)))


class _LocalAutomationConnectionPool(HTTPConnectionPool):
    def __init__(self) -> None:
        super().__init__(AUTOMATION_HELPER_HOST)

    def _new_conn(self) -> _LocalAutomationConnection:
        return _LocalAutomationConnection()


class _LocalAutomationAdapter(HTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        return _LocalAutomationConnectionPool()
