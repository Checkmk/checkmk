#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from cmk.utils.type_defs import UserId

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.userdb.utils import (
    get_connection,
    release_users_lock,
    UserConnector,
    UserConnectorRegistry,
)
from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.userdb.saml2.config import valuespec_to_config
from cmk.gui.userdb.saml2.interface import AuthenticatedUser
from cmk.gui.userdb.store import load_users, save_users

# TODO (lisa): introduce enums
SAML2_CONNECTOR_TYPE = "saml2"

LOGGER = logger.getChild("saml2")


class Connector(UserConnector):
    def __init__(self, raw_config: Mapping[str, Any]) -> None:
        super().__init__(raw_config)
        self.config = valuespec_to_config(self._config)

    @classmethod
    def type(cls) -> str:
        return SAML2_CONNECTOR_TYPE

    @property
    def id(self) -> str:
        return self.config.id

    @classmethod
    def title(cls) -> str:
        return _("SAML Authentication")

    @classmethod
    def short_title(cls) -> str:
        return _("SAML 2.0")

    def is_enabled(self) -> bool:
        return not self.config.disabled

    def create_and_update_user(self, user_id: UserId, user_profile: AuthenticatedUser) -> None:
        """Update user profile in Checkmk users store.

        A new user is created on the condition that a user with the same ID does not already exist
        for a different connection.

        Args:
            user_id: The unique ID of the user that is to be created or edited
            user_profile: The profile of the user that should be entered in the Checkmk user store.

        Raises:
            ValueError:
                - The user exists, but the corresponding connection cannot be determined (e.g. when
                  a connection has been deleted)
                - The user already exists for a different connection
        """
        user_spec = UserSpec(
            {
                "user_id": user_id,
                "alias": user_profile.alias,
                "contactgroups": list(user_profile.contactgroups),
                "force_authuser": user_profile.force_authuser,
                "roles": list(user_profile.roles),
                "connector": self.config.id,
            }
        )
        if user_profile.email:
            # TODO (lisa): this seems to be wrongly typed. It is possible to create users without an
            # email
            user_spec["email"] = user_profile.email

        try:
            self._create_and_update_user(
                user_id=user_id, user_spec=user_spec, users=load_users(lock=True)
            )
        finally:
            release_users_lock()

    def _create_and_update_user(self, user_id: UserId, user_spec: UserSpec, users: Users) -> None:
        if not (user_entry := users.get(user_id)):
            users[user_id] = user_spec
            save_users(users, datetime.now())  # releases the lock implicitly
            return

        self._update_user(
            user_id=user_id,
            user_profile=user_spec,
            current_user_entry=user_entry,
            connection_id=user_entry.get("connector"),
            users=users,
        )

    def _update_user(
        self,
        user_id: UserId,
        user_profile: UserSpec,
        users: Users,
        current_user_entry: UserSpec,
        connection_id: str | None,
    ) -> None:
        if not connection_id or not (connection := get_connection(connection_id)):
            LOGGER.debug(
                "Attempting to update user %s for connection %s, but does not exist",
                repr(user_id),
                connection_id,
            )
            raise ValueError("Unknown connection")

        if connection.id != self.id:
            LOGGER.debug(
                "Attempting to create user %s but already exists for connection %s of type %s",
                repr(user_id),
                connection.id,
                connection.type(),
            )
            raise ValueError("User already exists for different connection")

        if user_profile == current_user_entry:
            return

        users[user_id] = user_profile
        save_users(users, datetime.now())  # releases the lock implicitly

    def locked_attributes(self) -> Sequence[str]:
        """Attributes managed by the connector.

        List the names of user attributes that are managed automatically by the SAML2 connector, and
        may not be edited via the GUI. This always includes the 'password' attribute, as well as any
        other mapped attributes.

        Returns:
            A list of attributes managed by the connector, always containing at least the 'password'
            attribute.
        """
        return ["password"] + [
            k
            for k, v in self.config.interface_config.user_attributes.attribute_names.dict().items()
            if v
        ]


def register(user_connector_registry: UserConnectorRegistry) -> None:
    user_connector_registry.register(Connector)
