#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains functionality for dealing with X509 certificates.

At the moment, only certificates based on RSA keys are supported.

Moreover, certificates created using the classes below can currently only be used for signing
purposes (either signing data or other certificates). Key encipherment and encryption are not
supported.

Outline:

CertificateWithPrivateKey
    represents a bundle of a certificate and its matching private key. Use
    `CertificateWithPrivateKey.generate_self_signed(...)` to create a self-signed certificate.

PersistedCertificateWithPrivateKey
    allows persisting a CertificateWithPrivateKey's certificate and private key to two individual
    files on the hard drive.

Certificate
    contains the public key and certificate information, but no private key. Useful for validating
    certificates and signatures.

RsaPublicKey/RsaPrivateKey
    probably don't have a direct use case on their own in our code base, at the moment.

"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, NewType, overload

import cryptography.exceptions
import cryptography.hazmat.primitives.asymmetric.padding as padding
import cryptography.hazmat.primitives.asymmetric.rsa as rsa
import cryptography.x509 as x509
from cryptography.hazmat.primitives import serialization
from dateutil.relativedelta import relativedelta

from cmk.utils.crypto import HashAlgorithm
from cmk.utils.crypto.password import Password
from cmk.utils.exceptions import MKException
from cmk.utils.site import omd_site

Signature = NewType("Signature", bytes)


class _SerializedPEM:
    """A serialized anything in PEM format

    we tried NewTypes but the str or bytes encoding/decoding calls were just
    annoying. This class can be inherited by the former NewTypes"""

    def __init__(self, pem: str | bytes) -> None:
        if isinstance(pem, str):
            self._data = pem.encode()
        elif isinstance(pem, bytes):
            self._data = pem
        else:
            raise TypeError("Pem must either be bytes or str")

    @property
    def str(self) -> str:
        return self._data.decode()

    @property
    def bytes(self) -> bytes:
        return self._data


class PlaintextPrivateKeyPEM(_SerializedPEM):
    """A unencrypted private key in pem format"""


class EncryptedPrivateKeyPEM(_SerializedPEM):
    """A encrypted private key in pem format"""


class PublicKeyPEM(_SerializedPEM):
    """A public key in pem format"""


class CertificatePEM(_SerializedPEM):
    """A certificate in pem format"""


class InvalidSignatureError(MKException):
    """A signature could not be verified"""


class InvalidExpiryError(MKException):
    """The certificate is either not yet valid or not valid anymore"""


class WrongPasswordError(MKException):
    """The private key could not be decrypted, probably due to a wrong password"""


class InvalidPEMError(MKException):
    """The PEM is invalid"""


