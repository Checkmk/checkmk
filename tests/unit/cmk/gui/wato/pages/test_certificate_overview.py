#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.gui.cert_info import cert_info_registry, CertificateInfo
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request as global_request
from cmk.gui.http import response as global_response
from cmk.gui.pages import PageContext
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.certificate_overview import (
    certificate_id,
    CertificateView,
    PageDownloadCertificate,
)


@pytest.fixture(name="cert_file")
def fixture_cert_file(tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "some_cert.pem"
    path.write_bytes(
        CertificateWithPrivateKey.generate_self_signed(
            common_name="test", organization="test", key_size=1024
        )
        .certificate.dump_pem()
        .bytes
    )
    cert_info_registry.register(CertificateInfo("test", lambda: {path: "For testing"}))
    try:
        yield path
    finally:
        cert_info_registry.unregister("test")


@pytest.fixture(name="cert_and_key_file")
def fixture_cert_and_key_file(tmp_path: Path) -> Iterator[Path]:
    # this is how the site certificate is stored: certificate and private key in one file
    path = tmp_path / "bundle.pem"
    bundle = CertificateWithPrivateKey.generate_self_signed(
        common_name="test", organization="test", key_size=1024
    )
    path.write_bytes(bundle.certificate.dump_pem().bytes + bundle.private_key.dump_pem(None).bytes)
    cert_info_registry.register(CertificateInfo("test_bundle", lambda: {path: "For testing"}))
    try:
        yield path
    finally:
        cert_info_registry.unregister("test_bundle")


@pytest.fixture(name="page_context")
def fixture_page_context(request_context: None) -> PageContext:  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    return PageContext(
        config=Config(),
        request=global_request,
        transactions=transactions,
        session=session,
    )


@pytest.mark.usefixtures("request_context")
def test_download_link_does_not_use_a_data_uri(cert_file: Path) -> None:
    # Firefox refuses to navigate the Setup iframe to a data: URI, so nothing happened
    # at all when clicking the download icon (CMK-38956).
    href = str(CertificateView.load(cert_file).get_fields()["Download"])

    assert "data:" not in href
    assert f"download_certificate.py?cert={certificate_id(cert_file)}" in href
    # The path must not leak into the URL.
    assert str(cert_file) not in href


def test_page_download_serves_the_certificate(page_context: PageContext, cert_file: Path) -> None:
    page_context.request.set_var("cert", certificate_id(cert_file))
    PageDownloadCertificate().page(page_context)

    assert global_response.headers["Content-type"].startswith("application/x-pem-file")
    assert global_response.headers["Content-Disposition"] == 'attachment; filename="some_cert.pem"'
    assert global_response.get_data() == cert_file.read_bytes()


def test_page_download_does_not_serve_the_private_key(
    page_context: PageContext, cert_and_key_file: Path
) -> None:
    # The file is not served as it is: it is parsed and only the certificate is dumped again.
    page_context.request.set_var("cert", certificate_id(cert_and_key_file))
    PageDownloadCertificate().page(page_context)

    served = global_response.get_data()
    assert b"PRIVATE KEY" not in served
    assert (
        served
        == Certificate.load_pem(CertificatePEM(cert_and_key_file.read_bytes())).dump_pem().bytes
    )


@pytest.mark.parametrize("requested", ["/etc/passwd", "unregistered.pem"])
def test_page_download_rejects_unregistered_certificates(
    page_context: PageContext, cert_file: Path, requested: str
) -> None:
    path = cert_file.parent / requested
    for cert in (str(path), certificate_id(path)):
        page_context.request.set_var("cert", cert)
        with pytest.raises(MKUserError, match="Unknown certificate"):
            PageDownloadCertificate().page(page_context)

    assert not global_response.get_data()
