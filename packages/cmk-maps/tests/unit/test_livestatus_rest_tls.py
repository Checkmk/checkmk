#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import os
import ssl
from pathlib import Path

import pytest

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.maps.backend.connections.livestatus import LivestatusConnection
from cmk.maps.backend.core.config import settings


@functools.cache
def _ca_pem(common_name: str) -> bytes:
    ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=common_name, organization="test", key_size=1024, is_ca=True
    )
    return ca.certificate.dump_pem().bytes


def _write_ca(path: Path, common_name: str) -> None:
    path.write_bytes(_ca_pem(common_name))


def _trusts(context: ssl.SSLContext | bool, common_name: str) -> bool:
    assert isinstance(context, ssl.SSLContext)
    der = ssl.PEM_cert_to_DER_cert(_ca_pem(common_name).decode())
    return der in context.get_ca_certs(binary_form=True)


@pytest.fixture(name="ca_file")
def fixture_ca_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    ca_dir = tmp_path / "var" / "ssl"
    ca_dir.mkdir(parents=True)
    return ca_dir / "ca-certificates.crt"


def test_rest_calls_skip_verification_when_it_is_off(ca_file: Path) -> None:
    _write_ca(ca_file, "site-ca")
    assert LivestatusConnection(tls_verify=False)._rest_tls is False  # noqa: SLF001


@pytest.mark.usefixtures("ca_file")
def test_rest_calls_trust_the_system_without_site_cas() -> None:
    assert LivestatusConnection()._rest_tls is True  # noqa: SLF001


def test_rest_calls_trust_the_site_cas(ca_file: Path) -> None:
    _write_ca(ca_file, "site-ca")
    assert _trusts(LivestatusConnection()._rest_tls, "site-ca")  # noqa: SLF001


def test_rest_calls_trust_site_cas_written_anew(ca_file: Path) -> None:
    connection = LivestatusConnection()
    _write_ca(ca_file, "old-ca")
    assert _trusts(connection._rest_tls, "old-ca")  # noqa: SLF001
    _write_ca(ca_file, "new-ca")
    mtime = ca_file.stat().st_mtime_ns + 1_000_000_000
    os.utime(ca_file, ns=(mtime, mtime))
    context = connection._rest_tls  # noqa: SLF001
    assert _trusts(context, "new-ca")
    assert not _trusts(context, "old-ca")
