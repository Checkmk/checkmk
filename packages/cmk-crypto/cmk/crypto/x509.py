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

X509NameOid: TypeAlias = pyca_x509.oid.NameOID


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
class SubjectAlternativeName:
    """One Subject Alternative Name for a certificate's SAN extension.

    Note that the "Subject Alternative Name" extension (`cryptography.x509.SubjectAlternativeName`)
    represents a list of names. This wrapper represents _one_ name, so really it's a wrapper around
    `cryptography.x509.GeneralName`.
    """

    name: pyca_x509.GeneralName

    @classmethod
    def dns_name(cls, name: str) -> SubjectAlternativeName:
        """Create a SubjectAlternativeName that represents a domain name.

        >>> SubjectAlternativeName.dns_name("test.example.com").name.value
        'test.example.com'
        """
        return cls(pyca_x509.DNSName(name))

    @classmethod
    def uuid(cls, name: UUID) -> SubjectAlternativeName:
        """Create a SubjectAlternativeName that represents a UUID.

        >>> SubjectAlternativeName.uuid(
        ...     UUID("12345678-1234-5678-1234-567812345678")
        ... ).name.value
        'urn:uuid:12345678-1234-5678-1234-567812345678'
        """
        return cls(pyca_x509.UniformResourceIdentifier(name.urn))
