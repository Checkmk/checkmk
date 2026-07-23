#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Directory data types shared by the LDAP and SAML test fixtures."""

from collections.abc import Sequence
from dataclasses import dataclass

LDAP_BASE_DN = "dc=ldap,dc=local"
LDAP_USERS_OU = "users"
LDAP_GROUPS_OU = "groups"
LDAP_ADMIN_CN = "admin"


@dataclass(frozen=True)
class DirectoryUser:
    uid: str
    common_name: str
    surname: str
    password: str
    given_name: str = ""
    email: str = ""

    @property
    def dn(self) -> str:
        return f"uid={self.uid},ou={LDAP_USERS_OU},{LDAP_BASE_DN}"


@dataclass(frozen=True)
class Directory:
    """Static directory contents shared by the LDAP server and SAML IdP."""

    users: Sequence[DirectoryUser]
    admin_password: str = "cmk-admin"
    base_dn: str = LDAP_BASE_DN
    users_ou: str = LDAP_USERS_OU
    groups_ou: str = LDAP_GROUPS_OU

    @property
    def admin_dn(self) -> str:
        return f"cn={LDAP_ADMIN_CN},{self.base_dn}"

    @property
    def users_dn(self) -> str:
        return f"ou={self.users_ou},{self.base_dn}"


def default_directory() -> Directory:
    """Minimal directory for the SAML SSO tests: ``bob`` (primary) and ``carol`` (a fresh identity)."""
    return Directory(
        users=[
            DirectoryUser(
                uid="bob",
                common_name="Bob Example",
                surname="Example",
                given_name="Bob",
                password="bob-pwd",
                email="bob@example.com",
            ),
            DirectoryUser(
                uid="carol",
                common_name="Carol Example",
                surname="Example",
                given_name="Carol",
                password="carol-pwd",
                email="carol@example.com",
            ),
        ],
    )


def two_ldap_directories() -> tuple[Directory, Directory]:
    """Two single-user directories for the two-LDAP-connector tests.

    Distinct ``uid``s (``alice`` / ``dave``) so each connector contributes a user
    that uniquely identifies its source directory; both reuse the default base DN.
    """
    dir_a = Directory(
        users=[
            DirectoryUser(
                uid="alice",
                common_name="Alice Ldap",
                surname="Ldap",
                given_name="Alice",
                password="alice-pwd",
                email="alice@example.com",
            )
        ],
    )
    dir_b = Directory(
        users=[
            DirectoryUser(
                uid="dave",
                common_name="Dave Ldap",
                surname="Ldap",
                given_name="Dave",
                password="dave-pwd",
                email="dave@example.com",
            )
        ],
    )
    return dir_a, dir_b


def to_ldif(directory: Directory) -> str:
    """Return LDIF seeding the users and parent OU (suffix/admin come from the openldap image)."""
    lines: list[str] = [
        f"dn: ou={directory.users_ou},{directory.base_dn}",
        "objectClass: organizationalUnit",
        f"ou: {directory.users_ou}",
        "",
    ]
    for user in directory.users:
        lines.extend(
            [
                f"dn: {user.dn}",
                "objectClass: top",
                "objectClass: person",
                "objectClass: organizationalPerson",
                "objectClass: inetOrgPerson",
                f"uid: {user.uid}",
                f"cn: {user.common_name}",
                f"sn: {user.surname}",
                f"userPassword: {user.password}",
            ]
        )
        if user.given_name:
            lines.append(f"givenName: {user.given_name}")
        if user.email:
            lines.append(f"mail: {user.email}")
        lines.append("")
    return "\n".join(lines)
