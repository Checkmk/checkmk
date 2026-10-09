# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A stand-in for the REST API of a Veeam Backup & Replication server.

`replaying()` answers the special agent with responses recorded from a real server, so
the system test runs where no Veeam server is available. Timestamps in the recording are
moved forward by the time passed since the recording, so that ages ("last backup 3 hours
ago") stay what they were.

The recording is made by a script in the qa-test-data repository; README.md explains
how to use it.
"""

import json
import re
import tempfile
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from functools import partial
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qsl

from tests.testlib.system.mock_server import MockEndpoint, MockMethod, MockResponse, MockServer

RECORDING_FILE = Path(__file__).parent / "recorded_responses.json"

TOKEN_PATH = "/api/oauth2/token"
_ACCESS_TOKEN = "mock-access-token"
_REFRESH_TOKEN = "mock-refresh-token"
_TOKEN_RESPONSE = json.dumps(
    {
        "access_token": _ACCESS_TOKEN,
        "token_type": "bearer",
        "refresh_token": _REFRESH_TOKEN,
        "expires_in": 900,
    }
).encode()

# Some endpoints (e.g. /api/v1/taskSessions) leave out the UTC offset.
_ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")


@dataclass(frozen=True)
class Credentials:
    user: str
    password: str


@dataclass(frozen=True)
class RecordedResponse:
    status: int
    body: object


@dataclass
class Recording:
    recorded_at: datetime
    api_version: str
    """The `x-api-version` the special agent sent while recording. Replay rejects any other
    version, the way a real server rejects a version it does not support."""
    responses: dict[str, RecordedResponse]
    """By URL path, without the query string."""

    @classmethod
    def load(cls, path: Path) -> Recording:
        raw = json.loads(path.read_text())
        return cls(
            recorded_at=datetime.fromisoformat(raw["recorded_at"]),
            api_version=raw["api_version"],
            responses={
                url_path: RecordedResponse(status=response["status"], body=response["body"])
                for url_path, response in raw["responses"].items()
            },
        )


def _shift_timestamp(value: str, delta: timedelta) -> str:
    timestamp = datetime.fromisoformat(value)
    if timestamp.year < 1970:
        # A placeholder for "never", not a point in time.
        return value
    return (timestamp + delta).isoformat()


def shift_timestamps(value: object, delta: timedelta) -> object:
    match value:
        case str() if _ISO_TIMESTAMP.fullmatch(value):
            return _shift_timestamp(value, delta)
        case list():
            return [shift_timestamps(item, delta) for item in value]
        case dict():
            return {key: shift_timestamps(item, delta) for key, item in value.items()}
        case _:
            return value


def _accepts_login(
    api_version: str, credentials: Credentials, headers: dict[str, str], body: bytes
) -> bool:
    """Reject what a real server rejects: an API version it does not know, or wrong credentials."""
    if (version := _header(headers, "x-api-version")) != api_version:
        raise AssertionError(
            f"API version {version} is not supported, the responses were recorded with {api_version}"
        )
    form = dict(parse_qsl(body.decode()))
    match form.get("grant_type"):
        case "password":
            accepted = (form.get("username"), form.get("password")) == (
                credentials.user,
                credentials.password,
            )
        case "refresh_token":
            accepted = form.get("refresh_token") == _REFRESH_TOKEN
        case _:
            accepted = False
    if not accepted:
        raise AssertionError("Invalid credentials")
    return True


def _has_access_token(headers: dict[str, str], body: bytes) -> bool:  # noqa: ARG001
    if _header(headers, "authorization") != f"Bearer {_ACCESS_TOKEN}":
        raise AssertionError("Missing or invalid access token")
    return True


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((value for key, value in headers.items() if key.lower() == name), None)


def _replayed_body(
    recording: Recording,
    recorded: RecordedResponse,
    headers: dict[str, str],  # noqa: ARG001
    body: bytes,  # noqa: ARG001
) -> bytes:
    # A list is recorded in full and answered as a single page, whatever page was asked
    # for: the agent stops paging once it has all items.
    delta = datetime.now(tz=UTC) - recording.recorded_at
    return json.dumps(shift_timestamps(recorded.body, delta)).encode()


@contextmanager
def replaying(recording_file: Path, *, credentials: Credentials, address: str) -> Generator[int]:
    """Answer with the recorded responses to anyone logging in with `credentials`.

    Listens on a free port, which it yields.
    """
    recording = Recording.load(recording_file)
    with (
        tempfile.TemporaryDirectory() as cert_dir,
        MockServer(host=address, https=True, cert_dir=Path(cert_dir), ignore_query=True) as server,
    ):
        server.add_endpoint(
            MockEndpoint(MockMethod.POST, TOKEN_PATH),
            MockResponse(
                HTTPStatus.OK,
                _TOKEN_RESPONSE,
                request_validator=partial(_accepts_login, recording.api_version, credentials),
            ),
        )
        for url_path, recorded in recording.responses.items():
            server.add_endpoint(
                MockEndpoint(MockMethod.GET, url_path),
                MockResponse(
                    recorded.status,
                    partial(_replayed_body, recording, recorded),
                    request_validator=_has_access_token,
                ),
            )
        yield server.server.server_address[1]
