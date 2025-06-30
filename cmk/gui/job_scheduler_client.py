#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="no-untyped-def"

import socket
from typing import Final, override

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool

import cmk.ccc.resulttype as result

from cmk.utils import paths

from cmk.gui.i18n import _

JOB_SCHEDULER_HOST: Final = "localhost"
JOB_SCHEDULER_BASE_URL: Final = "http://local-ui-job-scheduler"
JOB_SCHEDULER_ENDPOINT: Final = f"{JOB_SCHEDULER_BASE_URL}/automation"
JOB_SCHEDULER_SOCKET: Final = "tmp/run/ui-job-scheduler.sock"


class StartupError(Exception): ...


class JobSchedulerClient:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.mount(JOB_SCHEDULER_BASE_URL, _JobSchedulerAdapter())

    def get(self, endpoint: str) -> result.Result[requests.Response, StartupError]:
        return self._request("GET", f"{JOB_SCHEDULER_BASE_URL}/{endpoint}")

    def post(
        self, endpoint: str, json: dict[str, object]
    ) -> result.Result[requests.Response, StartupError]:
        return self._request("POST", f"{JOB_SCHEDULER_BASE_URL}/{endpoint}", json)

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
                    % (paths.omd_root.joinpath(JOB_SCHEDULER_SOCKET), e)
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


class _JobSchedulerConnection(HTTPConnection):
    def __init__(self) -> None:
        super().__init__(JOB_SCHEDULER_HOST)

    @override
    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(paths.omd_root.joinpath(JOB_SCHEDULER_SOCKET)))


class _JobSchedulerConnectionPool(HTTPConnectionPool):
    def __init__(self) -> None:
        super().__init__(JOB_SCHEDULER_HOST)

    def _new_conn(self) -> _JobSchedulerConnection:
        return _JobSchedulerConnection()


class _JobSchedulerAdapter(HTTPAdapter):
    @override
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        return _JobSchedulerConnectionPool()
