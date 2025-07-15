#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Generic, Literal, TypedDict, TypeVar

from cmk.ccc.user import UserId

from cmk.gui.type_defs import Users, UserSpec

from cmk.crypto.password import Password

CheckCredentialsResult = UserId | None | Literal[False]


class UserConnectionConfig(TypedDict):
    id: str
    disabled: bool


_T_Config = TypeVar("_T_Config", bound=UserConnectionConfig)


class UserConnector(abc.ABC, Generic[_T_Config]):
    def __init__(self, cfg: _T_Config) -> None:
        self._config = cfg

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        """The string representing this connector to humans"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def id(self) -> str:
        """The unique identifier of the connection"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def short_title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def config_changed(cls) -> None:
        return

    #
    # USERDB API METHODS
    #

    @abc.abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError()

    # Optional: Hook function can be registered here to be executed
    # to validate a login issued by a user.
    # Gets parameters: username, password
    # Has to return either:
    #     '<user_id>' -> Login succeeded
    #     False       -> Login failed
    #     None        -> Unknown user
    def check_credentials(self, user_id: UserId, password: Password) -> CheckCredentialsResult:
        return None

    # Optional: Hook function can be registered here to be executed
    # to synchronize all users.
    def do_sync(
        self,
        *,
        add_to_changelog: bool,
        only_username: UserId | None,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
    ) -> None:
        pass

    # Optional: Tells whether or not the synchronization (using do_sync()
    # method) is needed.
    def sync_is_needed(self) -> bool:
        return False

    # Optional: Hook function can be registered here to be xecuted
    # to save all users.
    def save_users(self, users: dict[UserId, UserSpec]) -> None:
        pass

    # List of user attributes locked for all users attached to this
    # connection. Those locked attributes are read-only in Setup.
    def locked_attributes(self) -> Sequence[str]:
        return []

    def multisite_attributes(self) -> Sequence[str]:
        return []

    def non_contact_attributes(self) -> Sequence[str]:
        return []


class ConnectorType:
    # TODO: should be improved to be an enum
    SAML2 = "saml2"
    LDAP = "ldap"
    HTPASSWD = "htpasswd"
    OAUTH2 = "oauth2"
