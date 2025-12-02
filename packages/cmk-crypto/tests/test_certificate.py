#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for Certificate and friends"""

from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from datetime import datetime, UTC
from ipaddress import ip_network
from pathlib import Path
from typing import NoReturn
from uuid import UUID

import pytest
import time_machine
from cryptography import x509 as pyca_x509
from dateutil.relativedelta import relativedelta

from cmk.ccc.site import SiteId
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateWithPrivateKey,
    InvalidExpiryError,
    NegativeSerialException,
    PersistedCertificateWithPrivateKey,
)
from cmk.crypto.keys import InvalidSignatureError, PlaintextPrivateKeyPEM, PrivateKey
from cmk.crypto.password import Password
from cmk.crypto.pem import PEMDecodingError
from cmk.crypto.x509 import (
    SAN,
    SubjectAlternativeNames,
    X509Name,
)


def _rsa_private_keys_equal(key_a: PrivateKey, key_b: PrivateKey) -> bool:
    """Check if two keys are the same RSA key"""
    # Assert keys are RSA keys here just to cut corners on type checking. ed25519 keys don't have
    # private_numbers(). Also, no-one else needs __eq__ on PrivateKey at the moment.
    return key_a.get_raw_rsa_key().private_numbers() == key_b.get_raw_rsa_key().private_numbers()


def test_generate_self_signed(self_signed_cert: CertificateWithPrivateKey) -> None:
    assert (
        self_signed_cert.public_key
        == self_signed_cert.certificate.public_key
        == self_signed_cert.private_key.public_key
    )

    assert self_signed_cert.certificate.is_self_signed()
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


def test_loading_parts_from_combined_file_content(
    self_signed_cert: CertificateWithPrivateKey,
) -> None:
    """Check that Certificate.load_pem and PrivateKey.load_pem work on combined files"""
    key_pem = self_signed_cert.private_key.dump_pem(None).str
    cert_pem = self_signed_cert.certificate.dump_pem().str
    combined = key_pem + "\n" + cert_pem

    assert Certificate.load_pem(CertificatePEM(combined)).dump_pem().str == cert_pem
    assert PrivateKey.load_pem(PlaintextPrivateKeyPEM(combined)).dump_pem(None).str == key_pem


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
    assert self_signed_cert.certificate.subject_alternative_names is None


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
    assert ca.is_self_signed()
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
        (SubjectAlternativeNames([])),
        (SubjectAlternativeNames([SAN.dns_name(n) for n in ["foo.bar", "bar.foo"]])),
        (
            SubjectAlternativeNames(
                [
                    SAN.uuid(UUID("12345678-1234-5678-1234-567812345678")),
                    SAN.checkmk_site(SiteId("testsite")),
                    SAN.ip_address(ip_network("127.0.0.1/24", strict=False)),
                ]
            )
        ),
    ),
)
def test_subject_alt_names(
    self_signed_cert: CertificateWithPrivateKey, sans: SubjectAlternativeNames
) -> None:
    """
    Test setting and retrieval of subject-alt-names (DNS)

    This is relevant because they get written into the x509 structure and need to be
    read back correctly. See SubjectAlternativeNames.from_extension().
    """
    assert (
        Certificate.create(
            subject_public_key=self_signed_cert.private_key.public_key,
            subject_name=X509Name.create(common_name="sans_test"),
            subject_alternative_names=sans,
            expiry=relativedelta(days=1),
            start_date=datetime.now(UTC),
            is_ca=False,
            issuer_signing_key=self_signed_cert.private_key,
            issuer_name=X509Name.create(common_name="sans_test"),
        ).subject_alternative_names
        == sans
    )


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
    with pytest.raises(pyca_x509.ExtensionNotFound):
        # The tested cert does not set the key usage extension at all,
        # this should not prevent certificate signing.
        # Only if the extension is there but the key_cert_sign bit is missing the cert should not be
        # used for signing.
        # This is a regression test.
        cert.get_extension_for_class(pyca_x509.KeyUsage)

    assert cert.may_sign_certificates()


def test_negative_serial_number() -> None:
    pem = CertificatePEM(
        "-----BEGIN CERTIFICATE-----\n"
        "MIIDdjCCAl6gAwIBAgIB1jANBgkqhkiG9w0BAQsFADBUMQswCQYDVQQGEwJERTET\n"
        "MBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQ\n"
        "dHkgTHRkMQ0wCwYDVQQDDARUZXN0MB4XDTI0MDMxMjEyMjczNVoXDTI0MDQxMTEy\n"
        "MjczNVowVDELMAkGA1UEBhMCREUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNV\n"
        "BAoMGEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDENMAsGA1UEAwwEVGVzdDCCASIw\n"
        "DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALwjwGHMwjbfpYhedHiQTMv840lX\n"
        "tAAj7qMzFAcEScmSM7eA3/8lJDsECu6IJrHWr9E+xYPjYfDo0FvE7LClKjewZ/ZM\n"
        "1wNOQGZpSXRf1fuIj9j7V3D4jsf9NNhh39OkVom9kFzmgpLBvZi+vV2PWBt+MWHp\n"
        "2hE1p0FvqizECcJuPurM+1YLV19xekO2jG/pQdWapoP1+3ygXK2BFn2hfmBkuLME\n"
        "PMRtIilTfQKwLktQ4jrLo8r/3CuAvGzhn6xs0bkjlMVSq+P2ZAyBbiOA4ZgBvoS2\n"
        "XnL0b9OV5hKHcLXvV79pcSOkfTW1vn61SIs3hqsQB9qXRwTfKS1z/1Ecs7ECAwEA\n"
        "AaNTMFEwHQYDVR0OBBYEFJwCbbR6GEf0bz8c4U0LFXmBMt5xMB8GA1UdIwQYMBaA\n"
        "FJwCbbR6GEf0bz8c4U0LFXmBMt5xMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcN\n"
        "AQELBQADggEBAKMxGO4A/095brhG6zb5Ttxzmmwm6sYxbvFQ1P9XEhH9muNJRwR1\n"
        "JGlLqMFrlwprA4jJ2mKbug2dFhBC38K/Y8teZpVgfIDbmnbvWoydh7tHk7IO3XKh\n"
        "zRiKHH5hPVulLnfSjhZkb0zEL3HtzLloO3kTlq2hse8NG457B1+cp6VbVzTt28FP\n"
        "vYSuV6jo4O+RwoCWtpSHpaHj+9OqS+FgW50hZJ1Dka9Rn7ffuH8cM3BkAC9Hs7t1\n"
        "X7TQFDWfQAIVDKvgV5HUU274PnjmriGShrevm12LB+/iuetYiYBgwMU9jwh5vty0\n"
        "/VrSsAozs97u+tzvnA/C255sFL3J7hobGi8=\n"
        "-----END CERTIFICATE-----\n"
    )
    with pytest.raises(NegativeSerialException) as exc_info:
        Certificate.load_pem(pem)

    exception = exc_info.value
    assert exception.subject == "CN=Test,O=Internet Widgits Pty Ltd,ST=Some-State,C=DE"
    assert (
        exception.fingerprint
        == "DF:29:9C:05:A8:AE:26:94:92:0B:31:66:1F:DF:27:92:28:8C:81:39:88:07:3A:86:B3:30:FB:66:39:FB:6E:71"
    )
    assert "-42" in str(exception)


