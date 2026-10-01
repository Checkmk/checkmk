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
from http import HTTPStatus
from typing import override

import requests
import requests.auth
import urllib3
from pydantic import BaseModel, ValidationError

from cmk.password_store.v1 import parser_add_secret_option, resolve_secret_option, Secret
from cmk.plugins.veeam.lib import parse_iso8601_epoch
from cmk.server_side_programs.v1 import HostnameValidationAdapter, report_agent_crashes, Storage

AGENT = "veeam"

__version__ = "3.0.0b1"

PASSWORD_OPTION = "password"

API_VERSION = "1.3-rev0"
TOKEN_PATH = "/api/oauth2/token"

TOKEN_STORAGE_KEY = "token"
MIN_TOKEN_VALIDITY = 60
"""Seconds a stored access token must still be valid to be reused at agent start."""


type FetchStrategy = Callable[["VeeamClient", str], str]
"""Fetches a section's data and renders it, including its `<<<name:sep(0)>>>`
header(s), into the exact text to write to stdout for it. Takes the client and
the section name; which API path(s) to call is baked into the strategy itself."""

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
        self._session.headers["x-api-version"] = API_VERSION
        self.url = url
        self._cert_server_name = cert_server_name
        self._timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        data: Mapping[str, str] | None = None,
        auth: requests.auth.AuthBase | None = None,
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
        response = self._api.request("POST", TOKEN_PATH, data=data)
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

    def _refresh(self, refresh_token: str) -> _StoredToken | None:
        try:
            return self._request_token(
                {"grant_type": "refresh_token", "refresh_token": refresh_token}
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
            if exc.status == HTTPStatus.UNAUTHORIZED:
                raise TerminateAgent(
                    f"Authentication at the Veeam REST API failed for user '{self._user}': "
                    f"{exc.message}. Check the user name and password"
                ) from exc
            if exc.status == HTTPStatus.BAD_REQUEST and exc.code == "NotImplemented":
                raise TerminateAgent(
                    f"The Veeam backup server does not support the REST API version "
                    f"{API_VERSION}: {exc.message}"
                ) from exc
            raise TerminateAgent(
                f"Login at the Veeam REST API failed with HTTP {exc.status}: {exc.message}"
            ) from exc

    def renew(self) -> None:
        """Replace the current token: spend its refresh token, fall back to the password."""
        refreshed = self._refresh(self._token.refresh_token) if self._token is not None else None
        self._token = refreshed if refreshed is not None else self._login()

    def authenticate(self) -> None:
        """Reuse the stored access token if it is still valid long enough, renew it otherwise."""
        self._token = self._load_token()
        if self._token is None or self._token.expires_at - time.time() < MIN_TOKEN_VALIDITY:
            self.renew()


class VeeamClient:
    def __init__(self, api: VeeamApi, auth: VeeamAuth) -> None:
        self._api = api
        self._auth = auth

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


def _get_all(client: VeeamClient, path: str, limit: int | None = None) -> list[object]:
    """Fetch every page of a `data`/`pagination` endpoint and merge them."""
    items: list[object] = []
    skip = 0
    page_size = "" if limit is None else f"&limit={limit}"
    while True:
        page = client.get(f"{path}?skip={skip}{page_size}")
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

    def _fetch(client: VeeamClient, name: str) -> str:
        return f"<<<{name}:sep(0)>>>\n{json.dumps(client.get(path))}\n"

    return _fetch


def fetch_list(path: str) -> FetchStrategy:
    """A `data`/`pagination` endpoint, fetched to completion, one item per line."""

    def _fetch(client: VeeamClient, name: str) -> str:
        items = _get_all(client, path)
        return f"<<<{name}:sep(0)>>>\n" + "".join(f"{json.dumps(item)}\n" for item in items)

    return _fetch


def fetch_list_piggyback(path: str) -> FetchStrategy:
    """A `data`/`pagination` endpoint whose items each belong to a different host.

    Each item's `name` field names the object it is about (e.g. the protected
    machine); items are grouped by it and wrapped in a piggyback envelope. An
    item with no name cannot be attributed to a host and is dropped.
    """

    def _fetch(client: VeeamClient, name: str) -> str:
        groups: dict[str, list[object]] = {}
        for item in _get_all(client, path):
            if not isinstance(item, dict) or not (host := item.get("name")):
                continue
            groups.setdefault(host, []).append(item)

        output = ""
        for host, host_items in groups.items():
            output += f"<<<<{host}>>>>\n<<<{name}:sep(0)>>>\n"
            output += "".join(f"{json.dumps(item)}\n" for item in host_items)
            output += "<<<<>>>>\n"
        return output

    return _fetch


_MALWARE_SEVERITY = {"Clean": 0, "Informative": 1, "Suspicious": 2, "Infected": 3}
_UNKNOWN_MALWARE_SEVERITY = len(_MALWARE_SEVERITY)


def _malware_severity(status: object) -> int:
    if not isinstance(status, str):
        return _UNKNOWN_MALWARE_SEVERITY
    return _MALWARE_SEVERITY.get(status, _UNKNOWN_MALWARE_SEVERITY)


def _malware_rollup(points: Sequence[Mapping[str, object]]) -> object:
    """The worst malware status of all restore points. A missing or unknown status
    counts as worst, so that it surfaces in the check."""
    return max(
        (point.get("malwareStatus") for point in points), key=_malware_severity, default=None
    )


def _newest(points: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    dated = [
        (epoch, point)
        for point in points
        if isinstance(created := point.get("creationTime"), str)
        and (epoch := parse_iso8601_epoch(created)) is not None
    ]
    return max(dated, key=lambda item: item[0])[1] if dated else None


def fetch_restore_points(limit: int = 500) -> FetchStrategy:
    """One record per backup object, with its restore points reduced to the newest one
    and a malware status rollup.

    Forwarding every restore point would be far too much output on a mid-sized estate.
    The restore points carry no field referencing their backup object, so they are
    matched on name and platform. Fetching them per object
    (/api/v1/backupObjects/{id}/restorePoints) would be exact, but costs one request
    per backup object on every run.
    """

    def _fetch(client: VeeamClient, name: str) -> str:
        backup_objects = _get_all(client, "/api/v1/backupObjects", limit)
        points: dict[tuple[object, object], list[Mapping[str, object]]] = {}
        for point in _get_all(client, "/api/v1/restorePoints", limit):
            if isinstance(point, dict):
                points.setdefault((point.get("name"), point.get("platformId")), []).append(point)

        output = f"<<<{name}:sep(0)>>>\n"
        for backup_object in backup_objects:
            if not isinstance(backup_object, dict):
                continue
            object_points = points.get(
                (backup_object.get("name"), backup_object.get("platformId")), []
            )
            newest = _newest(object_points)
            record = {
                "name": backup_object.get("name"),
                "platformName": backup_object.get("platformName"),
                "type": backup_object.get("type"),
                "restorePointsCount": backup_object.get("restorePointsCount"),
                "lastRestorePoint": (
                    None
                    if newest is None
                    else {
                        "creationTime": newest.get("creationTime"),
                        "type": newest.get("type"),
                        "malwareStatus": newest.get("malwareStatus"),
                    }
                ),
                "malwareStatus": _malware_rollup(object_points),
            }
            output += f"{json.dumps(record)}\n"
        return output

    return _fetch


def write_sections(client: VeeamClient, sections: Sequence[Section]) -> None:
    for name, fetch in sections:
        sys.stdout.write(fetch(client, name))


SECTIONS: Sequence[Section] = (
    ("veeam_server_info", fetch_object("/api/v1/serverInfo")),
    ("veeam_license", fetch_object("/api/v1/license")),
    ("veeam_backup_jobs", fetch_list("/api/v1/jobs/states")),
    ("veeam_backups", fetch_list_piggyback("/api/v1/taskSessions")),
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
            auth = VeeamAuth(
                api,
                storage=Storage(AGENT, host=args.address),
                user=args.user,
                password=resolve_secret_option(args, PASSWORD_OPTION),
            )
            auth.authenticate()
            wanted = set(args.sections)
            selected = [section for section in SECTIONS if section[0] in wanted]
            write_sections(VeeamClient(api, auth), selected)
    except TerminateAgent as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
