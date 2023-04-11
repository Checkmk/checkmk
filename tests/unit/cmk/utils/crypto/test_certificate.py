#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from cmk.utils.crypto import HashAlgorithm
from cmk.utils.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateWithPrivateKey,
    InvalidExpiryError,
    InvalidPEMError,
    InvalidSignatureError,
    PersistedCertificateWithPrivateKey,
    RsaPrivateKey,
    Signature,
    WrongPasswordError,
)
from cmk.utils.crypto.password import Password

# this is the same as in testlib.certs
FROZEN_NOW = datetime(2023, 1, 1, 8, 0, 0)


def test_generate_self_signed(self_signed_cert: CertificateWithPrivateKey) -> None:
    assert (
        self_signed_cert.public_key
        == self_signed_cert.certificate.public_key
        == self_signed_cert.private_key.public_key
    )

    self_signed_cert.certificate.verify_is_signed_by(self_signed_cert.certificate)

    assert "TestGenerateSelfSigned" == self_signed_cert.certificate.common_name
    assert "Checkmk Site" in self_signed_cert.certificate.organization_name


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
    expectation: AbstractContextManager,
) -> None:
    # time_offset is the time difference to (mocked) certificate creation
    # allowed_drift is the tolerance parameter of verify_expiry (defaults to 2 hours for None)
    #
    # We assume the cert is valid from FROZEN_NOW til FROZEN_NOW + 2 hours.
    #
    with freeze_time(FROZEN_NOW + time_offset):
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
    with freeze_time(FROZEN_NOW + when):
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

    # mypy doesn't find most attributes of cryptography's RSAPrivateKey as it seems
    loaded_nums = loaded.private_key._key.private_numbers()  # type: ignore[attr-defined]
    orig_nums = self_signed_cert.private_key._key.private_numbers()  # type: ignore[attr-defined]
    assert loaded_nums == orig_nums


def test_serialize_rsa_key(tmp_path: Path) -> None:
    key = RsaPrivateKey.generate(512)

    pem_plain = key.dump_pem(None)
    assert pem_plain.bytes.startswith(b"-----BEGIN PRIVATE KEY-----")

    loaded_plain = RsaPrivateKey.load_pem(pem_plain)
    assert loaded_plain._key.private_numbers() == key._key.private_numbers()  # type: ignore[attr-defined]

    pem_enc = key.dump_pem(Password("verysecure"))
    assert pem_enc.bytes.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----")

    with pytest.raises(WrongPasswordError):
        # Note: we suspect this test might be flaky; as of 2023-03-21 we once saw an InvalidPEMError
        # instead of the WrongPasswordError here. It seems cryptography gets a wrong error reason
        # from openssl in backends.openssl.backend.py:_handle_key_loading_error().
        # It uses openssl ERR_get_error (see `man 3 ERR_get_error`) for this -- maybe it gets the
        # error from another test running in parallel instead? Spend more time investigating if this
        # happens more often.
        RsaPrivateKey.load_pem(pem_enc, Password("wrong"))

    loaded_enc = RsaPrivateKey.load_pem(pem_enc, Password("verysecure"))
    assert loaded_enc._key.private_numbers() == key._key.private_numbers()  # type: ignore[attr-defined]


@pytest.mark.parametrize("data", [b"", b"test", b"\0\0\0", "sign here: 📝".encode()])
def test_verify_rsa_key(data: bytes) -> None:
    private_key = RsaPrivateKey.generate(1024)
    signed = private_key.sign_data(data)

    private_key.public_key.verify(signed, data, HashAlgorithm.Sha512)

    with pytest.raises(InvalidSignatureError):
        private_key.public_key.verify(Signature(b"nope"), data, HashAlgorithm.Sha512)


def test_loading_combined_file_content(self_signed_cert: CertificateWithPrivateKey) -> None:
    pw = Password("unittest")
    with pytest.raises(InvalidPEMError, match="Could not find certificate"):
        CertificateWithPrivateKey.load_combined_file_content("", None)

    with pytest.raises(InvalidPEMError, match="Unable to load certificate."):
        CertificateWithPrivateKey.load_combined_file_content(
            "-----BEGIN CERTIFICATE-----a-----END CERTIFICATE-----", None
        )

    file_content = self_signed_cert.certificate.dump_pem().str
    with pytest.raises(InvalidPEMError, match="Could not find private key"):
        CertificateWithPrivateKey.load_combined_file_content(file_content, None)
    with pytest.raises(InvalidPEMError, match="Could not find encrypted private key"):
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


@pytest.mark.parametrize(
    "sans,expected",
    (
        ([], []),
        (["foo.bar", "bar.foo"], ["foo.bar", "bar.foo"]),
    ),
)
def test_subject_alt_names(
    self_signed_cert: CertificateWithPrivateKey, sans: list[str], expected: list[str]
) -> None:
    """test setting and retrieval of subject-alt-names (DNS)"""
    assert (
        Certificate._create(
            public_key=self_signed_cert.private_key.public_key,
            signing_key=self_signed_cert.private_key,
            common_name="unittest",
            organization="unit",
            expiry=relativedelta(days=1),
            start_date=datetime.now(),
            organizational_unit_name="unit",
            subject_alt_dns_names=sans,
        ).get_subject_alt_names()
        == expected
    )
