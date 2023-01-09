#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Any

from pydantic import BaseModel

from cmk.utils.redis import get_redis_client
from cmk.utils.type_defs import UserId

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.userdb.utils import get_connection, UserConnector, UserConnectorRegistry
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb.saml2.interface import Interface, InterfaceConfig
from cmk.gui.userdb.store import OpenFileMode, Users, UserStore

# TODO (lisa): introduce enums
SAML2_CONNECTOR_TYPE = "saml2"

LOGGER = logger.getChild("saml2")


class ConnectorConfig(BaseModel):
    type: str
    version: str
    id: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    interface_config: InterfaceConfig
    create_users_on_login: bool


class Connector(UserConnector):
    def __init__(self, raw_config: dict[str, Any]) -> None:
        super().__init__(raw_config)
        self.__config = ConnectorConfig(**self._config)
        self.__interface = Interface(
            config=self.__config.interface_config, requests_db=get_redis_client()
        )

    @property
    def interface(self) -> Interface:
        return self.__interface

    @classmethod
    def type(cls) -> str:
        return SAML2_CONNECTOR_TYPE

    @property
    def id(self) -> str:
        return self.__config.id

    @classmethod
    def title(cls) -> str:
        return _("SAML Authentication")

    @classmethod
    def short_title(cls) -> str:
        return _("SAML 2.0")

    def is_enabled(self) -> bool:
        return not self.__config.disabled

    def identity_provider_url(self) -> str:
        return self.__config.interface_config.idp_metadata_endpoint

    def create_and_update_user(
        self, user_id: UserId, updated_user_profile: UserSpec | None = None
    ) -> None:
        """Update user profile in Checkmk users store.

        It can be configured whether to create new users when they first log in. In this case, the
        user is created on the condition that a user with the same ID does not already exist for a
        different connection.

        Args:
            user_id: The unique ID of the user that is to be created or edited
            updated_user_profile: The profile of the user that should be entered in the Checkmk user store.
                If not specified, the default profile is used. This can be configured via the global
                settings.

        Raises:
            ValueError:
                - The user does not exist, and it is not configured to create users
                - The user exists, but the corresponding connection cannot be determined (e.g. when
                  a connection has been deleted)
                - The user already exists for a different connection
        """
        if updated_user_profile is None:
            updated_user_profile = copy.deepcopy(active_config.default_user_profile)
            updated_user_profile["connector"] = self.__config.id
            updated_user_profile["alias"] = user_id

        with UserStore(mode=OpenFileMode.WRITE) as user_store:
            if not (user_entry := user_store.get(user_id)):
                self._create_user(user_id, updated_user_profile, user_store)
                return

            self._update_user(
                user_id=user_id,
                user_profile=updated_user_profile,
                connection_id=user_entry.get("connector"),
                user_store=user_store,
            )

    def _create_user(self, user_id: UserId, user_profile: UserSpec, user_store: Users) -> None:
        if not self.__config.create_users_on_login:
            LOGGER.debug("User %s does not exist, and not configured to create", repr(user_id))
            raise ValueError("User does not exist")

        user_store[user_id] = user_profile

    def _update_user(
        self, user_id: UserId, user_profile: UserSpec, user_store: Users, connection_id: str | None
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

        user_store[user_id] = user_profile


def register(user_connector_registry: UserConnectorRegistry) -> None:
    user_connector_registry.register(Connector)
