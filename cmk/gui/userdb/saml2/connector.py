#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Any

from pydantic import BaseModel

from cmk.utils.type_defs import UserId

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.userdb.utils import get_connection, UserConnector, UserConnectorRegistry
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb.saml2.interface import Interface, InterfaceConfig
from cmk.gui.userdb.store import OpenFileMode, UserStore

# TODO (lisa): introduce enums
SAML2_CONNECTOR_TYPE = "saml2"

# TODO (CMK-11846): currently this logs to cmk.web.saml2 but it would be good to have dedicated logging
# for SAML that can be changed via the global settings
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
        self.__interface = Interface(self.__config.interface_config)

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

    def create_and_update_user(self, user_id: UserId, user_profile: UserSpec | None = None) -> None:
        """Update user profile in Checkmk users store.

        It can be configured whether to create new users when they first log in. In this case, the
        user is created on the condition that a user with the same ID does not already exist for a
        different connection.

        Args:
            user_id: The unique ID of the user that is to be created or edited
            user_profile: The profile of the user that should be updated in the Checkmk user store.
                If not specified, the default profile is used. This can be configured via the global
                settings.

        Raises:
            IndexError: when the user cannot be edited (either because it does not exist and it is
                not configured to create users automatically, or because the user already exists for a
                different connection).
        """
        if user_profile is None:
            user_profile = copy.deepcopy(active_config.default_user_profile)
            user_profile["connector"] = self.__config.id
            user_profile["alias"] = user_id

        with UserStore(mode=OpenFileMode.WRITE) as user_store:
            if (
                not (user_entry := user_store.get(user_id))
                and not self.__config.create_users_on_login
            ):
                LOGGER.debug("User %s does not exist, and not configured to create", user_id)
                raise IndexError("User does not exist")

            user_entry = user_store.setdefault(user_id, user_profile)

            if (
                connection := get_connection(user_entry["connector"])
            ) is not None and connection.type() != self.type():
                LOGGER.debug(
                    "Attempting to create user %s but already exists for connection %s",
                    (user_id, connection.type()),
                )
                raise IndexError("User already exists for different connection")

            user_entry.update(user_profile)


def register(user_connector_registry: UserConnectorRegistry) -> None:
    user_connector_registry.register(Connector)