class CertificateWithPrivateKey(NamedTuple):
    """A bundle of a certificate and its matching private key"""

    certificate: Certificate
    private_key: RsaPrivateKey

    @classmethod
    def generate_self_signed(
        cls,
        common_name: str,
        organization: str | None = None,  # defaults to "Checkmk Site <SITE>"
        organizational_unit_name: str | None = None,
        expiry: relativedelta = relativedelta(years=2),
        key_size: int = 4096,
        start_date: datetime | None = None,  # defaults to now
        subject_alt_dns_names: list[str] | None = None,
        is_ca: bool = False,
    ) -> CertificateWithPrivateKey:
        """Generate an RSA private key and create a self-signed certificated for it."""

        private_key = RsaPrivateKey.generate(key_size)
        name = X509Name.create(
            common_name=common_name,
            organization_name=organization or f"Checkmk Site {omd_site()}",
            organizational_unit=organizational_unit_name,
        )
        certificate = Certificate._create(
            subject_public_key=private_key.public_key,
            subject_name=name,
            subject_alt_dns_names=subject_alt_dns_names,
            expiry=expiry,
            start_date=start_date or Certificate._naive_utcnow(),
            is_ca=is_ca,
            issuer_signing_key=private_key,
            issuer_name=name,
        )

        return CertificateWithPrivateKey(certificate, private_key)

    @property
    def public_key(self) -> RsaPublicKey:
        """
        Convenience accessor to the certificate's public key.

        This _should_ be the public key that belongs to the private key as well.
        """
        return self.certificate.public_key

    @classmethod
    def load_combined_file_content(
        cls, content: str, passphrase: Password | None
    ) -> CertificateWithPrivateKey:
        """load a keypair from the contents of a "combined" file (a file
        containing cert and private key"""
        if (
            cert_match := re.search(
                r"-----BEGIN CERTIFICATE-----[\s\w+/=]+-----END CERTIFICATE-----", content
            )
        ) is None:
            raise InvalidPEMError("Could not find certificate")
        cert = Certificate.load_pem(CertificatePEM(cert_match.group(0)))

        if passphrase is not None:
            if (
                key_match := re.search(
                    r"-----BEGIN ENCRYPTED PRIVATE KEY-----[\s\w+/=]+-----END ENCRYPTED PRIVATE KEY-----",
                    content,
                )
            ) is None:
                raise InvalidPEMError("Could not find encrypted private key")
            key = RsaPrivateKey.load_pem(EncryptedPrivateKeyPEM(key_match.group(0)), passphrase)
        else:
            if (
                key_match := re.search(
                    r"-----BEGIN PRIVATE KEY-----[\s\w+/=]+-----END PRIVATE KEY-----", content
                )
            ) is None:
                raise InvalidPEMError("Could not find private key")
            key = RsaPrivateKey.load_pem(PlaintextPrivateKeyPEM(key_match.group(0)), None)

        return cls(
            certificate=cert,
            private_key=key,
        )

    def sign_csr(self, csr: CertificateSigningRequest, expiry: relativedelta) -> Certificate:
        """Create a certificate by signing a certificate signing request"""
        if not self.certificate.may_sign_certificates():
            raise ValueError("This certificate is not suitable for signing CSRs")

        if not csr.is_signature_valid:
            raise ValueError("CSR signature is not valid")

        # Add the DNS name of the subject CN as alternative name.
        # Our root CA has always done this, so for now this behavior is hardcoded.
        sans = x509.DNSName(csr.subject.common_name).value

        return Certificate._create(
            subject_public_key=csr.public_key,
            subject_name=csr.subject,
            subject_alt_dns_names=[sans],
            issuer_signing_key=self.private_key,
            issuer_name=self.certificate.subject,
            expiry=expiry,
            start_date=Certificate._naive_utcnow(),
            is_ca=False,
        )


class PersistedCertificateWithPrivateKey(CertificateWithPrivateKey):
    """
    A certificate & private key bundle locally stored on disk.

    For storing and loading encrypted private keys, the password must be provided to the respective
    methods. It is not stored by this class.
    """

    certificate_path: Path
    private_key_path: Path

    def __new__(
        cls,
        certificate_path: Path,
        certificate: Certificate,
        private_key_path: Path,
        private_key: RsaPrivateKey,
    ) -> PersistedCertificateWithPrivateKey:
        """
        Initialize the certificate bundle.

        No files are written to disk by this methods.
        """

        pcwpk = super().__new__(cls, certificate, private_key)
        pcwpk.certificate_path = certificate_path
        pcwpk.private_key_path = private_key_path

        return pcwpk

    @classmethod
    def read_files(
        cls,
        certificate_path: Path,
        private_key_path: Path,
        private_key_password: Password | None = None,
    ) -> PersistedCertificateWithPrivateKey:
        """
        Load a pair of PKCS8 PEM encoded X.509 certificate and private key.

        Provide the password if the private key is encrypted.
        """
        cert = Certificate.load_pem(CertificatePEM(certificate_path.read_bytes()))

        # bit verbose, as mypy thinks the PEM-NewTypes are bytes when I try to assign them directly
        pk_pem = private_key_path.read_bytes()
        if private_key_password is None:
            key = RsaPrivateKey.load_pem(PlaintextPrivateKeyPEM(pk_pem))
        else:
            key = RsaPrivateKey.load_pem(EncryptedPrivateKeyPEM(pk_pem), private_key_password)

        return PersistedCertificateWithPrivateKey(certificate_path, cert, private_key_path, key)

    @classmethod
    def persist(
        cls,
        certificate_with_key: CertificateWithPrivateKey,
        certificate_path: Path,
        private_key_path: Path,
        private_key_password: Password | None = None,
    ) -> PersistedCertificateWithPrivateKey:
        """Persist a `CertificateWithPrivateKey` instance to disk"""

        cert = certificate_with_key.certificate
        key = certificate_with_key.private_key
        pcwpk = PersistedCertificateWithPrivateKey(certificate_path, cert, private_key_path, key)
        pcwpk.write_files(private_key_password)
        return pcwpk

    def write_files(self, private_key_password: Password | None) -> None:
        """
        Write `certificate` to `certificate_path` and `private_key` to `private_key_path`.

        Files will be written in PKCS8 PEM encoding, an optional password can be provided for the
        private key.
        """

        self.certificate_path.touch(mode=0o600)
        self.private_key_path.touch(mode=0o600)
        self.certificate_path.write_bytes(self.certificate.dump_pem().bytes)
        self.private_key_path.write_bytes(self.private_key.dump_pem(private_key_password).bytes)


