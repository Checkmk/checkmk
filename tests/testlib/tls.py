#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ssl
import subprocess
from pathlib import Path


class CMKTLSError(RuntimeError): ...


def tls_connect(host: str, port: int, ca_path: Path, tls_version: ssl.TLSVersion) -> None:
    """connect to a socket with a specific tls version"""
    if tls_version == ssl.TLSVersion.SSLv3:
        raise CMKTLSError("Not even openssl supports that")

    tls_flag = {
        ssl.TLSVersion.TLSv1: "-tls1",
        ssl.TLSVersion.TLSv1_1: "-tls1_1",
        ssl.TLSVersion.TLSv1_2: "-tls1_2",
        ssl.TLSVersion.TLSv1_3: "-tls1_3",
    }[tls_version]

    openssl_call = subprocess.run(
        [
            "openssl",
            "s_client",
            "-connect",
            f"{host}:{port}",
            "-CAfile",
            str(ca_path),
            tls_flag,
            "-cipher",
            "DEFAULT@SECLEVEL=0",
            "-servername",
            host,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if openssl_call.returncode == 0:
        return

    assert openssl_call.returncode == 1

    (
        _some_number,
        _error,
        _some_hex_value,
        literal_ssl_routines,
        error_0,
        error_1,
        _origin,
        _some_other_number,
        msg,
    ) = openssl_call.stderr.splitlines()[-1].split(":")
    assert literal_ssl_routines == "SSL routines"

    if error_1 in ("unexpected eof while reading", "no protocols available"):
        raise CMKTLSError(f"{error_0}:{error_1}")
    if error_1 == "sslv3 alert handshake failure" and msg == "SSL alert number 40":
        # I think this is due to a client cert required
        return
    if error_1 == "tlsv1 alert protocol version" and msg == "SSL alert number 70":
        raise CMKTLSError(msg)

    raise RuntimeError("Unknown openssl error: {openssl_call.stderr=}")
