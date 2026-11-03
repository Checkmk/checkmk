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
import logging
import sys
import time
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import override

import requests
import requests.auth
import urllib3
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from cmk.password_store.v1 import parser_add_secret_option, resolve_secret_option, Secret
from cmk.plugins.veeam.lib import parse_iso8601_epoch
from cmk.server_side_programs.v1 import (
    AgentMessages,
    HostnameValidationAdapter,
    report_agent_crashes,
    Storage,
)

AGENT = "veeam"

_LOGGER = logging.getLogger(__name__)

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


class AccessDenied(RuntimeError):
    """The Veeam user may not read an endpoint (HTTP 403)."""

    def __init__(self, path: str) -> None:
        self.endpoint = path.split("?", 1)[0]
        super().__init__(f"Access to {self.endpoint} was denied (HTTP 403)")


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
        "--port",
        type=int,
        default=443,
        help="Port of the Veeam REST API (default: 443)",
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
                    f"{exc.message}. Check the user name and password. After repeated "
                    "failed logins, Veeam may lock the user and then reject even the correct "
                    "password until the user is unlocked"
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
        self._lists: dict[tuple[str, str], list[object]] = {}

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
            raise AccessDenied(path) from error
        raise TerminateAgent(str(error)) from error

    def get_all(self, path: str, limit: int | None = None, extra_params: str = "") -> list[object]:
        """Fetch every page of a `data`/`pagination` endpoint and merge them.

        `extra_params` is appended verbatim to every page's query string, e.g.
        "&typeFilter=Backup"; it must already be percent-encoded where needed.

        The result is kept for the lifetime of this client (one agent run), so
        sections requesting the same list (e.g. /api/v1/jobs/states) share one
        fetch and see the same snapshot. `limit` only sets the page size, not
        the merged result, so it is not part of the cache key.
        """
        key = (path, extra_params)
        if (cached := self._lists.get(key)) is None:
            cached = self._lists[key] = self._fetch_all_pages(path, limit, extra_params)
        return list(cached)

    def _fetch_all_pages(self, path: str, limit: int | None, extra_params: str) -> list[object]:
        items: list[object] = []
        skip = 0
        page_size = "" if limit is None else f"&limit={limit}"
        while True:
            page = self.get(f"{path}?skip={skip}{page_size}{extra_params}")
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
        items = client.get_all(path)
        return Fetched(
            own=f"<<<{name}:sep(0)>>>\n" + "".join(f"{json.dumps(item)}\n" for item in items)
        )

    return _fetch


class _ApiItem(BaseModel):
    """An item of a REST API list, with the API's camelCase field names. A field is
    required exactly when the API schema (/swagger/v1.3-rev1/swagger.json) requires it."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


def _parse_items[Item: _ApiItem](model: type[Item], items: Iterable[object]) -> list[Item]:
    """The items that fit `model`; one that doesn't is skipped rather than fatal."""
    parsed: list[Item] = []
    for item in items:
        try:
            parsed.append(model.model_validate(item))
        except ValidationError as exc:
            _LOGGER.debug(
                "Skipping an item that does not fit %(model)s: %(error)s",
                {"model": model.__name__, "error": exc},
            )
    return parsed


class _Backup(_ApiItem):
    """An item of GET /api/v1/backups."""

    id: str
    job_id: str | None = None


class _SessionProgress(_ApiItem):
    """The `sessionProgress` of a job in GET /api/v1/jobs/states: totals of its current
    session, over all of the job's objects."""

    # Required by the API schema, but VBR 13 leaves some out (seen for a File Backup job).
    processed_size: int | None = None
    read_size: int | None = None
    transferred_size: int | None = None


class _Job(_ApiItem):
    """An item of GET /api/v1/jobs."""

    id: str
    is_disabled: bool


def _disabled_job_ids(client: VeeamClient) -> frozenset[str]:
    """The ids of the jobs that are disabled in Veeam.

    `status` in GET /api/v1/jobs/states is only "Disabled" for agent policies; a disabled
    agent backup or file backup job stays "Stopped". `isDisabled` in GET /api/v1/jobs is
    set for every job type.
    """
    return frozenset(
        job.id for job in _parse_items(_Job, client.get_all("/api/v1/jobs")) if job.is_disabled
    )


def fetch_backup_jobs(client: VeeamClient, name: str) -> Fetched:
    """GET /api/v1/jobs/states, one job per line, each with `isDisabled` added (see
    `_disabled_job_ids`)."""
    disabled_ids = _disabled_job_ids(client)
    return Fetched(
        own=f"<<<{name}:sep(0)>>>\n"
        + "".join(
            f"{json.dumps({**item, 'isDisabled': item.get('id') in disabled_ids})}\n"
            for item in client.get_all("/api/v1/jobs/states")
            if isinstance(item, dict)
        )
    )


