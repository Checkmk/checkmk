#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_receiver.lib.mtls_auth_validator import (
    INJECTED_ISSUER_HEADER,
    INJECTED_SERIAL_HEADER,
    INJECTED_UUID_HEADER,
)
from cmk.agent_receiver.worker import _headers_with_verified_identity

_INJECTED_UUID_KEY = INJECTED_UUID_HEADER.encode()
_INJECTED_ISSUER_KEY = INJECTED_ISSUER_HEADER.encode()
_INJECTED_SERIAL_KEY = INJECTED_SERIAL_HEADER.encode()


def test_omits_headers_when_no_client_certificate() -> None:
    result = _headers_with_verified_identity(
        [(b"host", b"localhost")], client_cn=None, issuer_cn=None, serial_number=None
    )

    assert result == [(b"host", b"localhost")]


def test_strips_client_supplied_headers_when_no_client_certificate() -> None:
    result = _headers_with_verified_identity(
        [
            (b"host", b"localhost"),
            (_INJECTED_UUID_KEY, b"spoofed-uuid"),
            (_INJECTED_ISSUER_KEY, b"spoofed-issuer"),
            (_INJECTED_SERIAL_KEY, b"spoofed-serial"),
        ],
        client_cn=None,
        issuer_cn=None,
        serial_number=None,
    )

    assert result == [(b"host", b"localhost")]


def test_injects_certificate_names_and_strips_client_supplied_copies() -> None:
    result = _headers_with_verified_identity(
        [
            (_INJECTED_UUID_KEY, b"spoofed-uuid"),
            (_INJECTED_ISSUER_KEY, b"spoofed-issuer"),
            (_INJECTED_SERIAL_KEY, b"spoofed-serial"),
            (b"host", b"localhost"),
        ],
        client_cn="real-uuid",
        issuer_cn="real-issuer",
        serial_number="real-serial",
    )

    assert result == [
        (_INJECTED_UUID_KEY, b"real-uuid"),
        (_INJECTED_ISSUER_KEY, b"real-issuer"),
        (_INJECTED_SERIAL_KEY, b"real-serial"),
        (b"host", b"localhost"),
    ]


def test_injects_certificate_names_when_no_client_supplied_copies() -> None:
    result = _headers_with_verified_identity(
        [(b"host", b"localhost")],
        client_cn="real-uuid",
        issuer_cn="real-issuer",
        serial_number="real-serial",
    )

    assert result == [
        (_INJECTED_UUID_KEY, b"real-uuid"),
        (_INJECTED_ISSUER_KEY, b"real-issuer"),
        (_INJECTED_SERIAL_KEY, b"real-serial"),
        (b"host", b"localhost"),
    ]