class Certificate:
    """An X.509 RSA certificate"""

    def __init__(self, certificate: x509.Certificate) -> None:
        """Wrap an cryptography.x509.Certificate (RSA keys only)"""

        if not isinstance(certificate.public_key(), rsa.RSAPublicKey):
            raise ValueError("Only RSA certificates are supported at this time")
        self._cert = certificate

    @classmethod
    def _create(
        cls,
        *,
        # subject info
        subject_public_key: RsaPublicKey,
        subject_name: X509Name,
        subject_alt_dns_names: list[str] | None = None,
        # cert properties
        expiry: relativedelta,
        start_date: datetime,
        is_ca: bool = False,
        # issuer info
        issuer_signing_key: RsaPrivateKey,
        issuer_name: X509Name,
    ) -> Certificate:
        """
        Internal method to create a new certificate. It makes a lot of assumptions about how our
        certificates are used and is not suitable for general use.
        """
        assert not Certificate._is_timezone_aware(
            start_date
        ), "Certificate expiry must use naive datetimes"

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name.name)
            .issuer_name(issuer_name.name)
            .not_valid_before(start_date)
            .not_valid_after(start_date + expiry)
            .serial_number(x509.random_serial_number())
            .public_key(subject_public_key._key)
        )

        # RFC 5280 4.2.1.9.  Basic Constraints
        basic_constraints = x509.BasicConstraints(ca=is_ca, path_length=0 if is_ca else None)
        builder = builder.add_extension(basic_constraints, critical=True)

        # RFC 5280 4.2.1.2.  Subject Key Identifier
        #     this extension MUST appear in all conforming CA certificates
        #     ...
        #     this extension SHOULD be included in all end entity certificates
        builder = builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(subject_public_key._key), critical=False
        )

        # RFC 5280 4.2.1.9.  Key Usage
        #
        # Currently only digital signature.
        # Note that some combinations of usage bits may have security implications. See
        # RFC 3279 2.3 and other links in RFC 5280 4.2.1.9. before enabling more usages.
        builder = builder.add_extension(
            x509.KeyUsage(
                # TODO: we need digital_signature for TLS
                digital_signature=not is_ca,  # signing data
                content_commitment=False,  # aka non_repudiation
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=is_ca,
                crl_sign=is_ca,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        if subject_alt_dns_names is not None:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName(san) for san in subject_alt_dns_names]),
                critical=False,
            )

        return Certificate(
            builder.sign(private_key=issuer_signing_key._key, algorithm=HashAlgorithm.Sha512.value)
        )

    @classmethod
    def load_pem(cls, pem_data: CertificatePEM) -> Certificate:
        try:
            return Certificate(x509.load_pem_x509_certificate(pem_data.bytes))
        except ValueError:
            raise InvalidPEMError("Unable to load certificate.")

    def dump_pem(self) -> CertificatePEM:
        return CertificatePEM(self._cert.public_bytes(serialization.Encoding.PEM))

    @property
    def serial_number(self) -> int:
        """The serial as a Python integer."""
        return self._cert.serial_number

    @property
    def serial_number_string(self) -> str:
        """
        The serial as a ':' separated hex string.

        This is the same format shown by 'openssl x509' and it looks like this:
            65:2e:18:0f:3f:a7:4b:c8:a6:fb:da:ea:bc:f8:57:f1:d0:96:5e:47
        """
        sn = self.serial_number
        return sn.to_bytes((sn.bit_length() + 7) // 8).hex(":")

    @property
    def public_key(self) -> RsaPublicKey:
        pk = self._cert.public_key()
        assert isinstance(pk, rsa.RSAPublicKey)
        return RsaPublicKey(pk)

    @property
    def subject(self) -> X509Name:
        return X509Name(self._cert.subject)

    @property
    def issuer(self) -> X509Name:
        return X509Name(self._cert.issuer)

    @property
    def common_name(self) -> str:
        return self.subject.common_name

    @property
    def organization_name(self) -> str | None:
        return self.subject.organization_name

    @property
    def not_valid_before(self) -> datetime:
        return self._cert.not_valid_before

    @property
    def not_valid_after(self) -> datetime:
        return self._cert.not_valid_after

    def verify_is_signed_by(self, signer: Certificate) -> None:
        """
        Verify that this certificate was signed by `signer`.

        Note that this check is not sufficient to verify the validity of the certificate, it only
        checks if the signature has been made by the public key in the given `signer` certificate.
        For example, THIS METHOD DOES NOT
            * validate the cert chain to a trusted root
            * check if certs are expired
            * check if certs are revoked

        :raise: InvalidSignatureError if the signature is not valid
        :raise: ValueError
                 * if the `signer` certificate's Key Usage does not allow certificate signature
                   verification (keyCertSign)
                 * if the signature scheme is not supported, see below

        We assume the signature is made with PKCS1 v1.5 padding, as this is the only scheme
        cryptography.io supports for X.509 certificates (see `RsaPublicKey.verify`). This is true
        for certificates created with `Certificate._create`, but might not be true for certificates
        loaded from elsewhere.
        """

        # Check if PKCS1 v1.5 padding is used. The scheme is identified as <hash>WithRSAEncryption
        # (RFC 4055 Section 5).
        # We only accept SHA256, SHA384 and SHA512. Unsupported schemes include MD5, SHA1,
        # RSAES-OAEP and RSASSA-PSS, and will lead to the error below.
        if (oid := self._cert.signature_algorithm_oid.dotted_string) not in [
            # https://oidref.com/1.2.840.113549.1.1
            "1.2.840.113549.1.1.11",  # sha256WithRSAEncryption
            "1.2.840.113549.1.1.12",  # sha384WithRSAEncryption
            "1.2.840.113549.1.1.13",  # sha512WithRSAEncryption
        ]:
            raise ValueError(f"Unsupported signature scheme for X.509 certificate ({oid})")

        # Check if the signer is allowed to sign certificates. Self-signed, non-CA certificates do
        # not need to set the usage bit. See also https://github.com/openssl/openssl/issues/1418.
        if not signer.may_sign_certificates() and not self._is_self_signed():
            raise ValueError(
                "Signer certificate does not allow certificate signature verification "
                "(CA flag or keyCertSign bit missing)."
            )

        signer.public_key.verify(
            Signature(self._cert.signature),
            self._cert.tbs_certificate_bytes,
            HashAlgorithm.from_cryptography(self._cert.signature_hash_algorithm),
        )

    def may_sign_certificates(self) -> bool:
        """
        Check if this certificate may be used to sign other certificates, that is, has the
        cA flag set and allows key usage KeyCertSign.

        Note that self-signed, non-CA end entity certificates may self-sign without this.
        """
        is_ca = False
        with contextlib.suppress(x509.ExtensionNotFound):
            is_ca = self._cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca

        has_key_sign_bit = False
        with contextlib.suppress(x509.ExtensionNotFound):
            has_key_sign_bit = self._cert.extensions.get_extension_for_class(
                x509.KeyUsage
            ).value.key_cert_sign

        return is_ca and has_key_sign_bit

    def _is_self_signed(self) -> bool:
        """Is the issuer the same as the subject?"""
        return self._cert.subject == self._cert.issuer

    def verify_expiry(self, allowed_drift: relativedelta | None = None) -> None:
        """
        Verify that the certificate is not expired and not "not yet valid", i.e. that the current
        time is between the certificate's "not_valid_before" and "not_valid_after".

        :param: allowed_drift can be provided to add tolerance for clock drift (default = 2 hours).

        :raise: InvalidExpiryError if the expiry is invalid.
        """
        if allowed_drift is None:
            allowed_drift = relativedelta(hours=+2)

        if self._is_not_valid_before(Certificate._naive_utcnow() + allowed_drift):
            raise InvalidExpiryError(
                f"Certificate is not yet valid (not_valid_before: {self._cert.not_valid_before})"
            )
        if self._is_expired_after(Certificate._naive_utcnow() - allowed_drift):
            raise InvalidExpiryError(
                f"Certificate is expired (not_valid_after: {self._cert.not_valid_after})"
            )

    def _is_not_valid_before(self, time: datetime) -> bool:
        assert not Certificate._is_timezone_aware(time)
        return time < self._cert.not_valid_before

    def _is_expired_after(self, time: datetime) -> bool:
        assert not Certificate._is_timezone_aware(time)
        return time > self._cert.not_valid_after

    def days_til_expiry(self) -> int:
        """
        Return the time remaining until the certificate expires in days (rounded down).

        This function should not be used to check certificate validity; use `verify_expiry()`
        instead. This function will not consider the certificate's "not_valid_before" attribute, so
        not-yet-valid certificates will not be detected here.
        If the certificate's "not_valid_after" time lies in the past, a negative value will be
        returned.
        """
        return (self._cert.not_valid_after - datetime.now()).days

    def fingerprint(self, algorithm: HashAlgorithm) -> bytes:
        """return the fingerprint

        >>> Certificate.load_pem(
        ...     CertificatePEM("\\n".join([
        ...         "-----BEGIN CERTIFICATE-----",
        ...         "MIIBYzCCAQ2gAwIBAgIUbPnfSpiyrseGMfzqs9QZF/QQWakwDQYJKoZIhvcNAQEF",
        ...         "BQAwHjENMAsGA1UEAwwEdW5pdDENMAsGA1UECgwEdGVzdDAeFw0yMzAyMDgwOTMw",
        ...         "NDRaFw0zMzAyMDgwOTMwNDRaMB4xDTALBgNVBAMMBHVuaXQxDTALBgNVBAoMBHRl",
        ...         "c3QwXDANBgkqhkiG9w0BAQEFAANLADBIAkEA0oU0G0Um+IztvdGmwgLiAf1srMCu",
        ...         "xi5SbZO+TyX6/e/yaTmRAvJv1159j+SYurqhKw6/UqI9PVhRyn/F+bkC2QIDAQAB",
        ...         "oyMwITAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBxjANBgkqhkiG9w0B",
        ...         "AQUFAANBALxBKfv6Z8zYbyGl4E5GqBSTltOwAOApoFCD1G+JJffwJ7axDstcYMPy",
        ...         "4Xll7GthxPWvXF+of3VAkEhv5qhIrKM=",
        ...         "-----END CERTIFICATE-----",
        ...     ]))
        ... ).fingerprint(HashAlgorithm.Sha256).hex()
        '9b567eaf29173dfddbc2e42e00023e65998a22475bc4a728fe0abdaaff364989'
        """
        return self._cert.fingerprint(algorithm.value)

    def get_subject_alt_names(self) -> list[str]:
        try:
            sans = self._cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            return []

        assert all(isinstance(x, str) for x in sans)
        # Well look at that assert...
        return sans  # type: ignore[no-any-return]

    @staticmethod
    def _is_timezone_aware(dt: datetime) -> bool:
        return dt.tzinfo is not None

    @staticmethod
    def _naive_utcnow() -> datetime:
        """
        Create a not timezone aware, "naive", datetime at UTC now. This mimics the deprecated
        datetime.utcnow(), but we still need it to be naive because that's what pyca/cryptography
        certificates use. See also https://github.com/pyca/cryptography/issues/9186.
        """
        return datetime.now(tz=timezone.utc).replace(tzinfo=None)


class RsaPrivateKey:
    """
    An unencrypted RSA private key.

    This class provides methods to generate, serialize and deserialize RSA private keys.
    """

    def __init__(self, key: rsa.RSAPrivateKey) -> None:
        self._key = key

    @classmethod
    def generate(cls, key_size: int) -> RsaPrivateKey:
        return RsaPrivateKey(rsa.generate_private_key(public_exponent=65537, key_size=key_size))

    @overload
    @classmethod
    def load_pem(cls, pem_data: PlaintextPrivateKeyPEM, password: None = None) -> RsaPrivateKey:
        ...

    @overload
    @classmethod
    def load_pem(cls, pem_data: EncryptedPrivateKeyPEM, password: Password) -> RsaPrivateKey:
        ...

    @classmethod
    def load_pem(
        cls,
        pem_data: EncryptedPrivateKeyPEM | PlaintextPrivateKeyPEM,
        password: Password | None = None,
    ) -> RsaPrivateKey:
        """
        Decode a PKCS8 PEM encoded RSA private key.

        `password` can be given if the key is encrypted.

        Raises:
            InvalidPEMError: if the PEM cannot be decoded.
            WrongPasswordError: if an encrypted PEM cannot be decrypted with the given password.
                NOTE: it seems we cannot rely on this error being raised. In the unit tests we
                sometimes saw an InvalidPEMError instead. Expect to see that as well.
            TypeError: when trying to load an EncryptedPrivateKeyPEM but no password is given.
                This would be caught by mypy though.

        >>> RsaPrivateKey.load_pem(EncryptedPrivateKeyPEM(""))
        Traceback (most recent call last):
            ...
        cmk.utils.crypto.certificate.InvalidPEMError

        >>> pem = EncryptedPrivateKeyPEM(
        ...     "\\n".join([
        ...         "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        ...         "MIIC3TBXBgkqhkiG9w0BBQ0wSjApBgkqhkiG9w0BBQwwHAQIMRfolchikB0CAggA",
        ...         "MAwGCCqGSIb3DQIJBQAwHQYJYIZIAWUDBAEqBBBvZ2ZdTgc5U+OgzNvBs3cXBIIC",
        ...         "gBe7tt6aHu+sfCvU8EzFqVbkf3f3qt6P/YEJZu4zXeGXrE+4D7E64PYooqGk+ZvU",
        ...         "/xyqHNoRzbAGEAqqEsMhZxjhQbgLmWVqGCJrqkkl8d5UlcG661AuevhYqIW8D3Bk",
        ...         "PfezIOnL+tDJuNb8y3KgQU0mqjUZ/BFLy6uTm6hQWeBluU5xtJ3C59o2JCP3pQwz",
        ...         "5V/EuLu0nLRSxCxDGcZqCr0s5A0AGv4U7xA9LEgER+ZuXLa2m+zp8VI8aR+1zUp+",
        ...         "lWq4rFY2UnA3DNayS/5QV0ljgDbE8Bzje6dwDhRiFUhgIwHa4C6EEDTajAXxbJEz",
        ...         "JebDaz9HLUMbfFdE2LYjagQx/kopb35eZUihZs3uHZXgXCQzeaaG7bunPBdiCuML",
        ...         "n0Cg+h13PmuH4eXuzcLEvwGzJrBrhenuYs/Vp9PYhwI7gIq+pqx7cgBprOge4xqM",
        ...         "gZbyhYoWCITEMg6lMYga1uZuBtvkel7/0PtC35qxdJyo5AEUCwSisY//t7oZownH",
        ...         "e8RlioxKnCisNxtcMYkPLmU68HNklZSX4/FrSd9zrWrpxC9XKKYeixe/RZPApeXO",
        ...         "phVLXl8KaX/xEAuonEZXH9XaZRnYA1Lg4Hl3lfbbHVffet9X1jpRRo4RCuQ+yQrJ",
        ...         "+YvX8SvnNAYHB1Pfp6aEqauUBR6FisUhHx2xahvnJ8y1GFNwY1VUEDdB63Ai0JVK",
        ...         "zIzEXU8/psX8xDh5Gm+n4ZVkgbuJQdvQgYLNT6vEglytEuJXYKFZQY4zX8J+vc3N",
        ...         "AVqHeoR61JEG+AcMdUgg2bO3vYorcQ8b3kwKkZzoBNeghMl6IS0Lj5tLVixweS5d",
        ...         "Rnp7GPpozA4jOM89/WEk+LE=",
        ...         "-----END ENCRYPTED PRIVATE KEY-----"
        ...     ])
        ... )

        >>> RsaPrivateKey.load_pem(pem, Password("foo"))
        <cmk.utils.crypto.certificate.RsaPrivateKey object at 0x...>

        >>> RsaPrivateKey.load_pem(pem, Password("not foo"))
        Traceback (most recent call last):
            ...
        cmk.utils.crypto.certificate.WrongPasswordError
        """

        pw = password.raw_bytes if password is not None else None
        try:
            return RsaPrivateKey(serialization.load_pem_private_key(pem_data.bytes, password=pw))
        except ValueError as exception:
            if str(exception) == "Bad decrypt. Incorrect password?":
                raise WrongPasswordError
            raise InvalidPEMError

    @overload
    def dump_pem(self, password: None) -> PlaintextPrivateKeyPEM:
        ...

    @overload
    def dump_pem(self, password: Password) -> EncryptedPrivateKeyPEM:
        ...

    def dump_pem(
        self, password: Password | None
    ) -> EncryptedPrivateKeyPEM | PlaintextPrivateKeyPEM:
        """
        Encode the private key in PKCS8 PEM (i.e. '-----BEGIN PRIVATE KEY-----...').

        If `password` is given, the key will be encrypted with the password
        (i.e. '-----BEGIN ENCRYPTED PRIVATE KEY-----...').
        """

        # mypy is convinced private_bytes() doesn't exist, I don't know why
        bytes_ = self._key.private_bytes(  # type: ignore[attr-defined]
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.raw_bytes)
            if password is not None
            else serialization.NoEncryption(),
        )
        if password is None:
            return PlaintextPrivateKeyPEM(bytes_)
        return EncryptedPrivateKeyPEM(bytes_)

    def dump_legacy_pkcs1(self) -> PlaintextPrivateKeyPEM:
        """Deprecated. Do not use.

        Encode the private key without encryption in PKCS#1 / OpenSSL format
        (i.e. '-----BEGIN RSA PRIVATE KEY-----...').
        """
        bytes_ = self._key.private_bytes(  # type: ignore[attr-defined]
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return PlaintextPrivateKeyPEM(bytes_)

    @property
    def public_key(self) -> RsaPublicKey:
        return RsaPublicKey(self._key.public_key())

    def sign_data(
        self, data: bytes, hash_algorithm: HashAlgorithm = HashAlgorithm.Sha512
    ) -> Signature:
        return Signature(self._key.sign(data, padding.PKCS1v15(), hash_algorithm.value))


class RsaPublicKey:
    def __init__(self, key: rsa.RSAPublicKey) -> None:
        self._key = key

    @classmethod
    def load_pem(cls, pem_data: PublicKeyPEM) -> RsaPublicKey:
        return RsaPublicKey(serialization.load_pem_public_key(pem_data.bytes))

    def dump_pem(self) -> PublicKeyPEM:
        # TODO: Use SubjectPublicKeyInfo format rather than PKCS1. PKCS1 doesn't include an
        # algorithm identifier.
        return PublicKeyPEM(
            self._key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.PKCS1,
            )
        )

    def dump_openssh(self) -> str:
        """Encode the public key in OpenSSH format (ssh-rsa AAAA...)"""
        return self._key.public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH,
        ).decode("utf-8")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RsaPublicKey):
            return NotImplemented
        return self._key.public_numbers() == other._key.public_numbers()

    def verify(self, signature: Signature, message: bytes, digest_algorithm: HashAlgorithm) -> None:
        # Currently the discouraged PKCS1 v1.5 padding is assumed. This is the only padding scheme
        # cryptography.io supports for signing X.509 certificates at this time.
        # See https://github.com/pyca/cryptography/issues/2850.
        # As long as our RsaPublic/PrivateKeys are only used for certificates there's no point in
        # supporting other schemes.
        padding_scheme = padding.PKCS1v15()

        try:
            self._key.verify(signature, message, padding_scheme, digest_algorithm.value)
        except cryptography.exceptions.InvalidSignature as e:
            raise InvalidSignatureError(e) from e


