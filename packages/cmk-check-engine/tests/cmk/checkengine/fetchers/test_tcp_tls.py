#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import socket
import ssl
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

import cmk.ccc.resulttype as result
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.agent_protocol import TCPEncryptionHandling
from cmk.checkengine.fetcher_abc import FetcherError, Mode
from cmk.checkengine.fetchers.tcp import TCPFetcher, TLSConfig
from cmk.checkengine.helper_interface import AgentRawData
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.crypto.x509 import SAN, SubjectAlternativeNames

REGISTERED_UUID = "11111111-1111-1111-1111-111111111111"
UNKNOWN_UUID = "22222222-2222-2222-2222-222222222222"
AGENT_OUTPUT = b"<<<check_mk>>>\nVersion: 2.6.0\n"


def _write_combined(path: Path, cert: CertificateWithPrivateKey) -> Path:
    path.write_text(cert.certificate.dump_pem().str + cert.private_key.dump_pem(None).str)
    return path


def _reject_unknown_connections(
    _sock: ssl.SSLObject, server_name: str | None, _ctx: ssl.SSLContext
) -> int | None:
    return None if server_name == REGISTERED_UUID else ssl.ALERT_DESCRIPTION_ACCESS_DENIED


@pytest.fixture(name="site_ca")
def _site_ca() -> CertificateWithPrivateKey:
    return CertificateWithPrivateKey.generate_self_signed(
        common_name="Site CA", organization="test", key_size=2048, is_ca=True
    )


@pytest.fixture(name="tls_config")
def _tls_config(tmp_path: Path, site_ca: CertificateWithPrivateKey) -> TLSConfig:
    ca_store = tmp_path / "ca-store.pem"
    ca_store.write_text(site_ca.certificate.dump_pem().str)
    site_crt = _write_combined(
        tmp_path / "site.pem",
        CertificateWithPrivateKey.generate_self_signed(
            common_name="site", organization="test", key_size=2048
        ),
    )
    return TLSConfig(cas_dir=tmp_path, ca_store=ca_store, site_crt=site_crt)


@pytest.fixture(name="agent_port")
def _agent_port(tmp_path: Path, site_ca: CertificateWithPrivateKey) -> Iterator[int]:
    agent_crt = _write_combined(
        tmp_path / "agent.pem",
        site_ca.issue_new_certificate(
            common_name=REGISTERED_UUID,
            organization="test",
            subject_alternative_names=SubjectAlternativeNames([SAN.dns_name(REGISTERED_UUID)]),
            key_size=2048,
            cert_log=tmp_path / "cert.log",
        ),
    )
    agent_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    agent_ctx.load_cert_chain(agent_crt)
    agent_ctx.sni_callback = _reject_unknown_connections
    listener = socket.create_server(("127.0.0.1", 0))

    def serve() -> None:
        conn, _addr = listener.accept()
        with conn, contextlib.suppress(ssl.SSLError, OSError):
            conn.sendall(b"16")
            with agent_ctx.wrap_socket(conn, server_side=True) as tls_conn:
                tls_conn.sendall(b"\x00\x00\x00" + AGENT_OUTPUT)

    agent = threading.Thread(target=serve)
    agent.start()
    yield listener.getsockname()[1]
    agent.join()
    listener.close()


def _fetcher(tmp_path: Path, port: int, uuid: str, tls_config: TLSConfig) -> TCPFetcher:
    uuid_file = tmp_path / "uuid"
    uuid_file.symlink_to(uuid)
    return TCPFetcher(
        family=socket.AF_INET,
        address=(HostAddress("127.0.0.1"), port),
        timeout=5.0,
        host_name=HostName("test-host"),
        encryption_handling=TCPEncryptionHandling.TLS_ENCRYPTED_ONLY,
        pre_shared_secret=None,
        uuid_file=uuid_file,
        tls_config=tls_config,
    )


def test_agent_not_registered_for_this_host_is_named_as_such(
    tmp_path: Path, agent_port: int, tls_config: TLSConfig
) -> None:
    with (
        _fetcher(tmp_path, agent_port, UNKNOWN_UUID, tls_config) as fetcher,
        pytest.raises(FetcherError, match="The agent at 127.0.0.1 is not registered for this host"),
    ):
        fetcher.fetch(Mode.CHECKING)


def test_agent_registered_for_this_host_delivers_its_output(
    tmp_path: Path, agent_port: int, tls_config: TLSConfig
) -> None:
    with _fetcher(tmp_path, agent_port, REGISTERED_UUID, tls_config) as fetcher:
        assert fetcher.fetch(Mode.CHECKING) == result.OK(AgentRawData(AGENT_OUTPUT))
