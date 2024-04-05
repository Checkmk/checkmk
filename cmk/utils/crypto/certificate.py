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

PublicKey/PrivateKey
    probably don't have a direct use case on their own in our code base, at the moment.

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import cryptography
import cryptography.hazmat.primitives.asymmetric as asym
import cryptography.x509 as x509
from cryptography.hazmat.primitives import serialization
from dateutil.relativedelta import relativedelta

from cmk.utils.crypto.keys import (
    EncryptedPrivateKeyPEM,
    InvalidSignatureError,
    PlaintextPrivateKeyPEM,
    PrivateKey,
    PublicKey,
)
from cmk.utils.crypto.password import Password
from cmk.utils.crypto.types import HashAlgorithm, InvalidPEMError, MKCryptoException, SerializedPEM
from cmk.utils.site import omd_site


class CertificatePEM(SerializedPEM):
    """A certificate in pem format"""


class InvalidExpiryError(MKCryptoException):
    """The certificate is either not yet valid or not valid anymore"""


class CertificateWithPrivateKey(NamedTuple):
    """A bundle of a certificate and its matching private key"""

    certificate: Certificate
    private_key: PrivateKey

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

        # Note: Various places in the code expect our own certs to use RSA at the moment.
        # At least: agent bakery and backups via key_mgmt.py, as well as the license server.
        private_key = PrivateKey.generate_rsa(key_size)
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
    def public_key(self) -> PublicKey:
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
            key = PrivateKey.load_pem(EncryptedPrivateKeyPEM(key_match.group(0)), passphrase)
        else:
            if (
                key_match := re.search(
                    r"-----BEGIN PRIVATE KEY-----[\s\w+/=]+-----END PRIVATE KEY-----", content
                )
            ) is None:
                raise InvalidPEMError("Could not find private key")
            key = PrivateKey.load_pem(PlaintextPrivateKeyPEM(key_match.group(0)), None)

        return cls(
            certificate=cert,
            private_key=key,
        )

    def sign_csr(self, csr: CertificateSigningRequest, expiry: relativedelta) -> Certificate:
        """
        Create a certificate by signing a certificate signing request.

        Note that the resulting certificate is NOT a CA. This means we don't do intermediate
        certificates at the moment.
        """
        if not self.certificate.may_sign_certificates():
            raise ValueError("This certificate is not suitable for signing CSRs")

        if not csr.is_signature_valid:
            raise ValueError("CSR signature is not valid")

        # Add the DNS name of the subject CN as alternative name.
        # Our root CA has always done this, so for now this behavior is hardcoded.
        if (cn := csr.subject.common_name) is None:
            raise ValueError("common name is expected for CSRs")

        return Certificate._create(
            subject_public_key=csr.public_key,
            subject_name=csr.subject,
            subject_alt_dns_names=[x509.DNSName(cn).value],
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
        private_key: PrivateKey,
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
            key = PrivateKey.load_pem(PlaintextPrivateKeyPEM(pk_pem))
        else:
            key = PrivateKey.load_pem(EncryptedPrivateKeyPEM(pk_pem), private_key_password)

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
        self._cert = certificate

    @classmethod
    def _create(
        cls,
        *,
        # subject info
        subject_public_key: PublicKey,
        subject_name: X509Name,
        subject_alt_dns_names: list[str] | None = None,
        # cert properties
        expiry: relativedelta,
        start_date: datetime,
        is_ca: bool = False,
        # issuer info
        issuer_signing_key: PrivateKey,
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

        return cls(
            builder.sign(private_key=issuer_signing_key._key, algorithm=HashAlgorithm.Sha512.value)
        )

    @classmethod
    def load_pem(cls, pem_data: CertificatePEM) -> Certificate:
        try:
            return cls(x509.load_pem_x509_certificate(pem_data.bytes))
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
    def public_key(self) -> PublicKey:
        key = self._cert.public_key()
        assert not isinstance(key, (asym.x448.X448PublicKey, asym.x25519.X25519PublicKey))
        return PublicKey(key)

    @property
    def subject(self) -> X509Name:
        return X509Name(self._cert.subject)

    @property
    def issuer(self) -> X509Name:
        return X509Name(self._cert.issuer)

    @property
    def common_name(self) -> str | None:
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
        :raise: ValueError if the `signer` certificate is not marked to sign certificates
                (see `may_sign_certificates`)
        """
        # Check if the signer is allowed to sign certificates. Self-signed, non-CA certificates do
        # not need to set the usage bit. See also https://github.com/openssl/openssl/issues/1418.
        if not signer.may_sign_certificates() and not self._is_self_signed():
            raise ValueError(
                "Signer certificate does not allow certificate signature verification "
                "(CA flag or keyCertSign bit missing)."
            )

        try:
            self._cert.verify_directly_issued_by(signer._cert)
        except cryptography.exceptions.InvalidSignature as e:
            raise InvalidSignatureError(str(e)) from e

    def may_sign_certificates(self) -> bool:
        """
        Check if this certificate may be used to sign other certificates, that is, has the
        cA flag set and allows key usage KeyCertSign (or does not restrict usage).

        Note that self-signed, non-CA end entity certificates may self-sign without this.
        """
        try:
            if not self._cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
                return False
        except x509.ExtensionNotFound:
            # This extension and flag MUST be set for a CA
            return False

        try:
            if not self._cert.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign:
                return False
        except x509.ExtensionNotFound:
            # If key usage is not restricted, that's ok
            pass

        return True

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
            ext = self._cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value
            assert isinstance(ext, x509.extensions.SubjectAlternativeName)
            sans = ext.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            return []

        return sans

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
        return [
            val.decode("utf-8") if isinstance(val := attr.value, bytes) else val
            for attr in self.name.get_attributes_for_oid(attribute)
        ]

    @property
    def common_name(self) -> str | None:
        """Get the common name
        >>> print(X509Name.create(common_name="john", organizational_unit="corp").common_name)
        john
        """
        name = self._get_name_attributes(x509.oid.NameOID.COMMON_NAME)
        if (count := len(name)) == 1:
            return name[0]
        if count == 0:
            return None
        raise ValueError(f"Expected to find at most one common name, found {count}")

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
        cls, subject_name: X509Name, subject_private_key: PrivateKey
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
    def public_key(self) -> PublicKey:
        key = self.csr.public_key()
        assert not isinstance(key, (asym.x448.X448PublicKey, asym.x25519.X25519PublicKey))
        return PublicKey(key)

    @property
    def is_signature_valid(self) -> bool:
        return self.csr.is_signature_valid