class _JobState(_ApiItem):
    """An item of GET /api/v1/jobs/states."""

    id: str
    name: str
    status: str
    session_id: str | None = None
    session_progress: _SessionProgress | None = None


class _RestorePoint(_ApiItem):
    """An item of GET /api/v1/restorePoints."""

    backup_id: str
    parent_backup_id: str | None = None
    name: str
    # Required by the API schema, but only used for the name/platform fallback join, so a
    # missing value must not drop the restore point.
    platform_id: str | None = None
    creation_time: str
    type: str | None = None
    malware_status: str | None = None


class _BackupObject(_ApiItem):
    """An item of GET /api/v1/backupObjects and of GET /api/v1/backups/{backupId}/objects
    (both BackupObjectModel)."""

    id: str
    name: str | None = None
    platform_id: str | None = None
    # Required by the API schema, but only passed through, so a missing value must not drop
    # the object.
    platform_name: str | None = None
    type: str | None = None
    restore_points_count: int | None = None


_MALWARE_SEVERITY = {"Clean": 0, "Informative": 1, "Suspicious": 2, "Infected": 3}
_UNKNOWN_MALWARE_SEVERITY = len(_MALWARE_SEVERITY)


def _malware_severity(status: str) -> int:
    return _MALWARE_SEVERITY.get(status, _UNKNOWN_MALWARE_SEVERITY)


def _malware_rollup(points: Sequence[_RestorePoint]) -> str | None:
    """The worst malware status of all restore points. An unknown status counts as
    worst, so that it surfaces in the check. A missing status means the point was not
    scanned (Veeam does not scan file share backups) and is ignored."""
    return max(
        (point.malware_status for point in points if point.malware_status is not None),
        key=_malware_severity,
        default=None,
    )


def _newest(points: Sequence[_RestorePoint]) -> _RestorePoint | None:
    dated = [
        (epoch, point)
        for point in points
        if (epoch := parse_iso8601_epoch(point.creation_time)) is not None
    ]
    return max(dated, key=lambda item: item[0])[1] if dated else None


