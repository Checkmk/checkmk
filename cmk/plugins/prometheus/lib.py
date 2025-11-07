#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Common functions used in Prometheus related Special agents
"""

from argparse import ArgumentParser, Namespace
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urljoin

from requests import Response, Session
from requests.auth import HTTPBasicAuth

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter

PASSWORD_OPTION = "password"
TOKEN_OPTION = "token"


class ApiSession:
    """Class for issuing multiple API calls

    ApiSession behaves similar to requests.Session with the exception that a
    base URL is provided and persisted.
    All requests use the base URL and append the provided url to it.
    """

    def __init__(
        self,
        base_url: str,
        auth: HTTPBasicAuth | None = None,
        tls_cert_verification: bool | HostnameValidationAdapter = True,
        additional_headers: Mapping[str, str] | None = None,
    ):
        self._session = Session()
        self._session.auth = auth
        self._session.headers.update(additional_headers or {})
        self._base_url = base_url

        if isinstance(tls_cert_verification, HostnameValidationAdapter):
            self._session.mount(self._base_url, tls_cert_verification)
            self.verify = True
        else:
            self.verify = tls_cert_verification

    def request(
        self,
        method: str,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self._session.request(
            method,
            urljoin(self._base_url, url),
            params=params,
            verify=self.verify,
        )

    def get(
        self,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self.request(
            "get",
            url,
            params=params,
        )


def add_authentication_args(parser: ArgumentParser) -> None:
    auth_method_subparsers = parser.add_subparsers(
        dest="auth_method",
        metavar="AUTH-METHOD",
        help="API authentication method",
    )

    parser_auth_login = auth_method_subparsers.add_parser(
        "auth_login",
        help="Authentication with username and password",
    )
    parser_auth_login.add_argument(
        "--username",
        required=True,
        metavar="USERNAME",
    )
    parser_add_secret_option(
        parser_auth_login,
        long=f"--{PASSWORD_OPTION}",
        required=True,
        help="Password for API authentication.",
    )

    parser_auth_token = auth_method_subparsers.add_parser(
        "auth_token",
        help="Authentication with token",
    )
    parser_add_secret_option(
        parser_auth_token,
        long=f"--{TOKEN_OPTION}",
        required=True,
        help="Token for API authentication.",
    )


@dataclass(frozen=True, kw_only=True)
class LoginAuth:
    username: str
    password: str


@dataclass(frozen=True)
class TokenAuth:
    token: str


def authentication_from_args(args: Namespace) -> LoginAuth | TokenAuth | None:
    match args.auth_method:
        case "auth_login":
            return LoginAuth(
                username=args.username,
                password=resolve_secret_option(args, PASSWORD_OPTION).reveal(),
            )
        case "auth_token":
            return TokenAuth(resolve_secret_option(args, TOKEN_OPTION).reveal())
        case _:
            return None


def get_api_url(connection: str, protocol: Literal["http", "https"]) -> str:
    return f"{protocol}://{connection}/api/v1/"


def generate_api_session(
    api_url: str,
    authentication: LoginAuth | TokenAuth | None,
    tls_cert_verification: bool | str,
) -> ApiSession:
    tls_cert_verification_: bool | HostnameValidationAdapter = (
        tls_cert_verification
        if isinstance(tls_cert_verification, bool)
        else HostnameValidationAdapter(tls_cert_verification)
    )
    match authentication:
        case LoginAuth(username=username, password=password):
            return ApiSession(
                api_url,
                auth=HTTPBasicAuth(username, password),
                tls_cert_verification=tls_cert_verification_,
            )
        case TokenAuth(token):
            return ApiSession(
                api_url,
                tls_cert_verification=tls_cert_verification_,
                additional_headers={"Authorization": "Bearer " + token},
            )
        case _:
            return ApiSession(
                api_url,
                tls_cert_verification=tls_cert_verification_,
            )