@dataclass
class X509Name:
    """Thin wrapper for X509 Name objects"""

    name: x509.Name

    @classmethod
    def create(
        cls,
        *,
        common_name: str,
        organization_name: str | None = None,
        organizational_unit: str | None = None,
    ) -> X509Name:
        if common_name == "":
            raise ValueError("common name must not be empty")

        attributes = [x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name)]
        if organization_name is not None:
            attributes.append(
                x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, organization_name)
            )
        if organizational_unit is not None:
            attributes.append(
                x509.NameAttribute(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME, organizational_unit)
            )

        return cls(x509.Name(attributes))

    def _get_name_attributes(self, attribute: x509.ObjectIdentifier) -> list[str]:
        return [attr.value for attr in self.name.get_attributes_for_oid(attribute)]

    @property
    def common_name(self) -> str:
        """Get the common name
        >>> print(X509Name.create(common_name="john", organizational_unit="corp").common_name)
        john
        """
        name = self._get_name_attributes(x509.oid.NameOID.COMMON_NAME)
        if (count := len(name)) != 1:
            raise ValueError(f"Expected to find exactly one common name, found {count}")
        return name[0]

    @property
    def organization_name(self) -> str | None:
        """Get the organization name, if set
        >>> print(X509Name.create(common_name="john", organizational_unit="unit").organization_name)
        None
        >>> print(
        ...     X509Name.create(
        ...         common_name="john", organization_name="corp", organizational_unit="unit"
        ...     ).organization_name
        ... )
        corp
        """
        name = self._get_name_attributes(x509.oid.NameOID.ORGANIZATION_NAME)
        if (count := len(name)) == 1:
            return name[0]
        if count == 0:
            return None
        raise ValueError(f"Expected to find at most one organization name, found {count}")

    @property
    def organizational_unit(self) -> str | None:
        """Get the organizational unit name, if set
        >>> print(
        ...     X509Name.create(
        ...         common_name="john", organization_name="corp"
        ...     ).organizational_unit
        ... )
        None
        >>> print(
        ...     X509Name.create(
        ...         common_name="john", organization_name="corp", organizational_unit="unit"
        ...     ).organizational_unit
        ... )
        unit
        """
        name = self._get_name_attributes(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME)
        if (count := len(name)) == 1:
            return name[0]
        if count == 0:
            return None
        raise ValueError(f"Expected to find at most one organizational unit name, found {count}")


@dataclass
class CertificateSigningRequest:
    """A request for some certificate authority to create and sign a certifiate for the requesting
    party. The requesting party is identified by its subject name and public key, and signs the CSR
    to prove its ownership of that public key.
    """

    csr: x509.CertificateSigningRequest

    @classmethod
    def create(
        cls, subject_name: X509Name, subject_private_key: RsaPrivateKey
    ) -> CertificateSigningRequest:
        """Create a new Certificate Signing Request

        Args:
            subject_name: The X509 name object of the requesting party as it will appear in the
                certificate. The common name must not be empty.
            subject_private_key: The RSA key whose public key should appear in the certificate.
                The private key is needed to sign the CSR and prove ownership of the public key.
        """

        builder = x509.CertificateSigningRequestBuilder().subject_name(subject_name.name)
        return cls(builder.sign(subject_private_key._key, HashAlgorithm.Sha512.value))

    @property
    def subject(self) -> X509Name:
        return X509Name(self.csr.subject)

    @property
    def public_key(self) -> RsaPublicKey:
        pk = self.csr.public_key()
        assert isinstance(pk, rsa.RSAPublicKey)
        return RsaPublicKey(pk)

    @property
    def is_signature_valid(self) -> bool:
        return self.csr.is_signature_valid
