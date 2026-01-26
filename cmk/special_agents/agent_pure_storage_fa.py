#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Pure Storage FlashArray via REST API 2.x with Check_MK.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import NamedTuple

import requests
import urllib3

from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter

_LOGGER = logging.getLogger("agent_pure_storage_fa")

__version__ = "2.4.0p21"

USER_AGENT = f"checkmk-special-purefa-{__version__}"


class _RestVersion(NamedTuple):
    major: int
    minor: int

    @classmethod
    def from_raw(cls, raw_version: str) -> _RestVersion:
        raw_major, raw_minor = raw_version.split(".", 1)
        return cls(int(raw_major), int(raw_minor))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


_REST_VERSION = _RestVersion(2, 0)


@dataclass(frozen=True, kw_only=True)
class _SectionSpec:
    name: str
    path: str
    min_version: _RestVersion
    params: Mapping[str, str] | None = None


_SECTIONS = [
    _SectionSpec(
        name="arrays",
        path="arrays",
        min_version=_RestVersion(2, 2),
    ),
    _SectionSpec(
        name="volumes",
        path="volumes",
        min_version=_RestVersion(2, 0),
    ),
    _SectionSpec(
        name="hardware",
        path="hardware",
        min_version=_RestVersion(2, 2),
    ),
    _SectionSpec(
        name="alerts",
        path="alerts",
        min_version=_RestVersion(2, 2),
        params={"filter": "state='open'"},
    ),
]


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="""Disables the checking of the servers ssl certificate""",
    )
    parser.add_argument(
        "--cert-server-name",
        help="""Expect this as the servers name in the ssl certificate. Overrides '--no-cert-check'.""",
    )
    parser.add_argument(
        "--api-token",
        type=str,
        required=True,
        help=(
            "Generate the API token through the Purity user interface"
            " (System > Users > Create API Token)"
            " or through the Purity command line interface"
            " (pureadmin create --api-token)"
        ),
    )
    parser.add_argument("server", type=str, help="Host name or IP address")
    return parser.parse_args(argv)


class AuthError(Exception):
    pass


class APIVersionError(Exception):
    pass


class SectionError(Exception):
    pass


class _PureStorageFlashArraySession:
    def __init__(self, server: str, cert_check: bool | str, timeout: int) -> None:
        self._session = requests.Session()
        self._base_url = f"https://{server}"

        self._verify = True
        if cert_check is False:
            # Watch out: we must provide the verify keyword to every individual request call!
            # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
            self._verify = False
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
        elif isinstance(cert_check, str):
            self._session.mount(self._base_url, HostnameValidationAdapter(cert_check))

        self._timeout = timeout
        self._x_auth_token = ""

    def post(self, path: str, headers: Mapping[str, str]) -> requests.Response:
        # Watch out: we must provide the verify keyword to every individual request call!
        # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
        return self._session.post(
            f"{self._base_url}/api/{path}",
            headers=headers,
            verify=self._verify,
            timeout=self._timeout,
        )

    def get(
        self, path: str, headers: Mapping[str, str], params: Mapping[str, str] | None = None
    ) -> requests.Response:
        # Watch out: we must provide the verify keyword to every individual request call!
        # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
        return self._session.get(
            f"{self._base_url}/api/{path}",
            headers=headers,
            params=params,
            verify=self._verify,
            timeout=self._timeout,
        )


class PureStorageFlashArray:
    def __init__(self, server: str, cert_check: bool | str, timeout: int) -> None:
        self._session = _PureStorageFlashArraySession(server, cert_check, timeout)

    def login(self, api_token: str) -> None:
        try:
            login_response = self._session.post(
                f"{_REST_VERSION}/login",
                {
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "api-token": api_token,
                },
            )
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("Login failed: %s", e)
            raise AuthError()

        if login_response.status_code != 200:
            _LOGGER.error(
                "Login failed: %s (%s)",
                login_response.reason,
                login_response.status_code,
            )
            raise AuthError()

        self._x_auth_token = login_response.headers["x-auth-token"]

    def read_latest_api_version(self) -> _RestVersion:
        try:
            api_version_response = self._session.get("api_version", {})
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("Getting API version failed: %s", e)
            raise APIVersionError()

        if api_version_response.status_code != 200:
            _LOGGER.error(
                "Getting API version failed: %s (%s)",
                api_version_response.reason,
                api_version_response.status_code,
            )
            raise APIVersionError()

        return max(
            v
            for r in api_version_response.json()["version"]
            if _REST_VERSION.major == (v := _RestVersion.from_raw(r)).major
        )

    def collect_section_data(
        self, latest_version: _RestVersion, spec: _SectionSpec
    ) -> tuple[str, Mapping]:
        try:
            section_response = self._session.get(
                f"{latest_version}/{spec.path}",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "x-auth-token": self._x_auth_token,
                },
                params=spec.params,
            )
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("Collecting '%s' failed: %s", spec.name, e)
            raise SectionError()

        if section_response.status_code != 200:
            _LOGGER.error(
                "Collecting '%s' failed: %s (%s)",
                spec.name,
                section_response.reason,
                section_response.status_code,
            )
            raise SectionError()

        return section_response.json()


def _filter_applicable_sections(
    latest_version: _RestVersion, sections: Sequence[_SectionSpec]
) -> Iterator[_SectionSpec]:
    for spec in sections:
        if spec.min_version > latest_version:
            _LOGGER.error(
                "Collecting '%s' failed: '%s' > '%s'",
                spec.name,
                spec.min_version,
                latest_version,
            )
            continue

        yield spec


def agent_pure_storage_fa(args: Args) -> int:
    pure_storage_fa = PureStorageFlashArray(
        args.server,
        args.cert_server_name or not args.no_cert_check,
        int(args.timeout),
    )

    try:
        pure_storage_fa.login(args.api_token)
    except AuthError:
        return 1

    try:
        latest_version = pure_storage_fa.read_latest_api_version()
    except APIVersionError:
        return 1

    for spec in _filter_applicable_sections(latest_version, _SECTIONS):
        try:
            data = pure_storage_fa.collect_section_data(latest_version, spec)
        except SectionError:
            if args.debug:
                return 1

        with SectionWriter(f"pure_storage_fa_{spec.name}") as writer:
            writer.append_json(data)

    return 0


def main() -> int:
    return special_agent_main(parse_arguments, agent_pure_storage_fa)
