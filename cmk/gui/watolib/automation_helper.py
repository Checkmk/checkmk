#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provide an interface to the automation helper"""

import logging
from collections.abc import Sequence
from typing import assert_never, Final

import requests

from cmk.automations.helper_api import AutomationPayload, AutomationResponse
from cmk.gui.exceptions import MKInternalError
from cmk.gui.i18n import _
from cmk.gui.utils.unixsocket_http import make_session as make_unixsocket_session
from cmk.utils import paths

from .automation_executor import arguments_with_timeout, AutomationExecutor, LocalAutomationResult


class HelperExecutor(AutomationExecutor):
    _SOCKET_PATH = paths.omd_root.joinpath("tmp/run/automation-helper.sock")
    _BASE_URL: Final = "http://local-automation"

    def execute(
        self,
        command: str,
        args: Sequence[str],
        stdin: str,
        logger: logging.Logger,
        timeout: int | None,
    ) -> LocalAutomationResult:
        session = make_unixsocket_session(
            self._SOCKET_PATH,
            self._BASE_URL,
        )

        payload = AutomationPayload(
            name=command,
            args=arguments_with_timeout(args, timeout),
            stdin=stdin,
            log_level=logger.getEffectiveLevel(),
        ).model_dump(mode="json")

        try:
            response = session.post(f"{self._BASE_URL}/automation", json=payload)
        except requests.ConnectionError as e:
            raise MKInternalError(
                _(
                    "Could not connect to automation helper. "
                    "Possibly the service <tt>automation-helper</tt> is not started, "
                    "please make sure that all site services are started. "
                    "Tried to connect via <tt>%s</tt>. Reported error was: %s."
                )
                % (self._SOCKET_PATH, e)
            )
        response.raise_for_status()
        response_data = AutomationResponse.model_validate(response.json())

        match response_data.serialized_result_or_error_code:
            case str():
                return LocalAutomationResult(
                    exit_code=0,
                    output=response_data.serialized_result_or_error_code,
                    command_description=self.command_description(command, args, logger, timeout),
                    error=response_data.stderr,
                )
            case int():
                return LocalAutomationResult(
                    exit_code=response_data.serialized_result_or_error_code,
                    output=response_data.stdout,
                    command_description=self.command_description(command, args, logger, timeout),
                    error=response_data.stderr,
                )
            case _:
                assert_never(response_data.serialized_result_or_error_code)

    def command_description(
        self, command: str, args: Sequence[str], logger: logging.Logger, timeout: int | None
    ) -> str:
        return repr({"command": command, "args": arguments_with_timeout(args, timeout)})
