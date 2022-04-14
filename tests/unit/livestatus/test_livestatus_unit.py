#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import errno
import socket
import ssl
from contextlib import closing

import pytest

import livestatus

from omdlib.certs import CertificateAuthority

from cmk.utils.certs import root_cert_path, RootCA


# Override top level fixture to make livestatus connects possible here
@pytest.fixture(autouse=True)
def prevent_livestatus_connect():
    pass


@pytest.fixture
def ca(tmp_path):
    p = tmp_path / "etc" / "ssl"
    return CertificateAuthority(
        root_ca=RootCA.load_or_create(root_cert_path(p), "ca-name"), ca_path=p
    )


@pytest.fixture()
def sock_path(monkeypatch, tmp_path):
    omd_root = tmp_path
    sock_path = omd_root / "tmp" / "run" / "live"
    monkeypatch.setenv("OMD_ROOT", "%s" % omd_root)
    # Will be fixed with pylint >2.0
    sock_path.parent.mkdir(parents=True)
    return sock_path


@pytest.mark.parametrize(
    "query_part",
    [
        "xyz\nabc",
        "xyz\nabc",
        b"xyz\nabc",
    ],
)
def test_lqencode(query_part):
    result = livestatus.lqencode(query_part)
    assert result == "xyzabc"


@pytest.mark.parametrize(
    "inp,expected_result",
    [
        ("ab c", "'ab c'"),
        ("ab'c", "'ab''c'"),
        ("ä \nabc", "'ä \nabc'"),
    ],
)
def test_quote_dict(inp, expected_result):
    result = livestatus.quote_dict(inp)
    assert isinstance(result, str)
    assert result == expected_result


def test_livestatus_local_connection_omd_root_not_set(monkeypatch, tmp_path):
    monkeypatch.delenv("OMD_ROOT")
    with pytest.raises(livestatus.MKLivestatusConfigError, match="OMD_ROOT is not set"):
        livestatus.LocalConnection()


def test_livestatus_local_connection_no_socket(sock_path):
    live = livestatus.LocalConnection()
    with pytest.raises(
        livestatus.MKLivestatusSocketError, match="Cannot connect to 'unix:%s'" % sock_path
    ):
        live.connect()


def test_livestatus_local_connection_not_listening(sock_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.bind("%s" % sock_path)

    live = livestatus.LocalConnection()
    with pytest.raises(
        livestatus.MKLivestatusSocketError, match="Cannot connect to 'unix:%s'" % sock_path
    ):
        live.connect()


def test_livestatus_local_connection(sock_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.bind("%s" % sock_path)
    sock.listen(1)

    live = livestatus.LocalConnection()
    assert isinstance(live, livestatus.SingleSiteConnection)


def test_livestatus_ipv4_connection():
    with closing(socket.socket(socket.AF_INET)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Pick a random port
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

        sock.listen(1)

        live = livestatus.SingleSiteConnection("tcp:127.0.0.1:%d" % port)
        live.connect()


def test_livestatus_ipv6_connection():
    with closing(socket.socket(socket.AF_INET6)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Pick a random port
        try:
            sock.bind(("::1", 0))
        except socket.error as e:
            # Skip this test in case ::1 can not be bound to
            # (happened in docker container with IPv6 disabled)
            if e.errno == errno.EADDRNOTAVAIL:
                pytest.skip("Unable to bind to ::1 (%s)" % e)

        port = sock.getsockname()[1]

        sock.listen(1)

        live = livestatus.SingleSiteConnection("tcp6:::1:%d" % port)
        live.connect()


@pytest.mark.parametrize(
    "socket_url,result",
    [
        ("unix:/omd/sites/heute/tmp/run/live", (socket.AF_UNIX, "/omd/sites/heute/tmp/run/live")),
        ("unix:/omd/sites/heute/tmp/run/li:ve", (socket.AF_UNIX, "/omd/sites/heute/tmp/run/li:ve")),
        ("tcp:127.0.0.1:1234", (socket.AF_INET, ("127.0.0.1", 1234))),
        ("tcp:126.0.0.1:abc", None),
        ("tcp6:::1:1234", (socket.AF_INET6, ("::1", 1234))),
        ("tcp6:::1:abc", None),
        ("xyz:bla", None),
    ],
)
def test_single_site_connection_socketurl(socket_url, result, monkeypatch):
    if result is None:
        with pytest.raises(livestatus.MKLivestatusConfigError, match="Invalid livestatus"):
            livestatus._parse_socket_url(socket_url)
        return

    assert livestatus._parse_socket_url(socket_url) == result


@pytest.mark.parametrize("tls", [True, False])
@pytest.mark.parametrize("verify", [True, False])
@pytest.mark.parametrize("ca_file_path", ["ca.pem", None])
def test_create_socket(tls, verify, ca, ca_file_path, monkeypatch, tmp_path):

    ssl_dir = tmp_path / "var/ssl"
    ssl_dir.mkdir(parents=True)
    with (ssl_dir / "ca-certificates.crt").open(mode="w", encoding="utf-8") as f:
        f.write((ca._ca_path / "ca.pem").open(encoding="utf-8").read())

    monkeypatch.setenv("OMD_ROOT", str(tmp_path))

    if ca_file_path is not None:
        ca_file_path = "%s/%s" % (ca._ca_path, ca_file_path)

    live = livestatus.SingleSiteConnection(
        "unix:/tmp/xyz", tls=tls, verify=verify, ca_file_path=ca_file_path
    )

    if ca_file_path is None:
        ca_file_path = tmp_path / "var/ssl/ca-certificates.crt"

    sock = live._create_socket(socket.AF_INET)

    if not tls:
        assert isinstance(sock, socket.socket)
        assert not isinstance(sock, ssl.SSLSocket)
        return

    assert isinstance(sock, ssl.SSLSocket)
    assert sock.context.verify_mode == (ssl.CERT_REQUIRED if verify else ssl.CERT_NONE)
    assert len(sock.context.get_ca_certs()) == 1
    assert live.tls_ca_file_path == str(ca_file_path)


def test_create_socket_not_existing_ca_file():
    live = livestatus.SingleSiteConnection(
        "unix:/tmp/xyz", tls=True, verify=True, ca_file_path="/x/y/z.pem"
    )
    with pytest.raises(livestatus.MKLivestatusConfigError, match="No such file or"):
        live._create_socket(socket.AF_INET)


def test_create_socket_no_cert(tmp_path):
    open(str(tmp_path / "z.pem"), "wb")  # pylint:disable=consider-using-with
    live = livestatus.SingleSiteConnection(
        "unix:/tmp/xyz", tls=True, verify=True, ca_file_path=str(tmp_path / "z.pem")
    )
    with pytest.raises(
        livestatus.MKLivestatusConfigError, match="(unknown error|no certificate or crl found)"
    ):
        live._create_socket(socket.AF_INET)


def test_local_connection(mock_livestatus):
    live = mock_livestatus
    live.set_sites(["local"])
    live.add_table(
        "status",
        [
            {
                "program_start": 1,
            },
        ],
    )
    live.expect_query("GET status\nColumns: program_start\nColumnHeaders: off")
    with mock_livestatus(expect_status_query=False):
        livestatus.LocalConnection().query_value("GET status\nColumns: program_start")
