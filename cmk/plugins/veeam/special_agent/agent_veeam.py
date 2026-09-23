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
from collections.abc import Callable, Mapping, Sequence

import requests
from pydantic import BaseModel, ValidationError

from cmk.password_store.v1 import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1 import HostnameValidationAdapter

PASSWORD_OPTION = "password"

API_VERSION = "1.3-rev0"
TOKEN_PATH = "/api/oauth2/token"


type FetchStrategy = Callable[["VeeamClient", str], str]
"""Fetches a section's data and renders it, including its `<<<name:sep(0)>>>`
header(s), into the exact text to write to stdout for it. Takes the client and
the section name; which API path(s) to call is baked into the strategy itself."""

type Section = tuple[str, FetchStrategy]
"""The agent section name and how to fetch it."""


class FatalError(Exception):
    """An error that makes the whole run pointless."""


class AuthenticationFailed(FatalError):
    pass


class ServerUnreachable(FatalError):
    pass


class CertificateRejected(FatalError):
    pass


class UnsupportedApiVersion(FatalError):
    pass


class EndpointError(Exception):
    """A single data request failed; the other sections are still worth writing."""


class _Token(BaseModel):
    access_token: str


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
    else:
        session.mount(url, HostnameValidationAdapter(cert_server_name))
    return session


def _veeam_error(response: requests.Response) -> tuple[str, str]:
    try:
        body = response.json()
    except json.JSONDecodeError:
        return "", response.text.strip() or (response.reason or "")
    if not isinstance(body, dict):
        return "", str(body)
    return str(body.get("errorCode") or ""), str(body.get("message") or "")


class VeeamClient:
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
        self._url = url
        self._cert_server_name = cert_server_name
        self._timeout = timeout

    def _request(
        self, method: str, path: str, data: Mapping[str, str] | None = None
    ) -> requests.Response:
        try:
            # Pass `verify` explicitly, otherwise REQUESTS_CA_BUNDLE would override it.
            return self._session.request(
                method,
                f"{self._url}{path}",
                timeout=self._timeout,
                verify=self._session.verify,
                data=data,
            )
        except requests.exceptions.SSLError as exc:
            if self._cert_server_name is None:
                raise CertificateRejected(
                    f"The TLS handshake with the Veeam backup server at {self._url} failed ({exc})"
                ) from exc
            raise CertificateRejected(
                f"The certificate of the Veeam backup server was rejected: it could not be "
                f"validated against the host name '{self._cert_server_name}'. Configure the "
                f"correct certificate server name or disable certificate verification in the "
                f"rule ({exc})"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ServerUnreachable(
                f"The Veeam backup server at {self._url} did not answer within "
                f"{self._timeout} seconds"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ServerUnreachable(
                f"The Veeam backup server at {self._url} is unreachable ({exc})"
            ) from exc
        except requests.RequestException as exc:
            raise EndpointError(f"Request to {path} failed ({exc})") from exc

    def login(self, user: str, password: str) -> None:
        try:
            response = self._request(
                "POST",
                TOKEN_PATH,
                data={"grant_type": "password", "username": user, "password": password},
            )
        except EndpointError as exc:
            raise FatalError(f"Login at the Veeam REST API failed: {exc}") from exc
        if response.ok:
            try:
                token = _Token.model_validate_json(response.content)
            except ValidationError as exc:
                raise FatalError(
                    "The Veeam REST API returned an invalid access token response"
                ) from exc
            self._session.headers["Authorization"] = f"Bearer {token.access_token}"
            return

        error_code, message = _veeam_error(response)
        if response.status_code == 401:
            raise AuthenticationFailed(
                f"Authentication at the Veeam REST API failed for user '{user}': {message}. "
                f"Check the user name and password"
            )
        if response.status_code == 400 and error_code == "NotImplemented":
            raise UnsupportedApiVersion(
                f"The Veeam backup server does not support the REST API version "
                f"{API_VERSION}: {message}"
            )
        raise FatalError(
            f"Login at the Veeam REST API failed with HTTP {response.status_code}: {message}"
        )

    def get(self, path: str) -> object:
        response = self._request("GET", path)
        if response.status_code == 401:
            raise AuthenticationFailed(
                f"The Veeam REST API rejected the session on {path}: {_veeam_error(response)[1]}"
            )
        if not response.ok:
            raise EndpointError(
                f"Request to {path} failed with HTTP {response.status_code}: "
                f"{_veeam_error(response)[1]}"
            )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise EndpointError(f"Request to {path} returned invalid JSON") from exc


def _get_all(client: VeeamClient, path: str) -> list[object]:
    """Fetch every page of a `data`/`pagination` endpoint and merge them."""
    items: list[object] = []
    skip = 0
    while True:
        page = client.get(f"{path}?skip={skip}")
        if not isinstance(page, dict) or "data" not in page or "pagination" not in page:
            raise EndpointError(f"Request to {path} did not return a paginated data list")
        batch = page["data"]
        total = page["pagination"]["total"]
        if not batch and len(items) < total:
            raise EndpointError(
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


def write_sections(client: VeeamClient, sections: Sequence[Section]) -> None:
    for name, fetch in sections:
        try:
            output = fetch(client, name)
        except EndpointError as exc:
            sys.stderr.write(f"Section {name}: {exc}\n")
            continue
        sys.stdout.write(output)


SECTIONS: Sequence[Section] = (
    ("veeam_backup_jobs", fetch_list("/api/v1/jobs/states")),
    ("veeam_backups", fetch_list_piggyback("/api/v1/taskSessions")),
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(sys.argv[1:] if argv is None else argv)
    url = base_url(args.address, args.port)
    cert_server_name = None if args.disable_cert_verification else args.cert_server_name

    try:
        with create_session(url, cert_server_name) as session:
            client = VeeamClient(
                session,
                url,
                cert_server_name=cert_server_name,
                timeout=args.timeout,
            )
            client.login(args.user, resolve_secret_option(args, PASSWORD_OPTION).reveal())
            # A failing data endpoint must not exit non-zero: that discards all sections.
            write_sections(client, SECTIONS)
    except FatalError as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