def test_zero_serial_number() -> None:
    """Test that a certificate with serial number zero can be loaded.

    Cryptography deprecated zero serials, truststores include such certs, so let's get notified if
    cryptography indeed removes support for them."""
    pem = CertificatePEM(
        "-----BEGIN CERTIFICATE-----\n"
        "MIIEADCCAuigAwIBAgIBADANBgkqhkiG9w0BAQUFADBjMQswCQYDVQQGEwJVUzEh\n"
        "MB8GA1UEChMYVGhlIEdvIERhZGR5IEdyb3VwLCBJbmMuMTEwLwYDVQQLEyhHbyBE\n"
        "YWRkeSBDbGFzcyAyIENlcnRpZmljYXRpb24gQXV0aG9yaXR5MB4XDTA0MDYyOTE3\n"
        "MDYyMFoXDTM0MDYyOTE3MDYyMFowYzELMAkGA1UEBhMCVVMxITAfBgNVBAoTGFRo\n"
        "ZSBHbyBEYWRkeSBHcm91cCwgSW5jLjExMC8GA1UECxMoR28gRGFkZHkgQ2xhc3Mg\n"
        "MiBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTCCASAwDQYJKoZIhvcNAQEBBQADggEN\n"
        "ADCCAQgCggEBAN6d1+pXGEmhW+vXX0iG6r7d/+TvZxz0ZWizV3GgXne77ZtJ6XCA\n"
        "PVYYYwhv2vLM0D9/AlQiVBDYsoHUwHU9S3/Hd8M+eKsaA7Ugay9qK7HFiH7Eux6w\n"
        "wdhFJ2+qN1j3hybX2C32qRe3H3I2TqYXP2WYktsqbl2i/ojgC95/5Y0V4evLOtXi\n"
        "EqITLdiOr18SPaAIBQi2XKVlOARFmR6jYGB0xUGlcmIbYsUfb18aQr4CUWWoriMY\n"
        "avx4A6lNf4DD+qta/KFApMoZFv6yyO9ecw3ud72a9nmYvLEHZ6IVDd2gWMZEewo+\n"
        "YihfukEHU1jPEX44dMX4/7VpkI+EdOqXG68CAQOjgcAwgb0wHQYDVR0OBBYEFNLE\n"
        "sNKR1EwRcbNhyz2h/t2oatTjMIGNBgNVHSMEgYUwgYKAFNLEsNKR1EwRcbNhyz2h\n"
        "/t2oatTjoWekZTBjMQswCQYDVQQGEwJVUzEhMB8GA1UEChMYVGhlIEdvIERhZGR5\n"
        "IEdyb3VwLCBJbmMuMTEwLwYDVQQLEyhHbyBEYWRkeSBDbGFzcyAyIENlcnRpZmlj\n"
        "YXRpb24gQXV0aG9yaXR5ggEAMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQAD\n"
        "ggEBADJL87LKPpH8EsahB4yOd6AzBhRckB4Y9wimPQoZ+YeAEW5p5JYXMP80kWNy\n"
        "OO7MHAGjHZQopDH2esRU1/blMVgDoszOYtuURXO1v0XJJLXVggKtI3lpjbi2Tc7P\n"
        "TMozI+gciKqdi0FuFskg5YmezTvacPd+mSYgFFQlq25zheabIZ0KbIIOqPjCDPoQ\n"
        "HmyW74cNxA9hi63ugyuV+I6ShHI56yDqg+2DzZduCLzrTia2cyvk0/ZM/iZx4mER\n"
        "dEr/VxqHD3VILs9RaRegAhJhldXRQLIQTO7ErBBDpqWeCtWVYpoNz4iCxTIM5Cuf\n"
        "ReYNnyicsbkqWletNw+vHX/bvZ8=\n"
        "-----END CERTIFICATE-----\n"
    )
    cert = Certificate.load_pem(pem)
    cert.subject.rfc4514_string() == '"C = US, O = "The Go Daddy Group, Inc.", OU = Go Daddy Class 2 Certification Authority"'
    assert cert.serial_number == 0
