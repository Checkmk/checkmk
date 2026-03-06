#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import ArgumentParser

import pytest

from cmk.plugins.emailchecks.lib.ac_args import (
    add_trx_arguments,
    BasicAuth,
    OAuth2,
    OAuth2WithTokens,
    parse_trx_arguments,
    Scope,
)


@pytest.fixture(scope="module")
def parser() -> ArgumentParser:
    parser = ArgumentParser()
    add_trx_arguments(parser, Scope.SEND)
    return parser


# TODO: add cases to test the logic around the password store and storage id. This will require
# mocking/patching out the password store backend.
class TestParseTrxArgumentsAuth:
    def test_parse_oauth_with_tokens(self, parser: ArgumentParser) -> None:
        argv = [
            "--send-server",
            "outlook.office.com",
            "--send-protocol",
            "GRAPHAPI",
            "--send-client-id",
            "ABC",
            "--send-client-secret",
            "password",
            "--send-tenant-id",
            "123",
            "--send-initial-access-token",
            "access-123",
            "--send-initial-refresh-token",
            "refresh-123",
            "--send-storage-id",
            "storage-123",
        ]
        args = parser.parse_args(argv)

        value = parse_trx_arguments(args, Scope.SEND).auth
        expected = OAuth2WithTokens(
            client_id="ABC",
            client_secret="password",
            tenant_id="123",
            storage_id="emailchecks-storage-123",
            initial_access_token="access-123",
            initial_refresh_token="refresh-123",
        )

        assert value == expected

    def test_parse_oauth(self, parser: ArgumentParser) -> None:
        argv = [
            "--send-server",
            "outlook.office.com",
            "--send-protocol",
            "EWS",
            "--send-client-id",
            "ABC",
            "--send-client-secret",
            "password",
            "--send-tenant-id",
            "123",
        ]
        args = parser.parse_args(argv)

        value = parse_trx_arguments(args, Scope.SEND).auth
        expected = OAuth2(client_id="ABC", client_secret="password", tenant_id="123")

        assert value == expected

    def test_parse_basic_auth(self, parser: ArgumentParser) -> None:
        argv = [
            "--send-server",
            "outlook.office.com",
            "--send-protocol",
            "EWS",
            "--send-username",
            "admin",
            "--send-password",
            "password",
        ]
        args = parser.parse_args(argv)

        value = parse_trx_arguments(args, Scope.SEND).auth
        expected = BasicAuth(username="admin", password="password")

        assert value == expected

    def test_parse_smtp_protocol_no_auth_required(self, parser: ArgumentParser) -> None:
        argv = ["--send-server", "outlook.office.com", "--send-protocol", "SMTP"]
        args = parser.parse_args(argv)
        assert parse_trx_arguments(args, Scope.SEND).auth is None

    def test_parse_auth_missing_auth_credentials(self, parser: ArgumentParser) -> None:
        argv = ["--send-server", "outlook.office.com", "--send-protocol", "EWS"]
        args = parser.parse_args(argv)
        with pytest.raises(RuntimeError, match="Incomplete auth credentials for EWS protocol."):
            parse_trx_arguments(args, Scope.SEND)

    @pytest.mark.parametrize(
        "secret",
        [
            "client-secret",
            "initial-access-token",
            "initial-refresh-token",
        ],
    )
    def test_mutually_exclusive_args_exits(self, parser: ArgumentParser, secret: str) -> None:
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    f"--send-{secret}",
                    "password",
                    f"--send-{secret}-reference",
                    "449555d1-b96b-439b-838f-d9c3bc5c950b:/path/to/password_store",
                ]
            )
