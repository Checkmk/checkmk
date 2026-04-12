#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal, override

from cmk import fields
from cmk.gui.ldap_integration.ldap_connector import LDAPUserConnector
from cmk.gui.userdb import connection_choices


class LDAPConnectionSuffix(fields.String):
    default_error_messages = {
        "should_exist": "The LDAP connection suffix {path!r} should exist but it doesn't.",
        "should_not_exist": "The LDAP connection suffix {path!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        required: bool = True,
        description: str = "The LDAP connection suffix can be used to distinguish equal named objects"
        " (name conflicts), for example user accounts, from different LDAP connections.",
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, description=description, **kwargs)
        self.presence = presence

    @override
    def _validate(self, value: str) -> None:
        super()._validate(value)

        if self.presence == "should_exist":
            if value not in LDAPUserConnector.get_connection_suffixes():
                raise self.make_error("should_exist", path=value)

        if self.presence == "should_not_exist":
            if value in LDAPUserConnector.get_connection_suffixes():
                raise self.make_error("should_not_exist", path=value)


class LDAPConnectionID(fields.String):
    default_error_messages = {
        "should_exist": "The LDAP connection {path!r} should exist but it doesn't.",
        "should_not_exist": "The LDAP connection {path!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        required: bool = True,
        description: str = "An LDAP connection ID string.",
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, description=description, **kwargs)
        self.presence = presence

    @override
    def _validate(self, value: str) -> None:
        super()._validate(value)

        ldap_connection_ids = [cnx_id for cnx_id, _ in connection_choices()]

        if self.presence == "should_exist":
            if value not in ldap_connection_ids:
                raise self.make_error("should_exist", path=value)

        if self.presence == "should_not_exist":
            if value in ldap_connection_ids:
                raise self.make_error("should_not_exist", path=value)
