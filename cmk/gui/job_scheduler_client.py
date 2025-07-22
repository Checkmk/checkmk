#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="no-untyped-def"

from typing import Final

import requests

import cmk.ccc.resulttype as result
from cmk.gui.i18n import _
from cmk.gui.utils.unixsocket_http import make_session as make_unixsocket_session
from cmk.utils import paths


class StartupError(Exception): ...


class JobSchedulerClient:
    _SOCKET_PATH = paths.omd_root.joinpath("tmp/run/ui-job-scheduler.sock")
    _BASE_URL: Final = "http://local-ui-job-scheduler"

    def __init__(self) -> None:
        self._session = make_unixsocket_session(
            self._SOCKET_PATH,
            self._BASE_URL,
        )

    def get(self, endpoint: str) -> result.Result[requests.Response, StartupError]:
        return self._request("GET", f"{self._BASE_URL}/{endpoint}")

    def post(
        self, endpoint: str, json: dict[str, object]
    ) -> result.Result[requests.Response, StartupError]:
        return self._request("POST", f"{self._BASE_URL}/{endpoint}", json)

    def _request(
        self, method: str, url: str, json: dict[str, object] | None = None
    ) -> result.Result[requests.Response, StartupError]:
        try:
            response = self._session.request(method, url, json=json, timeout=30)
        except requests.ConnectionError as e:
            return result.Error(
                StartupError(
                    _(
                        "Could not connect to ui-job-scheduler. "
                        "Possibly the service <tt>ui-job-scheduler</tt> is not started, "
                        "please make sure that all site services are started. "
                        "Tried to connect via <tt>%s</tt>. Reported error was: %s."
                    )
                    % (self._SOCKET_PATH, e)
                )
            )
        except requests.RequestException as e:
            return result.Error(
                StartupError(_("Communication with ui-job-scheduler failed: %s") % e)
            )

        if response.status_code != 200:
            return result.Error(
                StartupError(_("Got response: HTTP %s: %s") % (response.status_code, response.text))
            )

        return result.OK(response)
