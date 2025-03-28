#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for Certificate and friends"""

from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

import pytest
import time_machine
from cryptography import x509
from dateutil.relativedelta import relativedelta

from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateSigningRequest,
    CertificateWithPrivateKey,
    InvalidExpiryError,
    PersistedCertificateWithPrivateKey,
    X509Name,
)
from cmk.crypto.keys import InvalidSignatureError, PlaintextPrivateKeyPEM, PrivateKey
from cmk.crypto.password import Password
from cmk.crypto.pem import PEMDecodingError


def _rsa_private_keys_equal(key_a: PrivateKey, key_b: PrivateKey) -> bool:
    """Check if two keys are the same RSA key"""
    # Assert keys are RSA keys here just to cut corners on type checking. ed25519 keys don't have
    # private_numbers(). Also, no-one else needs __eq__ on PrivateKey at the moment.
    return key_a.get_raw_rsa_key().private_numbers() == key_b.get_raw_rsa_key().private_numbers()


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    """
    Return a self-signed RSA certificate.

    Valid from 2023-01-01 08:00:00 til 2023-01-01 10:00:00.
    """
    with time_machine.travel(datetime(2023, 1, 1, 8, 0, 0)):
        return CertificateWithPrivateKey.generate_self_signed(
            common_name="TestGenerateSelfSigned",
            organization="Checkmk Testing",
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


def test_generate_self_signed(self_signed_cert: CertificateWithPrivateKey) -> None:
    assert (
        self_signed_cert.public_key
        == self_signed_cert.certificate.public_key
        == self_signed_cert.private_key.public_key
    )

    assert self_signed_cert.certificate._is_self_signed()  # noqa: SLF001
    self_signed_cert.certificate.verify_is_signed_by(self_signed_cert.certificate)

    assert "TestGenerateSelfSigned" == self_signed_cert.certificate.common_name
    assert self_signed_cert.certificate.organization_name is not None
    assert "Checkmk Testing" in self_signed_cert.certificate.organization_name


@pytest.mark.parametrize(
    "time_offset,allowed_drift,expectation",
    [
        (
            relativedelta(hours=-5),  # It's 5 hours BEFORE cert creation.
            None,  # The default 2 hours slack is not enough.
            pytest.raises(InvalidExpiryError, match="not yet valid"),
        ),
        (relativedelta(hours=+5), None, pytest.raises(InvalidExpiryError, match="expired")),
        (
            # It's now 5 hours after cert creation, so the cert has expired 3 hours ago.
            relativedelta(hours=+5),
            relativedelta(hours=+5),  # But we allow 5 hours drift.
            does_not_raise(),
        ),
        (relativedelta(minutes=+10), None, does_not_raise()),
    ],
)
def test_verify_expiry(
    self_signed_cert: CertificateWithPrivateKey,
    time_offset: relativedelta,
    allowed_drift: relativedelta,
    expectation: AbstractContextManager[None | NoReturn],
) -> None:
    # time_offset is the time difference to (mocked) certificate creation
    # allowed_drift is the tolerance parameter of verify_expiry (defaults to 2 hours for None)
    #
    # We assume self_signed_cert is valid for 2 hours. Otherwise the test will not work.
    #
    with time_machine.travel(self_signed_cert.certificate.not_valid_before + time_offset):
        with expectation:
            self_signed_cert.certificate.verify_expiry(allowed_drift)


@pytest.mark.parametrize(
    "when,expected_days_remaining",
    [
        (relativedelta(seconds=0), 0),  # in 2 hours
        (relativedelta(days=-1), 1),  # yesterday it was valid for another day
        (relativedelta(months=-12), 365),  # 2022 was not a leap year
        (relativedelta(hours=+2), 0),  # expires right now
        (relativedelta(hours=+4), -1),  # today but rounded "down" to a day ago
    ],
)
def test_days_til_expiry(
    self_signed_cert: CertificateWithPrivateKey,
    when: relativedelta,
    expected_days_remaining: relativedelta,
) -> None:
    with time_machine.travel(self_signed_cert.certificate.not_valid_before + when):
        assert self_signed_cert.certificate.days_til_expiry() == expected_days_remaining


def test_write_and_read(tmp_path: Path, self_signed_cert: CertificateWithPrivateKey) -> None:
    cert_path = tmp_path / "cert.crt"
    key_path = tmp_path / "key.pem"
    password = Password("geheim")

    PersistedCertificateWithPrivateKey.persist(self_signed_cert, cert_path, key_path, password)

    assert key_path.read_bytes().splitlines()[0] == b"-----BEGIN ENCRYPTED PRIVATE KEY-----"
    assert cert_path.read_bytes().splitlines()[0] == b"-----BEGIN CERTIFICATE-----"

    loaded = PersistedCertificateWithPrivateKey.read_files(cert_path, key_path, password)

    assert loaded.certificate.serial_number == self_signed_cert.certificate.serial_number
    assert _rsa_private_keys_equal(loaded.private_key, self_signed_cert.private_key)


def test_loading_combined_file_content(self_signed_cert: CertificateWithPrivateKey) -> None:
    pw = Password("unittest")
    with pytest.raises(PEMDecodingError, match="Could not find certificate"):
        CertificateWithPrivateKey.load_combined_file_content("", None)

    with pytest.raises(PEMDecodingError, match="Unable to load certificate."):
        CertificateWithPrivateKey.load_combined_file_content(
            "-----BEGIN CERTIFICATE-----a-----END CERTIFICATE-----", None
        )

    file_content = self_signed_cert.certificate.dump_pem().str
    with pytest.raises(PEMDecodingError, match="Could not find private key"):
        CertificateWithPrivateKey.load_combined_file_content(file_content, None)
    with pytest.raises(PEMDecodingError, match="Could not find encrypted private key"):
        CertificateWithPrivateKey.load_combined_file_content(file_content, pw)

    assert (
        CertificateWithPrivateKey.load_combined_file_content(
            file_content + "\n" + self_signed_cert.private_key.dump_pem(None).str, None
        )
        .certificate.dump_pem()
        .str
        == self_signed_cert.certificate.dump_pem().str
    )
    assert (
        CertificateWithPrivateKey.load_combined_file_content(
            file_content + "\n" + self_signed_cert.private_key.dump_pem(pw).str, pw
        )
        .certificate.dump_pem()
        .str
        == self_signed_cert.certificate.dump_pem().str
    )


def test_verify_is_signed_by() -> None:
    # These were generated by hand.

    # Currently the certificate expiry is not checked. If this will be checked
    # one day, we should fix the time here.
    ca_pem = CertificatePEM(
        "\n".join(
            [
                "-----BEGIN CERTIFICATE-----",
                "MIICBDCCAW2gAwIBAgIUNu5U+5nbZYtaG90vJ46ozhgTp/IwDQYJKoZIhvcNAQEL",
                "BQAwLDEYMBYGA1UEAwwPU29tZSB0ZXN0aW5nIENBMRAwDgYDVQQKDAdUZXN0aW5n",
                "MB4XDTIzMDMwMzEwMTcyMFoXDTIzMDYwMTEwMTcyMFowLDEYMBYGA1UEAwwPU29t",
                "ZSB0ZXN0aW5nIENBMRAwDgYDVQQKDAdUZXN0aW5nMIGfMA0GCSqGSIb3DQEBAQUA",
                "A4GNADCBiQKBgQC7JTszgqpicT/qgnhYg10rYrGb0R/oYTjMG26RcSNw18ooSwYT",
                "1syLmV9ifXZ3GRyq08gg8SQgpUfgTwkySIvDJE5lpvk6yN3Ss3QACFKAOiaY79rj",
                "iiIBuKN+Woor4cgJG6KbK3uDMyPNezsjmZEiy5g5DdQUsAFN9CnVIWH0XQIDAQAB",
                "oyMwITAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBxjANBgkqhkiG9w0B",
                "AQsFAAOBgQChNpbrgxHFoyoSsjkcVaZHwK0nMgXzshaqeqciiDvEq3dS2+leFmcq",
                "KRB5AiLvdDQlWaJrFtdmfQs3uYRdJFmB9fIWvWdoUXRqcWphXq5+6IxWIsAF3Z6M",
                "Bbepnq9rp3OltabW0ux45qry09RFAVJA4eh+jOqKBMFNYrkVNGbgTg==",
                "-----END CERTIFICATE-----",
            ]
        )
    )
    cert_pem = CertificatePEM(
        "\n".join(
            [
                "-----BEGIN CERTIFICATE-----",
                "MIIB+DCCAWGgAwIBAgIUJfamCnTW8nHHswQf+Th1atxs5C4wDQYJKoZIhvcNAQEN",
                "BQAwLDEYMBYGA1UEAwwPU29tZSB0ZXN0aW5nIENBMRAwDgYDVQQKDAdUZXN0aW5n",
                "MB4XDTIzMDMwMzEwMTcyMFoXDTIzMDYwMTEwMTcyMFowIzEPMA0GA1UEAwwGc2ln",
                "bmVkMRAwDgYDVQQKDAdUZXN0aW5nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKB",
                "gQCxByXer6BpmXAkqdoqyGtf6fSuVFLN+k01CNRwhd8LOu4F7MVC9ZO5IxuHYfWr",
                "89TXZ2KaF+4r/Pxa89/k7pnwIwoJI16xc7cY6Lcba9/6GJngFYvD6ThNKio9GztA",
                "4vJS2OBF/tfZCwEW3s3Chfw3d5/ggRtiOR80/PiHKElxXwIDAQABoyAwHjAMBgNV",
                "HRMBAf8EAjAAMA4GA1UdDwEB/wQEAwID+DANBgkqhkiG9w0BAQ0FAAOBgQCvquV7",
                "cTkaozgnvwsgkyU8+qSeWtJ5mGJ700ASjCvBd7ZabC/efVAmeNhZDk4dHfl7mk/r",
                "vrSfdEuFFCOSo8rCNgFNBGIVvtu8ks1Viuq2zpwsE26JMT1dKA+0DdtDpOzSf7MV",
                "8k2/bFIyzFv9CEw43B6UX4QC2nNfWJIu1YkV2g==",
                "-----END CERTIFICATE-----",
            ]
        )
    )
    other_pem = CertificatePEM(
        "\n".join(
            [
                "-----BEGIN CERTIFICATE-----",
                "MIIB+DCCAWGgAwIBAgIUaFZY5XpToxJGKwy2XgkHywlqivkwDQYJKoZIhvcNAQEN",
                "BQAwLDEYMBYGA1UEAwwPU29tZSB0ZXN0aW5nIENBMRAwDgYDVQQKDAdUZXN0aW5n",
                "MB4XDTIzMDMwMzEwMjAwN1oXDTIzMDYwMTEwMjAwN1owIzEPMA0GA1UEAwwGc2ln",
                "bmVkMRAwDgYDVQQKDAdUZXN0aW5nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKB",
                "gQC8X9pCePQ2IVftGsc2KSG6o5NiM8WIubWw7BRLUOUEaqN63fmx5aRBhtbZk5ig",
                "mX8a9v6epaTdf6NRcHdOKuh1U5QSE1+XO/N8IAKjBdLFqZ0JHEmQIq6mc5zY4kIw",
                "tTBWk0Lshw09ZscH3YuE3LuUavdMSSHMkKINJFaGXlUUgQIDAQABoyAwHjAMBgNV",
                "HRMBAf8EAjAAMA4GA1UdDwEB/wQEAwID+DANBgkqhkiG9w0BAQ0FAAOBgQCNso9R",
                "ZRhI23EEaXMmpRqi46ViHgBQMsVGBWiBXk8LU44P5o/P+V4o9xlclm/Vs+JVPYxO",
                "e8fM3UdwRKFkw9Z17/oD7uIy1Kj+4wAJdm6A+iXRPIaQMooGFeg6cR4oPx9chPzM",
                "e9Q7tuF8u+dnFcJ2cHWAOnXGOZPQjT4W3EgUfw==",
                "-----END CERTIFICATE-----",
            ]
        )
    )
    Certificate.load_pem(cert_pem).verify_is_signed_by(Certificate.load_pem(ca_pem))
    with pytest.raises(InvalidSignatureError):
        Certificate.load_pem(other_pem).verify_is_signed_by(Certificate.load_pem(ca_pem))


def test_default_subject_alt_names(self_signed_cert: CertificateWithPrivateKey) -> None:
    """check that the self-signed cert does not come with SANs"""
    assert self_signed_cert.certificate.get_subject_alt_names() == []


def test_ec_cert() -> None:
    # a self signed P256 certificate to act as CA:
    #   openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 \
    #       -keyout key.pem -out cert.pem -days 365
    ca_pem = CertificatePEM(
        """
-----BEGIN CERTIFICATE-----
MIICRTCCAeugAwIBAgIUEny8ZebcY4jqZF9XHElye219vi4wCgYIKoZIzj0EAwIw
eDELMAkGA1UEBhMCREUxEDAOBgNVBAgMB0JhdmFyaWExHDAaBgNVBAoME0NoZWNr
bWsgVGVzdGluZyBJbmMxFzAVBgNVBAMMDnAyNTYtdGVzdC1jZXJ0MSAwHgYJKoZI
hvcNAQkBFhFoZWxsb0BleGFtcGxlLmNvbTAeFw0yMzExMDgxMzEwMDVaFw0yNDEx
MDcxMzEwMDVaMHgxCzAJBgNVBAYTAkRFMRAwDgYDVQQIDAdCYXZhcmlhMRwwGgYD
VQQKDBNDaGVja21rIFRlc3RpbmcgSW5jMRcwFQYDVQQDDA5wMjU2LXRlc3QtY2Vy
dDEgMB4GCSqGSIb3DQEJARYRaGVsbG9AZXhhbXBsZS5jb20wWTATBgcqhkjOPQIB
BggqhkjOPQMBBwNCAAT+ZbIByiW7aJLwBq3CfBNzcSs5+EvHnjRfZS1D3fHTty+G
xslQ9dLhjEbuJET0apWkEkBXaJB6+vHpoJpOZdRlo1MwUTAdBgNVHQ4EFgQUEKFg
CaDe8Hv5OZqdhO7ix0luLekwHwYDVR0jBBgwFoAUEKFgCaDe8Hv5OZqdhO7ix0lu
LekwDwYDVR0TAQH/BAUwAwEB/zAKBggqhkjOPQQDAgNIADBFAiAqvRhu2oJCsWos
bZf1yetY8sc2jXaDFlTTHQOp6Zx1FAIhAIjGd+50uRV66LND65uRipKkGOdNazvn
CdnYjBDhp0Ud
-----END CERTIFICATE-----"""
    )
    ca = Certificate.load_pem(ca_pem)
    assert ca._is_self_signed()  # noqa: SLF001
    ca.verify_is_signed_by(ca)

    # an ed25519 certificate issued by that CA:
    #   openssl req -newkey ed25519 -keyout ed25519-key.pem -out ed25519-csr.pem
    #   openssl x509 -req -in ed25519-csr.pem -CA cert.pem -CAkey key.pem -CAcreateserial \
    #       -out ed25519-cert.pem -days 365
    child_pem = CertificatePEM(
        """
-----BEGIN CERTIFICATE-----
MIIB0DCCAXYCFCQEVGZy+jv2HvByTHl3ENBZ7erjMAoGCCqGSM49BAMCMHgxCzAJ
BgNVBAYTAkRFMRAwDgYDVQQIDAdCYXZhcmlhMRwwGgYDVQQKDBNDaGVja21rIFRl
c3RpbmcgSW5jMRcwFQYDVQQDDA5wMjU2LXRlc3QtY2VydDEgMB4GCSqGSIb3DQEJ
ARYRaGVsbG9AZXhhbXBsZS5jb20wHhcNMjMxMTA4MTMxNzM2WhcNMjQxMTA3MTMx
NzM2WjCBizELMAkGA1UEBhMCREUxDzANBgNVBAgMBkJlcmxpbjEcMBoGA1UECgwT
Q2hlY2ttayBUZXN0aW5nIEluYzEQMA4GA1UECwwHT3V0cG9zdDEbMBkGA1UEAwwS
ZWQyNTUxOS1jaGlsZC1jZXJ0MR4wHAYJKoZIhvcNAQkBFg9ieWVAZXhhbXBsZS5j
b20wKjAFBgMrZXADIQDGG15BAIjPlmsElcmidhhthCLuAD2uJtv6r/W9FCC0GjAK
BggqhkjOPQQDAgNIADBFAiEA4QZF5KNx3hDIlThEOW+2o05/wCLOYtO8jJy4iuaK
ip0CIBdH+5jSUeJjJx5LCycuvh4TO7TG33MvgZG71DxvUY6q
-----END CERTIFICATE-----"""
    )
    child = Certificate.load_pem(child_pem)
    child.verify_is_signed_by(ca)


@pytest.mark.parametrize(
    "sans",
    (
        ([]),
        (["foo.bar", "bar.foo"]),
    ),
)
def test_subject_alt_names(self_signed_cert: CertificateWithPrivateKey, sans: list[str]) -> None:
    """test setting and retrieval of subject-alt-names (DNS)"""
    assert (
        Certificate._create(  # noqa: SLF001
            subject_public_key=self_signed_cert.private_key.public_key,
            subject_name=X509Name.create(common_name="sans_test"),
            subject_alt_dns_names=[x509.DNSName(n) for n in sans],
            expiry=relativedelta(days=1),
            start_date=datetime.now(timezone.utc),
            is_ca=False,
            issuer_signing_key=self_signed_cert.private_key,
            issuer_name=X509Name.create(common_name="sans_test"),
        ).get_subject_alt_names()
        == sans
    )


@pytest.mark.parametrize(
    "signing_cert_fixture,subject_key_fixture",
    [
        # this tries various kinds of certs/keys both as CA and as CSR subject
        ("self_signed_cert", "self_signed_ec_cert"),
        ("self_signed_ec_cert", "self_signed_ed25519_cert"),
        ("self_signed_ed25519_cert", "self_signed_cert"),
    ],
)
def test_sign_csr(
    signing_cert_fixture: str,
    subject_key_fixture: str,
    request: pytest.FixtureRequest,
) -> None:
    signing_certificate = request.getfixturevalue(signing_cert_fixture)
    # re-use the keys from our self-signed certs for convenience
    subject_key = request.getfixturevalue(subject_key_fixture).private_key

    csr = CertificateSigningRequest.create(
        subject_name=X509Name.create(common_name="csr_test", organization_name="csr_test_org"),
        subject_private_key=subject_key,
    )

    with time_machine.travel(signing_certificate.certificate.not_valid_before):
        new_cert = signing_certificate.sign_csr(csr, expiry=relativedelta(days=1))

    assert new_cert.not_valid_before == signing_certificate.certificate.not_valid_before
    assert (
        new_cert.not_valid_after
        == signing_certificate.certificate.not_valid_before + relativedelta(days=1)
    )

    new_cert.verify_is_signed_by(signing_certificate.certificate)
    assert new_cert.public_key == subject_key.public_key, (
        "The public key in the certificate matches the private key in the CSR"
    )
    assert new_cert.issuer == signing_certificate.certificate.subject, (
        "The issuer of the new certificate is the self_signed_cert"
    )


def test_csr_serialization() -> None:
    private_key = PrivateKey.generate_elliptic_curve()
    csr = CertificateSigningRequest.create(
        subject_name=X509Name.create(
            common_name="test_csr_serialization", organization_name="cmk.crypto.unittest"
        ),
        subject_private_key=private_key,
    )

    csr_pem = csr.dump_pem()
    loaded_csr = CertificateSigningRequest.load_pem(csr_pem)

    assert loaded_csr.subject == csr.subject
    assert loaded_csr.public_key == csr.public_key


def test_may_sign_certificates() -> None:
    pem = CertificatePEM(
        # openssl req -x509 -newkey rsa:1024 -sha256 -nodes -keyout key.pem -out cert.pem -days 365
        """-----BEGIN CERTIFICATE-----
MIIC3jCCAkegAwIBAgIUFfy37IHOcIANa5IVx93DEmYO0zowDQYJKoZIhvcNAQEL
BQAwgYAxCzAJBgNVBAYTAkRFMRAwDgYDVQQIDAdCYXZhcmlhMSEwHwYDVQQKDBhJ
bnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQxGDAWBgNVBAMMD2NoZWNrbWtfdGVzdF9j
YTEiMCAGCSqGSIb3DQEJARYTdGVzdGluZ0BleGFtcGxlLmNvbTAeFw0yMzExMTcx
NTIxMjhaFw0yNDExMTYxNTIxMjhaMIGAMQswCQYDVQQGEwJERTEQMA4GA1UECAwH
QmF2YXJpYTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMRgwFgYD
VQQDDA9jaGVja21rX3Rlc3RfY2ExIjAgBgkqhkiG9w0BCQEWE3Rlc3RpbmdAZXhh
bXBsZS5jb20wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBANR+1oqFEX52v9ZJ
xyEh93DnV5Zp9H3scxeFnnjpK0epFFCM/J6yiggws845+MYv7tvVM2rQHO8ud/2i
fpe5yuqcWtFfgm9UDHqsndiANyFKjkJ6PDfPLeyWmmXZuoHMPK3He/5usP6ovxYb
5OfqM2ZwleMoMSrVmjGHv5rfvYdXAgMBAAGjUzBRMB0GA1UdDgQWBBSQSbT3kTAg
QKpT/KrKFerYoxe17DAfBgNVHSMEGDAWgBSQSbT3kTAgQKpT/KrKFerYoxe17DAP
BgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4GBABmlbyhZeb7sx3BH3C0h
JPEGQcTEa+Xvh3EFz2mMldkkZP1hXqkiFMTHZGJ2Q3HXrUJ/jFUGUKRnWAmxUfu/
/pUPP2kOchlsjMPP6JCeZLsB6N/3fIRqHhamI5jr6KyBB0eJnR7QgB3sG8liPFbQ
JxDm8nhVOD3txg6wadiqhhdB
-----END CERTIFICATE-----
"""
    )
    cert = Certificate.load_pem(pem)
    with pytest.raises(x509.ExtensionNotFound):
        # The tested cert does not set the key usage extension at all,
        # this should not prevent certificate signing.
        # Only if the extension is there but the key_cert_sign bit is missing the cert should not be
        # used for signing.
        # This is a regression test.
        cert._cert.extensions.get_extension_for_class(x509.KeyUsage)  # noqa: SLF001

    assert cert.may_sign_certificates()
