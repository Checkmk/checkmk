#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.testlib.site import Site
from tests.testlib.tls import tls_listening_socket, tls_connect

TLS_VERSIONS = (
    ssl.TLSVersion.TLSv1,
    ssl.TLSVersion.TLSv1_1,
    ssl.TLSVersion.TLSv1_2,
    ssl.TLSVersion.TLSv1_3,
)


@contextmanager
def site_tmp(site: Site) -> Iterator[str]:
    yield from site.system_temp_dir()


@pytest.mark.parametrize("tls_version", TLS_VERSIONS, ids=lambda v: v.name)
def test_openssl_overwrite_ssl(site: Site, tmp_path: Path, tls_version: ssl.TLSVersion) -> None:
    """Check that we can connect with an old TLS version if we want to. Requests does not yet
    work"""

    with site_tmp(site) as site_temp_str:
        site_ca_path = Path(site_temp_str) / "test_ca.pem"

        # Our default openssl.cnf is tighter, so we need to relax it here
        # See https://checkmk.com/blog/how-monitor-servers-broken-tls-checkmk
        site_openssl_cnf_path = Path(site_temp_str) / "openssl.cnf"
        site.write_file(
            site_openssl_cnf_path,
            "\n".join(
                (
                    "openssl_conf = openssl_init",
                    "[openssl_init]",
                    "ssl_conf = ssl_configuration",
                    "[ssl_configuration]",
                    "system_default = policy",
                    "[policy]",
                    "MinProtocol = TLSv1",
                    "CipherString = DEFAULT:@SECLEVEL=0",
                )
            ),
        )
        with tls_listening_socket(tmp_path, tls_version) as (port, ca_path):
            site.write_file(site_ca_path, ca_path.read_text())
            site.check_output(  # this would raise if there was an ssl error
                [
                    "python",
                    "-c",
                    (
                        "import socket;"
                        "import ssl;"
                        "context = ssl.create_default_context();"
                        f'context.load_verify_locations(cafile="{site_ca_path}");'
                        f'sock = socket.create_connection(("localhost", {port}));'
                        'context.wrap_socket(sock, server_hostname="localhost")'
                    ),
                ],
                preserve_env=["OPENSSL_CONF"],
                env={"OPENSSL_CONF": str(site_openssl_cnf_path)},
            )


@pytest.mark.parametrize("tls_version", TLS_VERSIONS, ids=lambda v: v.name)
def test_test_utils(site: Site, tmp_path: Path, tls_version: ssl.TLSVersion) -> None:
    """make sure that our tls_connect indeed could connect to an old TLS version"""
    with tls_listening_socket(tmp_path, tls_version) as (port, ca_path):
        tls_connect("localhost", port, ca_path, tls_version)
