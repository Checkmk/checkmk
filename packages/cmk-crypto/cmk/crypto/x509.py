#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helpers for x.509 certificates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias
from uuid import UUID

from cryptography import x509 as pyca_x509
from pyasn1.codec.der.decoder import decode as der_decode
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1.error import PyAsn1Error
from pyasn1.type.char import UTF8String

X509NameOid: TypeAlias = pyca_x509.oid.NameOID

# OID for internal use only
OID_CHECKMK_SITE_SITENAME = pyca_x509.ObjectIdentifier("1.3.6.1.4.1.677775.1.1")


@dataclass
class X509Name:
    """Thin wrapper for X509 Name objects.

    These are used to identify the subject and issuer in X509 certificates. We don't use all
    possible attributes. Only:
        - common name
        - organization name (optional)
        - organizational unit name (optional)
    """

    name: pyca_x509.Name

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

        attributes = [pyca_x509.NameAttribute(X509NameOid.COMMON_NAME, common_name)]
        if organization_name is not None:
            attributes.append(
                pyca_x509.NameAttribute(X509NameOid.ORGANIZATION_NAME, organization_name)
            )
        if organizational_unit is not None:
            attributes.append(
                pyca_x509.NameAttribute(X509NameOid.ORGANIZATIONAL_UNIT_NAME, organizational_unit)
            )

        return cls(pyca_x509.Name(attributes))

    def get_single_name_attribute(self, attribute: pyca_x509.oid.ObjectIdentifier) -> str | None:
        """
        Get an attribute, returning only the first if multiple are found.

        Use an OID from X509NameOid.
        """
        return attrs[0] if (attrs := self._get_name_attributes(attribute)) else None

    def _get_name_attributes(self, attribute: pyca_x509.oid.ObjectIdentifier) -> list[str]:
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
        return self.get_single_name_attribute(X509NameOid.COMMON_NAME)

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
        return self.get_single_name_attribute(X509NameOid.ORGANIZATION_NAME)

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
        return self.get_single_name_attribute(X509NameOid.ORGANIZATIONAL_UNIT_NAME)

    def rfc4514_string(self) -> str:
        """Return the name in RFC4514 format like "CN=John Doe,O=Example Corp,OU=Unit"."""
        return self.name.rfc4514_string()


@dataclass(frozen=True, slots=True)
class SAN:
    """One Subject Alternative Name for a certificate's SAN extension.

    Note that the "Subject Alternative Name" extension (`cryptography.x509.SubjectAlternativeName`)
    represents a list of names. This wrapper represents _one_ name, so really it's a wrapper around
    `cryptography.x509.GeneralName`.
    """

    name: pyca_x509.GeneralName

    @classmethod
    def dns_name(cls, name: str) -> SAN:
        """Create a SubjectAlternativeName that represents a domain name.

        >>> SAN.dns_name("test.example.com").name.value
        'test.example.com'
        """
        return cls(pyca_x509.DNSName(name))

    @classmethod
    def uuid(cls, name: UUID) -> SAN:
        """Create a SubjectAlternativeName that represents a UUID.

        >>> SAN.uuid(UUID("12345678-1234-5678-1234-567812345678")).name.value
        'urn:uuid:12345678-1234-5678-1234-567812345678'
        """
        return cls(pyca_x509.UniformResourceIdentifier(name.urn))

    @staticmethod
    def decode_site_name(san: SAN) -> str:
        """Decode a Checkmk site name.

        >>> SAN.decode_site_name(SAN.checkmk_site("morgen"))
        'morgen'
        """
        if (
            not isinstance(san.name, pyca_x509.OtherName)
            or san.name.type_id != OID_CHECKMK_SITE_SITENAME
        ):
            raise ValueError("Invalid Checkmk site name type")

        try:
            decoded, leftover = der_decode(san.name.value, UTF8String)
        except (TypeError, PyAsn1Error) as e:
            raise ValueError(f"Invalid Checkmk site name encoding: {e!r}")

        if leftover:
            raise ValueError("Invalid Checkmk site name encoding")

        return str(decoded.decode("utf-8"))

    @classmethod
    def checkmk_site(cls, name: str) -> SAN:
        """Create a SubjectAlternativeName that represents a Checkmk site name.

        Use `decode_site_name` to show the name:

            >>> SAN.decode_site_name(SAN.checkmk_site("❤️"))
            '❤️'

        Usually you only want to check that two names match though:

            >>> SAN.checkmk_site("morgen") == SAN.checkmk_site("morgen")
            True
            >>> SAN.checkmk_site("morgen") == SAN.checkmk_site("gestern")
            False
        """
        return cls(pyca_x509.OtherName(OID_CHECKMK_SITE_SITENAME, der_encode(UTF8String(name))))


class SubjectAlternativeNames(list[SAN]):
    """A helper for the x509.SubjectAlternativeName extension."""

    def to_extension(self) -> pyca_x509.SubjectAlternativeName:
        """Return the names as an x509.SubjectAlternativeName extension."""
        return pyca_x509.SubjectAlternativeName([name.name for name in self])

    @classmethod
    def from_extension(cls, ext: pyca_x509.SubjectAlternativeName) -> SubjectAlternativeNames:
        """Create a SubjectAlternativeNames object from an x509.SubjectAlternativeName extension."""
        dns_names = [SAN.dns_name(name) for name in ext.get_values_for_type(pyca_x509.DNSName)]
        uris = [
            SAN.uuid(UUID(uri))
            for uri in ext.get_values_for_type(pyca_x509.UniformResourceIdentifier)
        ]
        site_names = [
            SAN(name)
            for name in ext.get_values_for_type(pyca_x509.OtherName)
            if name.type_id == OID_CHECKMK_SITE_SITENAME
        ]
        return cls(dns_names + uris + site_names)

    @classmethod
    def find_extension(cls, extensions: pyca_x509.Extensions) -> SubjectAlternativeNames | None:
        """Find the subject alternative name extension in a list of extensions."""
        try:
            ext = extensions.get_extension_for_oid(
                pyca_x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value
        except pyca_x509.ExtensionNotFound:
            return None

        if not isinstance(ext, pyca_x509.SubjectAlternativeName):
            raise ValueError("Failed to get subject alternative names.")

        return cls.from_extension(ext)