def _restore_point_object_id(
    point: _RestorePoint, candidates: Sequence[_BackupObject]
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
        return candidates[0].id
    base_name = point.name.rsplit(" Id: ", 1)[0]
    return next((obj.id for obj in candidates if obj.name == base_name), None)


def _total_count(backup_objects: Sequence[_BackupObject]) -> int | None:
    counts = [backup_object.restore_points_count for backup_object in backup_objects]
    ints = [count for count in counts if count is not None]
    return sum(ints) if len(ints) == len(counts) else None


BACKUP_OBJECTS_STORAGE_KEY = "backup_objects"


class _CachedBackupObjects(BaseModel):
    session_id: str
    objects: list[_BackupObject]


def _load_backup_objects_cache(storage: Storage) -> Mapping[str, _CachedBackupObjects]:
    try:
        raw = json.loads(storage.read(BACKUP_OBJECTS_STORAGE_KEY, "{}"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    cache: dict[str, _CachedBackupObjects] = {}
    for backup_id, entry in raw.items():
        try:
            cache[backup_id] = _CachedBackupObjects.model_validate(entry)
        except ValidationError:
            continue
    return cache


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

    A chain's objects only change when its job runs, so they are cached across runs and
    reused while the chain's job (`jobId` in GET /api/v1/backups) is still on the same
    session in GET /api/v1/jobs/states. Only a job whose `status` is "Stopped" counts, so
    a run in progress never caches or reuses an incomplete list. A chain without such a
    job is fetched every run.

    Veeam Agent jobs keep a separate per-machine chain for each computer, which
    GET /api/v1/backups does not list. Its job is found via the `parentBackupId` of its
    restore points: the job's own chain, which is listed.
    """

    def _fetch(client: VeeamClient, name: str) -> Fetched:
        backup_objects = _parse_items(_BackupObject, client.get_all("/api/v1/backupObjects", limit))
        restore_points = _parse_items(_RestorePoint, client.get_all("/api/v1/restorePoints", limit))
        backups = _parse_items(_Backup, client.get_all("/api/v1/backups", limit))
        jobs = _parse_items(_JobState, client.get_all("/api/v1/jobs/states"))

        backup_ids = {backup.id for backup in backups} | {
            point.backup_id for point in restore_points
        }
        job_id_by_backup_id = {
            backup.id: backup.job_id for backup in backups if backup.job_id is not None
        }
        job_id_by_backup_id |= {
            point.backup_id: job_id
            for point in restore_points
            if point.backup_id not in job_id_by_backup_id
            and point.parent_backup_id is not None
            and (job_id := job_id_by_backup_id.get(point.parent_backup_id)) is not None
        }
        finished_session_by_job_id = {
            job.id: job.session_id
            for job in jobs
            if job.status == "Stopped" and job.session_id is not None
        }

        old_cache = _load_backup_objects_cache(client.storage)
        new_cache: dict[str, _CachedBackupObjects] = {}
        objects_by_backup_id: dict[str, Sequence[_BackupObject]] = {}
        for backup_id in backup_ids:
            job_id = job_id_by_backup_id.get(backup_id)
            session_id = None if job_id is None else finished_session_by_job_id.get(job_id)
            if (cached := old_cache.get(backup_id)) is not None and cached.session_id == session_id:
                objects_by_backup_id[backup_id] = cached.objects
                new_cache[backup_id] = cached
                continue
            try:
                objects = client.get_all(f"/api/v1/backups/{backup_id}/objects", limit)
            except TerminateAgent as exc:
                if (
                    isinstance(exc.__cause__, VeeamApiError)
                    and exc.__cause__.status != HTTPStatus.UNAUTHORIZED
                ):
                    continue
                raise
            chain_objects = _parse_items(_BackupObject, objects)
            if len(chain_objects) != len(objects):
                # A partial list would attribute the skipped objects' restore points to the
                # others; leave the chain unresolved instead.
                continue
            objects_by_backup_id[backup_id] = chain_objects
            if session_id is not None:
                new_cache[backup_id] = _CachedBackupObjects(
                    session_id=session_id, objects=chain_objects
                )
        client.storage.write(
            BACKUP_OBJECTS_STORAGE_KEY,
            json.dumps({backup_id: entry.model_dump() for backup_id, entry in new_cache.items()}),
        )

        object_id_by_name_platform: dict[tuple[str, str], str] = {
            (obj.name, obj.platform_id): obj.id
            for obj in backup_objects
            if obj.name is not None and obj.platform_id is not None
        }

        points: dict[str, list[_RestorePoint]] = {}
        for point in restore_points:
            candidates = objects_by_backup_id.get(point.backup_id, [])
            object_id = _restore_point_object_id(point, candidates)
            if object_id is None and not candidates and point.platform_id is not None:
                # The chain's objects couldn't be resolved via id at all (lookup
                # failed or unsupported); fall back to the pre-id join, which
                # still works where the point's own name matches the object's.
                object_id = object_id_by_name_platform.get((point.name, point.platform_id))
            if object_id is not None:
                points.setdefault(object_id, []).append(point)

        host_by_object_id: dict[str, str] = {
            obj.id: obj.name
            for objects in objects_by_backup_id.values()
            for obj in objects
            if obj.name
        }
        machines: dict[str, list[_BackupObject]] = {}
        for backup_object in backup_objects:
            if host := host_by_object_id.get(backup_object.id, backup_object.name):
                machines.setdefault(host, []).append(backup_object)

        piggyback: dict[str, str] = {}
        for host, machine_objects in machines.items():
            machine_points = [point for obj in machine_objects for point in points.get(obj.id, [])]
            newest = _newest(machine_points)
            # The object holding the newest point, so that its type matches the point
            owner = next(
                (
                    obj
                    for obj in machine_objects
                    if any(p is newest for p in points.get(obj.id, []))
                ),
                machine_objects[0],
            )
            record = {
                "platformName": owner.platform_name,
                "type": owner.type,
                "restorePointsCount": _total_count(machine_objects),
                "lastRestorePoint": (
                    None
                    if newest is None
                    else {
                        "creationTime": newest.creation_time,
                        "type": newest.type,
                        "malwareStatus": newest.malware_status,
                    }
                ),
                "malwareStatus": _malware_rollup(machine_points),
            }
            piggyback[host] = f"<<<{name}:sep(0)>>>\n{json.dumps(record)}\n"
        return Fetched(piggyback=piggyback)

    return _fetch


def _job_sessions(
    jobs: Sequence[_JobState],
    disabled_ids: Container[str],
) -> dict[str, tuple[str, str]]:
    """Builds `sessionId -> (job id, job name)` from each job's current session.

    Disabled jobs (`disabled_ids`) are excluded, like the old plug-in; a
    schedule-disabled job is still included.
    """
    return {
        job.session_id: (job.id, job.name)
        for job in jobs
        if job.id not in disabled_ids and job.session_id is not None
    }


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

    Iterates `session_to_job` (built by `_job_sessions`) rather than the
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
            objects = client.get_all(f"/api/v1/backups/{session_info.resource_id}/objects")
        except TerminateAgent as exc:
            if _is_skippable(exc):
                continue
            raise
        parsed_objects = _parse_items(_BackupObject, objects)
        if len(parsed_objects) != len(objects):
            # A partial list would attribute the skipped objects' tasks to the others.
            continue
        names = [obj.name for obj in parsed_objects if obj.name]
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


def _session_fallback_task(
    session: _SessionInfo, job_name: str, session_progress: _SessionProgress | None
) -> Mapping[str, object]:
    """Builds a taskSessions-shaped record from a job's own session, for a
    single-object job taskSessions has no task for. With a single object, the job's
    `sessionProgress` sizes are that object's; its duration and rate cover the whole
    session rather than the object's processing, so they are left out."""
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
        "progress": ({} if duration is None else {"duration": duration})
        | (
            {}
            if session_progress is None
            else session_progress.model_dump(by_alias=True, exclude_none=True)
        ),
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

    Only the tasks of each job's current session (from /api/v1/jobs/states) are
    fetched, via /api/v1/sessions/{id}/taskSessions, and only for jobs whose
    objects resolved. This costs one request per job however long ago it last ran;
    a time window over /api/v1/taskSessions would reach back to the least recently
    run job and pull everything since. A task session lookup that 404s/400s leaves
    that job without tasks (a single-object job still falls back to its session).

    /api/v1/jobs/states also lists jobs that aren't backup jobs, e.g. backup copy
    jobs, whose sessions hold tasks of their own `sessionType`. These are dropped
    client-side: `sessionTypeFilter=BackupJob` isn't used, as on VBR 13.0.3.63 it
    silently matches nothing even for matching records.
    """
    jobs = _parse_items(_JobState, client.get_all("/api/v1/jobs/states"))
    session_to_job = _job_sessions(jobs, _disabled_job_ids(client))
    progress_by_job_id = {
        job.id: job.session_progress for job in jobs if job.session_progress is not None
    }
    job_objects = _resolve_job_object_names(client, session_to_job)

    groups: dict[str, list[Mapping[str, object]]] = {}

    newest: dict[tuple[str, str], Mapping[str, object]] = {}

    for session_id, (job_id, job_name) in session_to_job.items():
        if job_id not in job_objects:
            continue
        try:
            tasks = client.get_all(
                f"/api/v1/sessions/{session_id}/taskSessions", extra_params="&typeFilter=Backup"
            )
        except TerminateAgent as exc:
            if _is_skippable(exc):
                continue
            raise

        resolved_names = job_objects[job_id].names
        for task in tasks:
            if not isinstance(task, dict) or not isinstance(task_name := task.get("name"), str):
                continue
            if task.get("sessionType") != "BackupJob":
                continue
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

    # Single-object jobs whose session has no task at all (e.g. the
    # Linux/Windows Agent Backup gap) fall back to the job's own session: with only
    # one object, the job's result already *is* that object's result.
    for job_id, job_obj in job_objects.items():
        if len(job_obj.names) != 1 or job_obj.session.state is None:
            continue
        key = (job_obj.names[0], job_id)
        if key not in newest:
            newest[key] = _session_fallback_task(
                job_obj.session, job_obj.job_name, progress_by_job_id.get(job_id)
            )

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
    """Each piggyback host is written once, with the sections of all fetches for it.

    A section the user may not read is left out and reported as a warning, the other
    sections are still written.
    """
    piggyback: dict[str, list[str]] = {}
    messages = AgentMessages()
    for name, fetch in sections:
        try:
            fetched = fetch(client, name)
        except AccessDenied as exc:
            messages.add_warning(
                f"Could not create section '{name}': denied permission to endpoint {exc.endpoint}"
            )
            continue
        sys.stdout.write(fetched.own)
        for host, text in fetched.piggyback.items():
            piggyback.setdefault(host, []).append(text)
    for host, texts in piggyback.items():
        sys.stdout.write(f"<<<<{host}>>>>\n{''.join(texts)}<<<<>>>>\n")
    sys.stdout.write(messages.render())


SECTIONS: Sequence[Section] = (
    ("veeam_server_info", fetch_object("/api/v1/serverInfo")),
    ("veeam_license", fetch_object("/api/v1/license")),
    ("veeam_backup_jobs", fetch_backup_jobs),
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
    logging.basicConfig(level=logging.WARNING)
    if args.debug:
        _LOGGER.setLevel(logging.DEBUG)

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
