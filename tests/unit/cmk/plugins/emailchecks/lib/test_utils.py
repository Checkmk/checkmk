#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Sequence

import pytest

from cmk.plugins.emailchecks.lib.utils import parse_arguments

Args = argparse.Namespace


@pytest.mark.parametrize(
    "argv,expected_result",
    [
        pytest.param(
            [
                "--fetch-server",
                "my_server",
                "--fetch-username",
                "foo",
                "--fetch-password",
                "bar",
                "--fetch-protocol",
                "POP3",
            ],
            Args(
                debug=False,
                connect_timeout=10,
                fetch_server="my_server",
                fetch_username="foo",
                fetch_email_address=None,
                fetch_password="bar",
                fetch_password_reference=None,
                fetch_client_id=None,
                fetch_client_secret=None,
                fetch_client_secret_reference=None,
                fetch_tenant_id=None,
                fetch_protocol="POP3",
                fetch_port=None,
                fetch_tls=False,
                fetch_disable_cert_validation=False,
                verbose=0,
            ),
            id="POP3 protocol",
        ),
        pytest.param(
            [
                "--fetch-server",
                "my_server",
                "--fetch-username",
                "foo",
                "--fetch-password",
                "bar",
                "--fetch-protocol",
                "IMAP",
            ],
            Args(
                debug=False,
                connect_timeout=10,
                fetch_server="my_server",
                fetch_username="foo",
                fetch_email_address=None,
                fetch_password="bar",
                fetch_password_reference=None,
                fetch_client_id=None,
                fetch_client_secret=None,
                fetch_client_secret_reference=None,
                fetch_tenant_id=None,
                fetch_protocol="IMAP",
                fetch_port=None,
                fetch_tls=False,
                fetch_disable_cert_validation=False,
                verbose=0,
            ),
            id="IMAP protocol",
        ),
        pytest.param(
            [
                "--fetch-server",
                "my_server",
                "--fetch-username",
                "foo",
                "--fetch-password",
                "bar",
                "--fetch-protocol",
                "EWS",
            ],
            Args(
                debug=False,
                connect_timeout=10,
                fetch_server="my_server",
                fetch_username="foo",
                fetch_email_address=None,
                fetch_password="bar",
                fetch_password_reference=None,
                fetch_client_id=None,
                fetch_client_secret=None,
                fetch_client_secret_reference=None,
                fetch_tenant_id=None,
                fetch_protocol="EWS",
                fetch_port=None,
                fetch_tls=False,
                fetch_disable_cert_validation=False,
                verbose=0,
            ),
            id="EWS protocol",
        ),
    ],
)
def test_parse_arguments(argv: Sequence[str], expected_result: Args) -> None:
    parser = argparse.ArgumentParser(description="parser")
    result = parse_arguments(parser, argv)
    assert result == expected_result


def test_parse_arguments_error(capsys: pytest.CaptureFixture[str]) -> None:
    parser = argparse.ArgumentParser(description="parser")
    argv = [
        "--fetch-server",
        "my_server",
        "--fetch-username",
        "foo",
        "--fetch-password",
        "bar",
        "--fetch-protocol",
        "POP",
    ]

    with pytest.raises(SystemExit) as err:
        parse_arguments(parser, argv)

    assert err.value.code == 3

    captured = capsys.readouterr()
    assert "error: argument --fetch-protocol: invalid choice: 'POP'" in captured.err
