# encoding: utf-8

import OpenSSL
import pytest  # type: ignore
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import omdlib.certs as certs

CA_NAME = "test-ca"


@pytest.fixture
def ca(tmp_path, monkeypatch):
    p = tmp_path / "ca"
    return certs.CertificateAuthority(p, CA_NAME)


def test_initialize(ca):
    assert not ca.is_initialized
    ca.initialize()
    assert ca.is_initialized

    cert, key = ca._get_root_certificate()

    assert cert.get_subject().CN == CA_NAME

    ctx = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    ctx.use_privatekey(key)
    ctx.use_certificate(cert)
    ctx.check_privatekey()


def test_create_site_certificate(ca):
    ca.initialize()
    site_id = "xyz"
    assert not ca.site_certificate_exists(site_id)

    ca.create_site_certificate(site_id)

    assert ca.site_certificate_exists(site_id)

    cert, key = ca.read_site_certificate(site_id)

    assert cert.get_subject().CN == site_id

    ctx = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    ctx.use_privatekey(key)
    ctx.use_certificate(cert)
    ctx.check_privatekey()


def test_write_site_certificate(ca):
    ca.initialize()
    site_id = "xyz"
    assert not ca.site_certificate_exists(site_id)

    ca.create_site_certificate(site_id)

    assert ca.site_certificate_exists(site_id)

    cert, key = ca.read_site_certificate(site_id)

    assert cert.get_subject().CN == site_id

    ctx = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    ctx.use_privatekey(key)
    ctx.use_certificate(cert)
    ctx.check_privatekey()


def test_get_not_existing_site_certificate(ca):
    with pytest.raises(IOError, match="No such file or directory"):
        ca.read_site_certificate("xyz")


def test_create_site_certificate_ca_not_initialized(ca):
    with pytest.raises(Exception, match="not initialized"):
        ca.create_site_certificate("xyz")
