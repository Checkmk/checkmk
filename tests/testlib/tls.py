#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import ssl
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.testlib.https import HTTPSDummy


class CMKTLSError(RuntimeError): ...


def tls_connect(host: str, port: int, ca_path: Path, tls_version: ssl.TLSVersion) -> None:
    """connect to a socket with a specific tls version"""
    if tls_version == ssl.TLSVersion.SSLv3:
        raise CMKTLSError("Not even openssl supports that")

    context = ssl.create_default_context()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="ssl.TLSVersion..* is deprecated",
            category=DeprecationWarning,
        )
        context.minimum_version = tls_version
        context.maximum_version = tls_version
    context.set_ciphers("DEFAULT@SECLEVEL=0")
    context.load_verify_locations(cafile=str(ca_path))
    context.check_hostname = False

    with socket.create_connection((host, port)) as sock:
        try:
            with context.wrap_socket(sock, server_hostname=host):
                pass
        except ssl.SSLError as e:
            if str(e).startswith(
                "[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake failure"
            ):
                # Probably a client cert is required
                return
            raise CMKTLSError(str(e)) from e


@contextmanager
def tls_listening_socket(tmp_path: Path, tls_version: ssl.TLSVersion) -> Iterator[tuple[int, Path]]:
    """Open a tls listening socket with a specific tls version"""
    server = HTTPSDummy(cert_dir=tmp_path)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="ssl.TLSVersion..* is deprecated",
            category=DeprecationWarning,
        )
        server.ssl_context.minimum_version = tls_version
        server.ssl_context.maximum_version = tls_version
    server.ssl_context.set_ciphers("DEFAULT@SECLEVEL=0")
    try:
        port = server.run()
        yield port, server.cert_file
    finally:
        server.stop()
