#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from OpenSSL import crypto  # type: ignore[import]
from OpenSSL.crypto import X509Store, X509StoreContext  # type: ignore[import]
from OpenSSL.SSL import Context, TLSv1_METHOD  # type: ignore[import]
from pytest_mock.plugin import MockerFixture

from omdlib.certs import CertificateAuthority

from marcv.constants import CERT_NOT_AFTER, SERVER_CN  # type: ignore[import]
from marcv.create_certificate import (  # type: ignore[import]
    certificate_exists,
    create_certificate,
    get_certificate,
    main,
    make_private_key,
    read_pem,
)

CA_NAME = "test-ca"


@pytest.fixture
def ca(tmp_path: Path, monkeypatch) -> CertificateAuthority:
    p = tmp_path / "ca"
    return CertificateAuthority(p, CA_NAME)


def check_private_key(private_key: crypto.PKey, cert: crypto.X509) -> None:
    ctx = Context(TLSv1_METHOD)
    ctx.use_privatekey(private_key)
    ctx.use_certificate(cert)
    ctx.check_privatekey()


def verify_certificate(root_cert: crypto.X509, cert: crypto.X509) -> None:
    cert_store = X509Store()
    cert_store.add_cert(root_cert)
    store_ctx = X509StoreContext(cert_store, cert)
    store_ctx.verify_certificate()


def test_make_private_key() -> None:
    private_key = make_private_key()

    assert private_key.bits() == 2048
    assert private_key.type() == crypto.TYPE_RSA


def test_read_pem(ca: CertificateAuthority, tmp_path: Path) -> None:
    ca.initialize()
    root_cert, root_key = read_pem(tmp_path / "ca/ca.pem")

    check_private_key(root_key, root_cert)


def test_get_certificate(ca: CertificateAuthority, tmp_path: Path) -> None:
    ca.initialize()
    root_cert, root_key = read_pem(tmp_path / "ca/ca.pem")
    private_key = make_private_key()

    cert = get_certificate(SERVER_CN, root_cert, root_key, private_key, CERT_NOT_AFTER)

    not_before = datetime.strptime(cert.get_notBefore().decode("ascii"), "%Y%m%d%H%M%SZ")
    not_after = datetime.strptime(cert.get_notAfter().decode("ascii"), "%Y%m%d%H%M%SZ")

    assert not_after - not_before == timedelta(days=999 * 365)
    assert cert.get_version() == 2
    assert cert.get_subject().CN == "localhost"

    assert cert.get_issuer().CN == root_cert.get_subject().CN
    assert cert.get_extension_count() == 1
    assert cert.get_extension(0).get_short_name() == b"subjectAltName"

    check_private_key(private_key, cert)
    verify_certificate(root_cert, cert)


def test_create_server_certificate(ca: CertificateAuthority, tmp_path: Path) -> None:
    ca.initialize()

    root_cert = tmp_path / "ca/ca.pem"
    server_cert = tmp_path / "server_cert.pem"
    server_private_key = tmp_path / "server_key.pem"

    assert not certificate_exists(server_cert, server_private_key)
    create_certificate(SERVER_CN, root_cert, server_cert, server_private_key, CERT_NOT_AFTER)
    assert certificate_exists(server_cert, server_private_key)


def test_main_success(mocker: MockerFixture) -> None:
    create_certificate = mocker.patch("marcv.create_certificate.create_certificate")
    certificate_exists = mocker.patch(
        "marcv.create_certificate.certificate_exists", return_value=True
    )
    main()
    create_certificate.assert_not_called()
    certificate_exists.assert_called_once()


def test_main_failed(mocker: MockerFixture) -> None:
    mocker.patch("marcv.create_certificate.create_certificate")
    mocker.patch("marcv.create_certificate.certificate_exists", return_value=False)

    with pytest.raises(SystemExit):
        main()
