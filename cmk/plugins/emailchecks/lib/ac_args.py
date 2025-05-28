#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import assert_never, Literal

from cmk.utils import password_store


@dataclass
class BasicAuth:
    username: str
    password: str


@dataclass
class OAuth2:
    client_id: str
    client_secret: str
    tenant_id: str


MailboxAuth = BasicAuth | OAuth2 | None


class Scope(StrEnum):
    FETCH = "fetch"
    SEND = "send"


FETCH_PROTOCOLS = {"IMAP", "POP3", "EWS"}
SEND_PROTOCOLS = {"SMTP", "EWS"}


@dataclass(frozen=True)
class TRXConfig:
    server: str
    address: str
    auth: MailboxAuth
    protocol: Literal["IMAP", "POP3", "EWS", "SMTP"]
    port: int
    tls: bool
    disable_cert_validation: bool


def add_trx_arguments(parser: argparse.ArgumentParser, scope: Scope) -> None:
    match scope:
        case Scope.FETCH:
            protocols = FETCH_PROTOCOLS
        case Scope.SEND:
            protocols = SEND_PROTOCOLS
        case other:
            assert_never(other)

    parser.add_argument(
        f"--{scope}-server",
        required=True,
        metavar="ADDRESS",
        help=f"Host address of the {'/'.join(protocols)} server hosting your mailbox",
    )
    parser.add_argument(
        f"--{scope}-email-address",
        required=False,
        metavar="EMAIL-ADDRESS",
        help="Email address (default: same as username, only affects EWS protocol)",
    )
    parser.add_argument(
        f"--{scope}-username",
        required=False,
        metavar="USER",
        help=f"Username to use for {'/'.join(protocols)}",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{scope}-password",
        required=False,
        metavar="PASSWORD",
        help=f"Password to use for {'/'.join(protocols)}",
    )
    group.add_argument(
        f"--{scope}-password-reference",
        required=False,
        metavar="PASSWORD-ID",
        help=f"Password store reference of password to use for {'/'.join(protocols)}",
    )
    parser.add_argument(
        f"--{scope}-client-id",
        required=False,
        metavar="CLIENT_ID",
        help="OAuth2 ClientID for EWS",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{scope}-client-secret",
        required=False,
        metavar="CLIENT_SECRET",
        help="OAuth2 client secret for EWS",
    )
    group.add_argument(
        f"--{scope}-client-secret-reference",
        required=False,
        metavar="CLIENT_SECRET_ID",
        help="Password store reference for OAuth2 client secret for EWS",
    )
    parser.add_argument(
        f"--{scope}-tenant-id",
        required=False,
        metavar="TENANT_ID",
        help="OAuth2 TenantID for EWS",
    )
    parser.add_argument(
        f"--{scope}-protocol",
        type=str.upper,
        choices=protocols,
        required=True,
        help="Protocol used for mail transfer",
    )
    parser.add_argument(
        f"--{scope}-port",
        type=int,
        metavar="PORT",
        help=f"{'/'.join(protocols)} port (defaults to 110/995 (TLS) for POP3, to 143/993 (TLS) for "
        "IMAP and to 80/443 (TLS) for EWS)",
    )
    parser.add_argument(
        f"--{scope}-tls",
        action="store_true",
        help="Use TLS/SSL for fetching the mailbox (disabled by default)",
    )
    parser.add_argument(
        f"--{scope}-disable-cert-validation",
        action="store_true",
        help="Don't enforce SSL/TLS certificate validation",
    )


def _parse_auth(raw: Mapping[str, object]) -> MailboxAuth:
    match raw:
        case {
            "username": None,
            "password": None,
            "password_reference": None,
            "client_id": str(client_id),
            "client_secret": str() | None as client_secret,
            "client_secret_reference": str() | None as client_secret_refernce,
            "tenant_id": str(tenant_id),
        }:
            return OAuth2(
                client_id, _parse_secret(client_secret, client_secret_refernce), tenant_id
            )
        case {
            "username": str(username),
            "password": str() | None as password,
            "password_reference": str() | None as password_reference,
            "client_id": None,
            "client_secret": None,
            "client_secret_reference": None,
            "tenant_id": None,
        }:
            return BasicAuth(username, _parse_secret(password, password_reference))
        case {
            "username": None,
            "password": None,
            "password_reference": None,
            "protocol": "SMTP",
        }:
            return None
        case _:
            raise RuntimeError(
                "Either Username/Passwort or ClientID/ClientSecret/TenantID have to be set"
            )


def _parse_secret(secret: str | None, reference: str | None) -> str:
    if secret is not None:
        return secret
    if reference is None:
        raise ValueError("Either secret or secret reference must be set")
    secret_id, file = reference.split(":", 1)
    return password_store.lookup(Path(file), secret_id)


def _parse_port(raw: Mapping[str, object]) -> int:
    match raw:
        case {"port": int(port)}:
            return port
        case {"protocol": "POP3", "tls": True}:
            return 995
        case {"protocol": "POP3", "tls": False}:
            return 110
        case {"protocol": "IMAP", "tls": True}:
            return 993
        case {"protocol": "IMAP", "tls": False}:
            return 143
        case {"protocol": "SMTP"}:
            return 25
        case {"tls": True}:
            return 443
        case _:
            return 80


def parse_trx_arguments(args: argparse.Namespace, scope: Scope) -> TRXConfig:
    prefix = f"{scope}_"
    raw = {k.removeprefix(prefix): v for k, v in vars(args).items() if k.startswith(prefix)}
    return TRXConfig(
        server=raw["server"],
        # not sure how clever this is, what if we have neither?
        address=str(raw.get("email_address") or raw.get("username")),
        auth=_parse_auth(raw),
        protocol=raw["protocol"],
        port=_parse_port(raw),
        tls=raw["tls"],
        disable_cert_validation=raw["disable_cert_validation"],
    )
