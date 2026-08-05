#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from types import TracebackType
from typing import NamedTuple, Self

from tests.testlib.common.repo import repo_path
from tests.testlib.utils import run

logger = logging.getLogger(__name__)


class User(NamedTuple):
    uid: str
    ou: str
    cn: str
    sn: str
    password: str


class Group(NamedTuple):
    ou: str


class OpenLDAPManager:
    def __init__(
        self, groups: list[Group], users: list[User], ldif_path: Path, admin_password: str = "cmk"
    ) -> None:
        scripts_folder = repo_path() / "tests" / "scripts"
        self.setup_open_ldap_script = scripts_folder / "setup_openldap.sh"
        self.teardown_open_ldap_script = scripts_folder / "teardown_openldap.sh"
        self.groups = groups
        self.users = users
        self.content_file_path = ldif_path / "ldap_content.ldif"
        self.admin_password = admin_password

    def __enter__(self) -> Self:
        self.setup_open_ldap()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.teardown_open_ldap()

    def create_ldap_content_file(self) -> None:
        """Create an LDIF file with groups and users."""
        content = ""
        for group in self.groups:
            content += f"dn: ou={group.ou},dc=ldap,dc=local\n"
            content += "objectClass: organizationalUnit\n"
            content += f"ou: {group.ou}\n\n"

        for user in self.users:
            content += f"dn: uid={user.uid},ou={user.ou},dc=ldap,dc=local\n"
            content += (
                "objectclass: top\nobjectclass: person\nobjectclass: organizationalPerson\n"
                "objectclass: inetOrgPerson\n"
            )
            content += f"cn: {user.cn}\n"
            content += f"sn: {user.sn}\n"
            content += f"userPassword: {user.password}\n\n"

        with open(self.content_file_path, "w") as f:
            f.write(content)

    def setup_open_ldap(self) -> None:
        """Set up OpenLDAP using the prepared LDIF file."""
        logger.info("Setting up OpenLDAP...")
        self.create_ldap_content_file()
        run(
            [str(self.setup_open_ldap_script), self.admin_password, str(self.content_file_path)],
            sudo=True,
        )
        logger.info("OpenLDAP is set up")

    def teardown_open_ldap(self) -> None:
        """Delete OpenLDAP and related files."""
        logger.info("Deleting OpenLDAP and related files...")
        self.content_file_path.unlink()
        run([str(self.teardown_open_ldap_script)], sudo=True)
        logger.info("OpenLDAP is deleted")
