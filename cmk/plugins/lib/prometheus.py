#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Common functions used in Prometheus related Special agents
"""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from requests.auth import HTTPBasicAuth

from cmk.utils.password_store import lookup

from cmk.special_agents.v0_unstable.request_helper import (
    ApiSession,
    HostnameValidationAdapter,
    parse_api_url,
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
    group_auth_token = parser_auth_login.add_mutually_exclusive_group(required=True)
    group_auth_token.add_argument(
        "--password",
        metavar="PASSWORD",
    )
    group_auth_token.add_argument(
        "--password-reference",
        metavar="PASSWORD-REFERENCE",
        help="Password store reference of the password for API authentication.",
    )

    parser_auth_token = auth_method_subparsers.add_parser(
        "auth_token",
        help="Authentication with otken",
    )
    group_auth_token = parser_auth_token.add_mutually_exclusive_group(required=True)
    group_auth_token.add_argument(
        "--token",
        metavar="TOKEN",
    )
    group_auth_token.add_argument(
        "--token-reference",
        metavar="TOKEN-REFERENCE",
        help="Password store reference of the token for API authentication.",
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
                password=(
                    _lookup_from_password_store(args.password_reference)
                    if args.password_reference
                    else args.password
                ),
            )
        case "auth_token":
            return TokenAuth(
                _lookup_from_password_store(args.token_reference)
                if args.token_reference
                else args.token
            )
        case _:
            return None


def _lookup_from_password_store(raw_reference: str) -> str:
    pw_id, pw_file = raw_reference.split(":", 1)
    return lookup(Path(pw_file), pw_id)


def get_api_url(connection: str, protocol: Literal["http", "https"]) -> str:
    return parse_api_url(
        server_address=connection,
        api_path="api/v1/",
        protocol=protocol,
    )


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
