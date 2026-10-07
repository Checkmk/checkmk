#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_veeam

Checkmk special agent for Veeam Backup & Replication.

Queries the REST API of a Veeam backup server over the network, so that nothing
has to be installed on the backup server itself.
"""

import argparse
import json
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, UTC
from http import HTTPStatus
from typing import override
from urllib.parse import quote

import requests
import requests.auth
import urllib3
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cmk.password_store.v1 import parser_add_secret_option, resolve_secret_option, Secret
from cmk.plugins.veeam.lib import parse_iso8601_epoch
from cmk.server_side_programs.v1 import HostnameValidationAdapter, report_agent_crashes, Storage

AGENT = "veeam"

__version__ = "3.0.0b1"

PASSWORD_OPTION = "password"

API_VERSION = "1.3-rev1"
MIN_VEEAM_VERSION = "13.0.1.180"
"""The first Veeam Backup & Replication build that supports `API_VERSION`."""
TOKEN_PATH = "/api/oauth2/token"

TOKEN_STORAGE_KEY = "token"
MIN_TOKEN_VALIDITY = 60
"""Seconds a stored access token must still be valid to be reused at agent start."""


@dataclass(frozen=True, kw_only=True)
class Fetched:
    """A section rendered with its `<<<name:sep(0)>>>` header: for the Veeam server
    itself (`own`) and per piggyback host (`piggyback`, without the host envelope)."""

    own: str = ""
    piggyback: Mapping[str, str] = field(default_factory=dict)


type FetchStrategy = Callable[["VeeamClient", str], Fetched]
"""Fetches a section's data and renders it. Takes the client and the section name;
which API path(s) to call is baked into the strategy itself."""

type Section = tuple[str, FetchStrategy]
"""The agent section name and how to fetch it."""


class TerminateAgent(RuntimeError):
    """An error that makes the whole run pointless.

    Terminate the agent with a user facing message, but do not create a crash report.
    """


class VeeamApiError(RuntimeError):
    """The REST API answered a request with an HTTP error."""

    def __init__(self, path: str, response: requests.Response) -> None:
        self.status = response.status_code
        self.code, self.message = self._code_and_message(response)
        super().__init__(f"Request to {path} failed with HTTP {self.status}: {self.message}")

    @staticmethod
    def _code_and_message(response: requests.Response) -> tuple[str, str]:
        try:
            body = response.json()
        except json.JSONDecodeError:
            return "", response.text.strip() or (response.reason or "")
        if not isinstance(body, dict):
            return "", str(body)
        return str(body.get("errorCode") or ""), str(body.get("message") or "")


class _TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class _StoredToken(BaseModel):
    owner: str
    """The user and server the token was issued for."""
    access_token: str
    refresh_token: str
    """Can be used only once, and outlives the access token (14 days by default)."""
    expires_at: float
    """Expiry of the access token, as local unix time: immune to clock skew with the server."""


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--user", required=True, help="Veeam user name")
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", required=True, help="Password of the Veeam user"
    )
    parser.add_argument(
        "--port", type=int, default=9419, help="Port of the Veeam REST API (default: 9419)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for each request to the REST API (default: 30)",
    )

    tls = parser.add_mutually_exclusive_group(required=True)
    tls.add_argument(
        "--cert-server-name",
        help="Validate the server certificate against this host name",
    )
    tls.add_argument(
        "--disable-cert-verification",
        action="store_true",
        help="Do not verify the server certificate",
    )

    parser.add_argument(
        "--sections",
        type=_parse_sections,
        default=[name for name, _ in SECTIONS],
        metavar="SECTION,...",
        help=(
            "Comma-separated list of sections to fetch (default: all). A selected "
            "section that cannot be fetched terminates the agent."
        ),
    )

    parser.add_argument("address", help="Address of the Veeam backup server")

    return parser.parse_args(argv)


def base_url(address: str, port: int) -> str:
    return f"https://{address}:{port}"


def create_session(url: str, cert_server_name: str | None) -> requests.Session:
    """Build the session used for all API calls.

    We may be talking to an IP address while the certificate is issued for a host
    name, so certificate validation is pinned to `cert_server_name` rather than to
    whatever we dialled.
    """
    session = requests.Session()
    if cert_server_name is None:
        session.verify = False
        # The user opted out of verification; warning on every request is just noise.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    else:
        session.mount(url, HostnameValidationAdapter(cert_server_name))
    return session


class VeeamApi:
    """The transport for all requests to the REST API, with or without a token."""

    def __init__(
        self,
        session: requests.Session,
        url: str,
        *,
        cert_server_name: str | None,
        timeout: int,
    ) -> None:
        self._session = session
        self.url = url
        self._cert_server_name = cert_server_name
        self._timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        data: Mapping[str, str] | None = None,
        auth: requests.auth.AuthBase | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> requests.Response:
        try:
            # Pass `verify` explicitly, otherwise REQUESTS_CA_BUNDLE would override it.
            return self._session.request(
                method,
                f"{self.url}{path}",
                timeout=self._timeout,
                verify=self._session.verify,
                data=data,
                auth=auth,
                headers=headers,
            )
        except requests.exceptions.SSLError as exc:
            if self._cert_server_name is None:
                raise TerminateAgent(
                    f"The TLS handshake with the Veeam backup server at {self.url} failed ({exc})"
                ) from exc
            raise TerminateAgent(
                f"The certificate of the Veeam backup server was rejected: it could not be "
                f"validated against the host name '{self._cert_server_name}'. Configure the "
                f"correct certificate server name or disable certificate verification in the "
                f"rule ({exc})"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise TerminateAgent(
                f"The Veeam backup server at {self.url} did not answer within "
                f"{self._timeout} seconds"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise TerminateAgent(
                f"The Veeam backup server at {self.url} is unreachable ({exc})"
            ) from exc


class VeeamAuth(requests.auth.AuthBase):
    """Owns the access token: reuses the stored one, refreshes it, or logs in with the password.

    Pass it as `auth` to each API request rather than setting it on the session, so that
    the token requests themselves go out without it.
    """

    def __init__(
        self,
        api: VeeamApi,
        *,
        storage: Storage,
        user: str,
        password: Secret[str],
    ) -> None:
        self._api = api
        self._storage = storage
        self._user = user
        self._password = password
        self._owner = f"{user}@{api.url}"
        self._token: _StoredToken | None = None

    @override
    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.headers["x-api-version"] = API_VERSION
        # Without a token the request goes out unauthenticated; its 401 triggers renew().
        if self._token is not None:
            r.headers["Authorization"] = f"Bearer {self._token.access_token}"
        return r

    def _load_token(self) -> _StoredToken | None:
        if (raw := self._storage.read(TOKEN_STORAGE_KEY, None)) is None:
            return None
        try:
            token = _StoredToken.model_validate_json(raw)
        except ValidationError:
            return None
        return token if token.owner == self._owner else None

    def _request_token(self, data: Mapping[str, str]) -> _StoredToken:
        requested_at = time.time()
        response = self._api.request(
            "POST", TOKEN_PATH, data=data, headers={"x-api-version": API_VERSION}
        )
        if not response.ok:
            raise VeeamApiError(TOKEN_PATH, response)
        try:
            token = _TokenResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise TerminateAgent(
                "The Veeam REST API returned an invalid access token response"
            ) from exc
        stored = _StoredToken(
            owner=self._owner,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=requested_at + token.expires_in,
        )
        # Store right away: the refresh token we just used is gone for good.
        self._storage.write(TOKEN_STORAGE_KEY, stored.model_dump_json())
        return stored

    def _refresh(self, token: _StoredToken) -> _StoredToken | None:
        try:
            return self._request_token(
                {"grant_type": "refresh_token", "refresh_token": token.refresh_token}
            )
        except VeeamApiError as exc:
            if 400 <= exc.status < 500:
                # Expired, already used or revoked. The password login will tell if it's worse.
                return None
            raise TerminateAgent(
                f"Refreshing the access token at the Veeam REST API failed with HTTP "
                f"{exc.status}: {exc.message}"
            ) from exc

    def _login(self) -> _StoredToken:
        try:
            return self._request_token(
                {
                    "grant_type": "password",
                    "username": self._user,
                    "password": self._password.reveal(),
                }
            )
        except VeeamApiError as exc:
            if exc.status == HTTPStatus.BAD_REQUEST and exc.code == "NotImplemented":
                raise TerminateAgent(
                    f"The Veeam backup server does not support the REST API version "
                    f"{API_VERSION}. Veeam Backup & Replication {MIN_VEEAM_VERSION} or later "
                    f"is required (server: {exc.message})"
                ) from exc
            if exc.status == HTTPStatus.UNAUTHORIZED:
                raise TerminateAgent(
                    f"Authentication at the Veeam REST API failed for user '{self._user}': "
                    f"{exc.message}. Check the user name and password"
                ) from exc
            raise TerminateAgent(
                f"Login at the Veeam REST API failed with HTTP {exc.status}: {exc.message}"
            ) from exc

    def renew(self) -> None:
        """Replace the current token: spend its refresh token, fall back to the password."""
        refreshed = self._refresh(self._token) if self._token is not None else None
        self._token = refreshed if refreshed is not None else self._login()

    def authenticate(self) -> None:
        """Reuse the stored access token if it is still valid long enough, renew it otherwise."""
        self._token = self._load_token()
        if self._token is None or self._token.expires_at - time.time() < MIN_TOKEN_VALIDITY:
            self.renew()


class VeeamClient:
    def __init__(self, api: VeeamApi, auth: VeeamAuth, storage: Storage) -> None:
        self._api = api
        self._auth = auth
        self.storage = storage

    def get(self, path: str) -> object:
        response = self._api.request("GET", path, auth=self._auth)
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            # The token expired mid-run or was revoked: renew it and try once more.
            self._auth.renew()
            response = self._api.request("GET", path, auth=self._auth)
        if response.ok:
            return response.json()
        error = VeeamApiError(path, response)
        if error.status == HTTPStatus.UNAUTHORIZED:
            raise TerminateAgent(
                f"The Veeam REST API rejected the session on {path}: {error.message}"
            ) from error
        if error.status == HTTPStatus.FORBIDDEN:
            raise TerminateAgent(
                f"Access to {path} was denied (HTTP 403): {error.message} "
                f"(the Veeam user lacks a role required for this endpoint)"
            ) from error
        raise TerminateAgent(str(error)) from error


def _get_all(
    client: VeeamClient,
    path: str,
    limit: int | None = None,
    extra_params: str = "",
) -> list[object]:
    """Fetch every page of a `data`/`pagination` endpoint and merge them.

    `extra_params` is appended verbatim to every page's query string, e.g.
    "&typeFilter=Backup"; it must already be percent-encoded where needed.
    """
    items: list[object] = []
    skip = 0
    page_size = "" if limit is None else f"&limit={limit}"
    while True:
        page = client.get(f"{path}?skip={skip}{page_size}{extra_params}")
        if not isinstance(page, dict) or "data" not in page or "pagination" not in page:
            raise TerminateAgent(f"Request to {path} did not return a paginated data list")
        batch = page["data"]
        total = page["pagination"]["total"]
        if not batch and len(items) < total:
            raise TerminateAgent(
                f"Request to {path} returned an empty page before reaching {total} total items"
            )
        items.extend(batch)
        # Advance by the number of items actually returned, not the requested page size
        skip += len(batch)
        if len(items) >= total:
            return items


def fetch_object(path: str) -> FetchStrategy:
    """A single-object endpoint (no `data`/`pagination` envelope), e.g. /api/v1/serverInfo."""

    def _fetch(client: VeeamClient, name: str) -> Fetched:
        return Fetched(own=f"<<<{name}:sep(0)>>>\n{json.dumps(client.get(path))}\n")

    return _fetch


def fetch_list(path: str) -> FetchStrategy:
    """A `data`/`pagination` endpoint, fetched to completion, one item per line."""

    def _fetch(client: VeeamClient, name: str) -> Fetched:
        items = _get_all(client, path)
        return Fetched(
            own=f"<<<{name}:sep(0)>>>\n" + "".join(f"{json.dumps(item)}\n" for item in items)
        )

    return _fetch


_MALWARE_SEVERITY = {"Clean": 0, "Informative": 1, "Suspicious": 2, "Infected": 3}
_UNKNOWN_MALWARE_SEVERITY = len(_MALWARE_SEVERITY)


def _malware_severity(status: object) -> int:
    if not isinstance(status, str):
        return _UNKNOWN_MALWARE_SEVERITY
    return _MALWARE_SEVERITY.get(status, _UNKNOWN_MALWARE_SEVERITY)


def _malware_rollup(points: Sequence[Mapping[str, object]]) -> object:
    """The worst malware status of all restore points. An unknown status counts as
    worst, so that it surfaces in the check. A missing status means the point was not
    scanned (Veeam does not scan file share backups) and is ignored."""
    return max(
        (status for point in points if (status := point.get("malwareStatus")) is not None),
        key=_malware_severity,
        default=None,
    )


def _newest(points: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    dated = [
        (epoch, point)
        for point in points
        if isinstance(created := point.get("creationTime"), str)
        and (epoch := parse_iso8601_epoch(created)) is not None
    ]
    return max(dated, key=lambda item: item[0])[1] if dated else None


def _restore_point_object_id(
    point: Mapping[str, object], candidates: Sequence[Mapping[str, object]]
) -> str | None:
    """Picks which of a backup chain's object(s) a restore point belongs to.

    A chain with one object is unambiguous: take it directly, since the point's
    own `name` cannot be trusted to match the object's `name` (e.g. a Linux agent's
    point is named by IP, the object by hostname). A chain shared by several
    objects (e.g. a multi-folder File Backup job) has no such guarantee, but Veeam
    suffixes each such point's name with " Id: <n>"; stripping that back out of the
    point's name is what actually identifies which object it belongs to.
    """
    if len(candidates) == 1:
        object_id = candidates[0].get("id")
        return object_id if isinstance(object_id, str) else None
    point_name = point.get("name")
    if not isinstance(point_name, str):
        return None
    base_name = point_name.rsplit(" Id: ", 1)[0]
    for obj in candidates:
        if obj.get("name") == base_name and isinstance(object_id := obj.get("id"), str):
            return object_id
    return None


def _total_count(backup_objects: Sequence[Mapping[str, object]]) -> int | None:
    counts = [backup_object.get("restorePointsCount") for backup_object in backup_objects]
    ints = [count for count in counts if isinstance(count, int)]
    return sum(ints) if len(ints) == len(counts) else None


def fetch_restore_points(limit: int = 500) -> FetchStrategy:
    """One record per backed up machine: its newest restore point and a malware rollup,
    piggybacked onto the machine's host.

    The host is the object's name in its backup chain
    (GET /api/v1/backups/{backupId}/objects), the identity `fetch_backups` uses too, or
    its name in GET /api/v1/backupObjects if the chain could not be resolved. Every chain
    (GET /api/v1/backups) is resolved, so that an object without restore points lands on
    the same host as the others. A machine backed up by several jobs has one backup
    object per job; they are merged on the host.

    Restore points reference their chain via `backupId`; a point whose chain could not
    be resolved is joined by name and platform instead, if possible. See `_restore_point_object_id` for how a point is
    attributed to one of several objects sharing a chain.
    """

    def _fetch(client: VeeamClient, name: str) -> Fetched:
        backup_objects = _get_all(client, "/api/v1/backupObjects", limit)
        restore_points = _get_all(client, "/api/v1/restorePoints", limit)

        backup_ids = {
            backup_id
            for backup in _get_all(client, "/api/v1/backups", limit)
            if isinstance(backup, dict) and isinstance(backup_id := backup.get("id"), str)
        } | {
            backup_id
            for point in restore_points
            if isinstance(point, dict) and isinstance(backup_id := point.get("backupId"), str)
        }
        objects_by_backup_id: dict[str, list[Mapping[str, object]]] = {}
        for backup_id in backup_ids:
            try:
                objects = _get_all(client, f"/api/v1/backups/{backup_id}/objects", limit)
            except TerminateAgent as exc:
                if (
                    isinstance(exc.__cause__, VeeamApiError)
                    and exc.__cause__.status != HTTPStatus.UNAUTHORIZED
                ):
                    continue
                raise
            objects_by_backup_id[backup_id] = [obj for obj in objects if isinstance(obj, dict)]

        object_id_by_name_platform: dict[tuple[str, str], str] = {
            (obj_name, obj_platform_id): object_id
            for obj in backup_objects
            if isinstance(obj, dict)
            and isinstance(obj_name := obj.get("name"), str)
            and isinstance(obj_platform_id := obj.get("platformId"), str)
            and isinstance(object_id := obj.get("id"), str)
        }

        points: dict[str, list[Mapping[str, object]]] = {}
        for point in restore_points:
            if not isinstance(point, dict) or not isinstance(
                backup_id := point.get("backupId"), str
            ):
                continue
            candidates = objects_by_backup_id.get(backup_id, [])
            object_id = _restore_point_object_id(point, candidates)
            if (
                object_id is None
                and not candidates
                and isinstance(point_name := point.get("name"), str)
                and isinstance(point_platform_id := point.get("platformId"), str)
            ):
                # The chain's objects couldn't be resolved via id at all (lookup
                # failed or unsupported); fall back to the pre-id join, which
                # still works where the point's own name matches the object's.
                object_id = object_id_by_name_platform.get((point_name, point_platform_id))
            if object_id is not None:
                points.setdefault(object_id, []).append(point)

        host_by_object_id: dict[str, str] = {
            object_id: host
            for objects in objects_by_backup_id.values()
            for obj in objects
            if isinstance(object_id := obj.get("id"), str)
            and isinstance(host := obj.get("name"), str)
            and host
        }
        machines: dict[str, list[Mapping[str, object]]] = {}
        for backup_object in backup_objects:
            if (
                isinstance(backup_object, dict)
                and isinstance(object_id := backup_object.get("id"), str)
                and isinstance(
                    host := host_by_object_id.get(object_id, backup_object.get("name")), str
                )
                and host
            ):
                machines.setdefault(host, []).append(backup_object)

        piggyback: dict[str, str] = {}
        for host, machine_objects in machines.items():
            machine_points = [
                point for obj in machine_objects for point in points.get(str(obj["id"]), [])
            ]
            newest = _newest(machine_points)
            # The object holding the newest point, so that its type matches the point
            owner = next(
                (
                    obj
                    for obj in machine_objects
                    if any(p is newest for p in points.get(str(obj["id"]), []))
                ),
                machine_objects[0],
            )
            record = {
                "platformName": owner.get("platformName"),
                "type": owner.get("type"),
                "restorePointsCount": _total_count(machine_objects),
                "lastRestorePoint": (
                    None
                    if newest is None
                    else {
                        "creationTime": newest.get("creationTime"),
                        "type": newest.get("type"),
                        "malwareStatus": newest.get("malwareStatus"),
                    }
                ),
                "malwareStatus": _malware_rollup(machine_points),
            }
            piggyback[host] = f"<<<{name}:sep(0)>>>\n{json.dumps(record)}\n"
        return Fetched(piggyback=piggyback)

    return _fetch


def _job_sessions_and_window(
    jobs: list[object],
) -> tuple[dict[str, tuple[str, str]], str | None]:
    """Builds `sessionId -> (job id, job name)` from each job's current session,
    plus the earliest `lastRun` (the taskSessions window's lower bound).

    Disabled jobs are excluded, like the old plug-in; a schedule-disabled job is
    still included. Jobs that never ran don't affect the window.

    TODO: a rarely-run job drags the window back every cycle; cap it (e.g. 30
    days) if that becomes a real problem.
    """
    session_to_job: dict[str, tuple[str, str]] = {}
    last_runs: list[float] = []
    for job in jobs:
        if not isinstance(job, dict) or job.get("status") == "Disabled":
            continue
        session_id, job_id, job_name = job.get("sessionId"), job.get("id"), job.get("name")
        if isinstance(session_id, str) and isinstance(job_id, str) and isinstance(job_name, str):
            session_to_job[session_id] = (job_id, job_name)
        last_run = job.get("lastRun")
        if isinstance(last_run, str) and (epoch := parse_iso8601_epoch(last_run)) is not None:
            last_runs.append(epoch)

    if not last_runs:
        return session_to_job, None
    return session_to_job, datetime.fromtimestamp(min(last_runs), tz=UTC).isoformat()


def _task_creation_epoch(task: Mapping[str, object]) -> float:
    created = task.get("creationTime")
    if isinstance(created, str) and (epoch := parse_iso8601_epoch(created)) is not None:
        return epoch
    return float("-inf")


class _SessionResult(BaseModel):
    result: str
    message: str | None = None


class _SessionInfo(BaseModel):
    """The subset of SessionModel (GET /api/v1/sessions/{id}) we rely on."""

    model_config = ConfigDict(populate_by_name=True)

    state: str | None = None
    result: _SessionResult | None = None
    creation_time: str | None = Field(default=None, alias="creationTime")
    end_time: str | None = Field(default=None, alias="endTime")
    resource_id: str | None = Field(default=None, alias="resourceId")


@dataclass(frozen=True, kw_only=True)
class _JobObjects:
    names: list[str]
    job_name: str
    session: _SessionInfo
    """The job's current session; used for the single-object fallback in
    `fetch_backups`."""


def _is_skippable(exc: TerminateAgent) -> bool:
    """A failed per-job lookup that should just skip that job, not abort the agent."""
    return isinstance(exc.__cause__, VeeamApiError) and exc.__cause__.status in (
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.NOT_FOUND,
    )


JOB_OBJECT_NAMES_STORAGE_KEY = "job_object_names"


class _CachedJobCollection(BaseModel):
    session_id: str
    names: list[str]
    session: _SessionInfo


def _load_job_object_names_cache(storage: Storage) -> Mapping[str, _CachedJobCollection]:
    try:
        raw = json.loads(storage.read(JOB_OBJECT_NAMES_STORAGE_KEY, "{}"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    cache: dict[str, _CachedJobCollection] = {}
    for job_id, entry in raw.items():
        if not isinstance(job_id, str):
            continue
        try:
            cache[job_id] = _CachedJobCollection.model_validate(entry)
        except ValidationError:
            continue
    return cache


def _resolve_job_object_names(
    client: VeeamClient, session_to_job: Mapping[str, tuple[str, str]]
) -> dict[str, _JobObjects]:
    """Maps job ID -> its current session's object name(s), via
    GET /api/v1/sessions/{sessionId} -> resourceId -> GET /api/v1/backups/{id}/objects.

    Iterates `session_to_job` (built by `_job_sessions_and_window`) rather than the
    raw job list, so disabled/malformed jobs are filtered in one place only.

    Same identity as /api/v1/restorePoints and the old plug-in (e.g.
    "ip-172-31-26-65"), unlike taskSessions' own `name` (e.g. the raw IP for the
    same object) — and resolvable even for jobs taskSessions never has a task for
    at all (Agent Backup).

    /api/v1/backups/{id}/objects 400s under rev0 for File Backup jobs; rev1 fixes
    it, and the negotiated version already prefers rev1 when available. A job
    whose session/objects lookup 404s/400s is left out.

    The result is cached per job, keyed by the job's own current `sessionId`: a job
    whose session hasn't changed since the last run reuses its cached names/session
    instead of repeating both requests. Only a session whose own `state` is
    "Stopped" is cached, though: an in-progress session's `state`/`result`/`endTime`
    still change in place under the same `sessionId`, so caching it would freeze a
    job's single-object session fallback (`_session_fallback_task`) on a stale
    in-progress snapshot until the job's next run. A job no longer present this run
    is simply dropped from the cache.
    """
    old_cache = _load_job_object_names_cache(client.storage)
    new_cache: dict[str, _CachedJobCollection] = {}
    objects_by_job: dict[str, _JobObjects] = {}
    for session_id, (job_id, job_name) in session_to_job.items():
        cached_entry = old_cache.get(job_id)
        if cached_entry is not None and cached_entry.session_id == session_id:
            objects_by_job[job_id] = _JobObjects(
                names=cached_entry.names, job_name=job_name, session=cached_entry.session
            )
            new_cache[job_id] = cached_entry
            continue
        try:
            raw_session = client.get(f"/api/v1/sessions/{session_id}")
        except TerminateAgent as exc:
            if _is_skippable(exc):
                continue
            raise
        try:
            session_info = _SessionInfo.model_validate(raw_session)
        except ValidationError:
            continue
        if session_info.resource_id is None:
            continue
        try:
            objects = _get_all(client, f"/api/v1/backups/{session_info.resource_id}/objects")
        except TerminateAgent as exc:
            if _is_skippable(exc):
                continue
            raise
        names = [
            object_name
            for obj in objects
            if isinstance(obj, dict)
            and isinstance(object_name := obj.get("name"), str)
            and object_name
        ]
        if names:
            objects_by_job[job_id] = _JobObjects(
                names=names, job_name=job_name, session=session_info
            )
            if session_info.state == "Stopped":
                new_cache[job_id] = _CachedJobCollection(
                    session_id=session_id, names=names, session=session_info
                )
    client.storage.write(
        JOB_OBJECT_NAMES_STORAGE_KEY,
        json.dumps({job_id: entry.model_dump() for job_id, entry in new_cache.items()}),
    )
    return objects_by_job


def _format_dotnet_timespan(seconds: float) -> str:
    total_seconds = int(seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return (
        f"{days}.{hours:02d}:{minutes:02d}:{secs:02d}"
        if days
        else f"{hours:02d}:{minutes:02d}:{secs:02d}"
    )


def _session_fallback_task(session: _SessionInfo, job_name: str) -> Mapping[str, object]:
    """Builds a taskSessions-shaped record from a job's own session, for a
    single-object job taskSessions has no task for. A session has no per-task
    progress breakdown (size, read, transferred, rate), so those are left out."""
    duration = None
    if (
        session.creation_time is not None
        and session.end_time is not None
        and (created_epoch := parse_iso8601_epoch(session.creation_time)) is not None
        and (end_epoch := parse_iso8601_epoch(session.end_time)) is not None
    ):
        duration = _format_dotnet_timespan(end_epoch - created_epoch)
    return {
        "state": session.state,
        "result": session.result.model_dump(exclude_none=True) if session.result else None,
        "progress": {"duration": duration} if duration is not None else {},
        "endTime": session.end_time,
        "jobName": job_name,
    }


def fetch_backups(client: VeeamClient, name: str) -> Fetched:
    """One record per (job, object) pair: the newest task for that pairing,
    labelled with the job's name.

    Piggyback identity comes from `_resolve_job_object_names`, not a task's own
    `name` (the two disagree for some platforms, e.g. Agent Backup). A
    single-object job takes all its tasks unconditionally; a multi-object job
    matches by name instead, which only works where the two sides agree
    (confirmed for File Backup). A single-object job left with no task falls
    back to its own session (`_session_fallback_task`); a multi-object job in
    that case is just left without data.

    A task's job is resolved by matching its `sessionId` against each job's
    current session (from /api/v1/jobs/states), not via a third endpoint. A task
    whose session isn't any job's current one is dropped; its piggyback host just
    keeps showing its last known state via normal staleness handling.

    /api/v1/taskSessions is windowed with `createdAfterFilter` (earliest job
    `lastRun`) rather than fetched in full, to avoid pulling the server's entire
    history every run.

    `sessionTypeFilter=BackupJob` isn't used: on VBR 13.0.3.63 it silently
    matches nothing even for matching records, so `sessionType` is filtered
    client-side instead.
    """
    jobs = _get_all(client, "/api/v1/jobs/states")
    session_to_job, created_after = _job_sessions_and_window(jobs)
    job_objects = _resolve_job_object_names(client, session_to_job)

    groups: dict[str, list[Mapping[str, object]]] = {}

    newest: dict[tuple[str, str], Mapping[str, object]] = {}

    if created_after is not None:
        tasks = _get_all(
            client,
            "/api/v1/taskSessions",
            extra_params=f"&typeFilter=Backup&createdAfterFilter={quote(created_after)}",
        )

        for task in tasks:
            if not isinstance(task, dict) or not isinstance(task_name := task.get("name"), str):
                continue
            if task.get("sessionType") != "BackupJob":
                continue
            session_id = task.get("sessionId")
            if not isinstance(session_id, str) or (job := session_to_job.get(session_id)) is None:
                continue
            job_id, job_name = job
            resolved_names = job_objects[job_id].names if job_id in job_objects else []
            if len(resolved_names) == 1:
                object_name = resolved_names[0]
            elif task_name in resolved_names:
                object_name = task_name
            else:
                continue
            key = (object_name, job_id)
            current = newest.get(key)
            # TODO: ties (identical creationTime) are broken arbitrarily, by whichever
            # task is encountered last. A real tiebreak would compare `usn` (an
            # increasing update sequence number) instead, e.g.:
            #     task.get("usn", -1) >= current.get("usn", -1)
            # left out for now since such collisions are assumed to be rare.
            if current is None or _task_creation_epoch(task) >= _task_creation_epoch(current):
                newest[key] = {**task, "jobName": job_name}

    # Single-object jobs that /api/v1/taskSessions has no task for at all (e.g. the
    # Linux/Windows Agent Backup gap) fall back to the job's own session: with only
    # one object, the job's result already *is* that object's result.
    for job_id, job_obj in job_objects.items():
        if len(job_obj.names) != 1 or job_obj.session.state is None:
            continue
        key = (job_obj.names[0], job_id)
        if key not in newest:
            newest[key] = _session_fallback_task(job_obj.session, job_obj.job_name)

    for (object_name, _job_id), task in newest.items():
        groups.setdefault(object_name, []).append(task)

    return Fetched(
        piggyback={
            object_name: f"<<<{name}:sep(0)>>>\n"
            + "".join(f"{json.dumps(task)}\n" for task in object_tasks)
            for object_name, object_tasks in groups.items()
        }
    )


def write_sections(client: VeeamClient, sections: Sequence[Section]) -> None:
    """Each piggyback host is written once, with the sections of all fetches for it."""
    piggyback: dict[str, list[str]] = {}
    for name, fetch in sections:
        fetched = fetch(client, name)
        sys.stdout.write(fetched.own)
        for host, text in fetched.piggyback.items():
            piggyback.setdefault(host, []).append(text)
    for host, texts in piggyback.items():
        sys.stdout.write(f"<<<<{host}>>>>\n{''.join(texts)}<<<<>>>>\n")


SECTIONS: Sequence[Section] = (
    ("veeam_server_info", fetch_object("/api/v1/serverInfo")),
    ("veeam_license", fetch_object("/api/v1/license")),
    ("veeam_backup_jobs", fetch_list("/api/v1/jobs/states")),
    ("veeam_backups", fetch_backups),
    ("veeam_replicas", fetch_list("/api/v1/replicas")),
    ("veeam_protection_groups", fetch_list("/api/v1/agents/protectionGroups")),
    ("veeam_managed_servers", fetch_list("/api/v1/backupInfrastructure/managedServers")),
    ("veeam_wan_accelerators", fetch_list("/api/v1/backupInfrastructure/wanAccelerators")),
    ("veeam_config_backup", fetch_object("/api/v1/configBackup")),
    ("veeam_proxies", fetch_list("/api/v1/backupInfrastructure/proxies/states")),
    (
        "veeam_scaleout_repositories",
        fetch_list("/api/v1/backupInfrastructure/scaleOutRepositories"),
    ),
    ("veeam_restore_points", fetch_restore_points()),
    (
        "veeam_repositories",
        fetch_list("/api/v1/backupInfrastructure/repositories/states"),
    ),
)


def _parse_sections(value: str) -> list[str]:
    """Parse the `--sections` value: a comma-separated list of known section names."""
    known = {name for name, _ in SECTIONS}
    selected = value.split(",")
    if unknown := [name for name in selected if name not in known]:
        raise argparse.ArgumentTypeError(f"unknown section(s): {', '.join(unknown)}")
    return selected


@report_agent_crashes(AGENT, __version__)
def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(sys.argv[1:] if argv is None else argv)
    url = base_url(args.address, args.port)
    cert_server_name = None if args.disable_cert_verification else args.cert_server_name

    try:
        with create_session(url, cert_server_name) as session:
            api = VeeamApi(session, url, cert_server_name=cert_server_name, timeout=args.timeout)
            storage = Storage(AGENT, host=args.address)
            auth = VeeamAuth(
                api,
                storage=storage,
                user=args.user,
                password=resolve_secret_option(args, PASSWORD_OPTION),
            )
            auth.authenticate()
            wanted = set(args.sections)
            selected = [section for section in SECTIONS if section[0] in wanted]
            write_sections(VeeamClient(api, auth, storage), selected)
    except TerminateAgent as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
