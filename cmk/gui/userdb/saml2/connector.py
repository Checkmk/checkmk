#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import itertools
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.utils.redis import get_redis_client
from cmk.utils.type_defs import UserId

from cmk.gui.config import active_config
from cmk.gui.groups import load_contact_group_information
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.userdb.utils import get_connection, UserConnector, UserConnectorRegistry
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb.saml2.config import valuespec_to_config
from cmk.gui.userdb.saml2.interface import AuthenticatedUser, Interface
from cmk.gui.userdb.store import OpenFileMode, Users, UserStore

# TODO (lisa): introduce enums
SAML2_CONNECTOR_TYPE = "saml2"

LOGGER = logger.getChild("saml2")


class Connector(UserConnector):
    def __init__(self, raw_config: Mapping[str, Any]) -> None:
        super().__init__(raw_config)
        self.__config = valuespec_to_config(self._config)
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
        self, user_id: UserId, authenticated_user: AuthenticatedUser
    ) -> None:
        """Update user profile in Checkmk users store.

        A new user is created on the condition that a user with the same ID does not already exist
        for a different connection.

        Args:
            user_id: The unique ID of the user that is to be created or edited
            updated_user_profile: The profile of the user that should be entered in the Checkmk user store.
                If the profile attributes are not specified, the default profile is used. This can
                be configured via the global settings.

        Raises:
            ValueError:
                - The user exists, but the corresponding connection cannot be determined (e.g. when
                  a connection has been deleted)
                - The user already exists for a different connection
        """
        user_profile = authenticated_user_to_user_spec(
            authenticated_user,
            active_config.default_user_profile,
            contact_groups=set(load_contact_group_information().keys()),
        )
        user_profile["connector"] = self.__config.id

        with UserStore(mode=OpenFileMode.WRITE) as user_store:
            if not (user_entry := user_store.get(user_id)):
                user_store[user_id] = user_profile
                return

            self._update_user(
                user_id=user_id,
                user_profile=user_profile,
                connection_id=user_entry.get("connector"),
                user_store=user_store,
            )

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
            k for k, v in self.__config.interface_config.user_attributes.dict().items() if v
        ]


def authenticated_user_to_user_spec(
    authenticated_user: AuthenticatedUser,
    default_user_profile: UserSpec,
    *,
    contact_groups: set[str] | None = None,
) -> UserSpec:
    if contact_groups is None:
        contact_groups = set()

    user_spec = copy.deepcopy(default_user_profile)
    user_spec["user_id"] = authenticated_user.user_id
    user_spec["alias"] = authenticated_user.alias or authenticated_user.user_id
    if authenticated_user.email:
        # TODO (lisa): this seems to be wrongly typed. It is possible to create users without an
        # email
        user_spec["email"] = authenticated_user.email

    user_spec["contactgroups"] = list(
        set(
            itertools.chain(
                default_user_profile["contactgroups"],
                authenticated_user.contactgroups,
            )
        )
        & contact_groups
    )

    return user_spec


def register(user_connector_registry: UserConnectorRegistry) -> None:
    user_connector_registry.register(Connector)
