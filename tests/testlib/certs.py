#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from cmk.utils.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.utils.crypto.keys import PlaintextPrivateKeyPEM, PrivateKey


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    """
    Return a self-signed RSA certificate.

    Valid from 2023-01-01 08:00:00 til 2023-01-01 10:00:00.
    """
    with freeze_time(datetime(2023, 1, 1, 8, 0, 0)):
        return CertificateWithPrivateKey.generate_self_signed(
            common_name="TestGenerateSelfSigned",
            expiry=relativedelta(hours=2),
            key_size=1024,
            is_ca=True,
        )


@pytest.fixture(name="self_signed_ec_cert", scope="module")
def fixture_self_signed_ec() -> CertificateWithPrivateKey:
    """
    A self-signed elliptic curve certificate with a SECP256R1 key.
    """
    # openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc \
    #   -keyout key.pem -out cert.pem -days 1
    # Validity
    #   Not Before: Dec 29 14:37:04 2023 GMT
    #   Not After : Dec 30 14:37:04 2023 GMT
    return CertificateWithPrivateKey(
        Certificate.load_pem(
            CertificatePEM(
                """
-----BEGIN CERTIFICATE-----
MIICBDCCAamgAwIBAgIURxK5VwbFkuFrj/UDhbCAgwKcpXcwCgYIKoZIzj0EAwIw
VzELMAkGA1UEBhMCREUxDzANBgNVBAgMBkJlcmxpbjEYMBYGA1UECgwPQ2hlY2tt
ayBUZXN0aW5nMR0wGwYDVQQDDBRDaGVja21rIFRlc3RpbmcgUDI1NjAeFw0yMzEy
MjkxNDM3MDRaFw0yMzEyMzAxNDM3MDRaMFcxCzAJBgNVBAYTAkRFMQ8wDQYDVQQI
DAZCZXJsaW4xGDAWBgNVBAoMD0NoZWNrbWsgVGVzdGluZzEdMBsGA1UEAwwUQ2hl
Y2ttayBUZXN0aW5nIFAyNTYwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAARmKfJs
JI4bWwcTaYiCJjbh6OnH2iYHvuhIXzJWXvYn+UTN0FxAaBtHz3/qGiuAUBpbiB1k
gh15kEEbEK/icxJYo1MwUTAdBgNVHQ4EFgQUcVAnC7TaUfOUP50Drt/P/NGiAG4w
HwYDVR0jBBgwFoAUcVAnC7TaUfOUP50Drt/P/NGiAG4wDwYDVR0TAQH/BAUwAwEB
/zAKBggqhkjOPQQDAgNJADBGAiEA/a0ZYxrkMKWE+Q83ZcKR93/QpPHgWiPfSPl9
/4H+EygCIQCSlEM+c+wKa3SpyuqVcznn5vpi74GGbu5X2HXYS1i7bw==
-----END CERTIFICATE-----
"""
            )
        ),
        PrivateKey.load_pem(
            PlaintextPrivateKeyPEM(
                """
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgP2Mw7cTLE6oqkEzS
xF+QG7OIGRA+kK39qfjF6JhsNaehRANCAARmKfJsJI4bWwcTaYiCJjbh6OnH2iYH
vuhIXzJWXvYn+UTN0FxAaBtHz3/qGiuAUBpbiB1kgh15kEEbEK/icxJY
-----END PRIVATE KEY-----
"""
            )
        ),
    )


@pytest.fixture(name="self_signed_ed25519_cert", scope="module")
def fixture_self_signed_ed25519() -> CertificateWithPrivateKey:
    """
    A self-signed certificate with an ed25519 key.
    """
    # openssl req -x509 -newkey ed25519 -noenc -keyout key.pem -out cert.pem -days 1
    # Validity
    #   Not Before: Dec 29 14:38:10 2023 GMT
    #   Not After : Dec 30 14:38:10 2023 GMT
    return CertificateWithPrivateKey(
        Certificate.load_pem(
            CertificatePEM(
                """
-----BEGIN CERTIFICATE-----
MIIByTCCAXugAwIBAgIURBMWkxqtxKEpcvU94jJdJD6h+f4wBQYDK2VwMFoxCzAJ
BgNVBAYTAkRFMQ8wDQYDVQQIDAZCZXJsaW4xGDAWBgNVBAoMD0NoZWNrbWsgVGVz
dGluZzEgMB4GA1UEAwwXQ2hlY2ttayBUZXN0aW5nIEVkMjU1MTkwHhcNMjMxMjI5
MTQzODEwWhcNMjMxMjMwMTQzODEwWjBaMQswCQYDVQQGEwJERTEPMA0GA1UECAwG
QmVybGluMRgwFgYDVQQKDA9DaGVja21rIFRlc3RpbmcxIDAeBgNVBAMMF0NoZWNr
bWsgVGVzdGluZyBFZDI1NTE5MCowBQYDK2VwAyEAUvGarFROR22pSkiUpHbTpB+U
c82/7oKaie0Bi1hwR9GjUzBRMB0GA1UdDgQWBBRg5aUS15cGmbA9sUxlbVt2KoLn
JDAfBgNVHSMEGDAWgBRg5aUS15cGmbA9sUxlbVt2KoLnJDAPBgNVHRMBAf8EBTAD
AQH/MAUGAytlcANBAKVaIR2wiFbRNLwyHA7zFh/djdZxwvVP4BapFkh52g/CoAI6
r56dAy6S+mMKMmlpNsRZmzSCWsaW2rQPyFCONgM=
-----END CERTIFICATE-----
"""
            )
        ),
        PrivateKey.load_pem(
            PlaintextPrivateKeyPEM(
                """
-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIHKtxPcnklaXrUHmzVlJ2QRBEDG8C47QPZjlY8ApQnxg
-----END PRIVATE KEY-----
"""
            )
        ),
    )


@pytest.fixture(name="rsa_key", scope="module")
def fixture_rsa_key() -> PrivateKey:
    return PrivateKey.generate_rsa(1024)


def rsa_private_keys_equal(key_a: PrivateKey, key_b: PrivateKey) -> bool:
    """Check if two keys are the same RSA key"""
    # Assert keys are RSA keys here just to cut corners on type checking. ed25519 keys don't have
    # private_numbers(). Also, no-one else needs __eq__ on PrivateKey at the moment.
    return key_a.get_raw_rsa_key().private_numbers() == key_b.get_raw_rsa_key().private_numbers()
