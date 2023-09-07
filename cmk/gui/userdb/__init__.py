#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Rework connection management and multiplexing
from __future__ import annotations

import ast
import shutil
import time
import traceback
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Any, Literal

import cmk.utils.paths
from cmk.utils.crypto import password_hashing
from cmk.utils.crypto.password import Password, PasswordHash
from cmk.utils.store.htpasswd import Htpasswd
from cmk.utils.user import UserId

import cmk.gui.utils as utils
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.pages import PageRegistry
from cmk.gui.plugins.userdb.utils import (
    active_connections,
    ConnectorType,
    get_connection,
    get_user_attributes,
    new_user_template,
    user_attribute_registry,
    user_sync_config,
    UserAttribute,
    UserAttributeRegistry,
    UserConnector,
)
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import TwoFactorCredentials, Users, UserSpec
from cmk.gui.userdb.ldap_connector import MKLDAPException
from cmk.gui.userdb.session import is_valid_user_session, load_session_infos
from cmk.gui.userdb.store import (
    contactgroups_of_user,
    convert_idle_timeout,
    create_cmk_automation_user,
    custom_attr_path,
    general_userdb_job,
    get_last_activity,
    get_online_user_ids,
    load_contacts,
    load_custom_attr,
    load_multisite_users,
    load_user,
    load_users,
    remove_custom_attr,
    rewrite_users,
    save_custom_attr,
    save_two_factor_credentials,
    save_users,
    write_contacts_and_users_file,
)
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import (
    DEF_VALUE,
    DropdownChoice,
    TextInput,
    Transform,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
)

from ._check_credentials import check_credentials as check_credentials
from ._check_credentials import create_non_existing_user as create_non_existing_user
from ._check_credentials import (
    is_customer_user_allowed_to_login as is_customer_user_allowed_to_login,
)
from ._check_credentials import user_exists as user_exists
from ._check_credentials import user_exists_according_to_profile as user_exists_according_to_profile
from ._check_credentials import user_locked as user_locked
from ._user_sync import UserSyncBackgroundJob as UserSyncBackgroundJob

__all__ = [
    "contactgroups_of_user",
    "create_cmk_automation_user",
    "custom_attr_path",
    "get_last_activity",
    "get_online_user_ids",
    "load_contacts",
    "load_custom_attr",
    "load_multisite_users",
    "load_user",
    "load_users",
    "remove_custom_attr",
    "rewrite_users",
    "save_custom_attr",
    "save_users",
    "Users",
    "UserSpec",
    "write_contacts_and_users_file",
    "UserSyncBackgroundJob",
]

auth_logger = gui_logger.getChild("auth")


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    utils.load_web_plugins("userdb", globals())


# The saved configuration for user connections is a bit inconsistent, let's fix
# this here once and for all.
def _fix_user_connections() -> None:
    for cfg in active_config.user_connections:
        # Although our current configuration always seems to have a 'disabled'
        # entry, this might not have always been the case.
        cfg.setdefault("disabled", False)
        # Only migrated configurations have a 'type' entry, all others are
        # implictly LDAP connections.
        cfg.setdefault("type", "ldap")


# When at least one LDAP connection is defined and active a sync is possible
def sync_possible() -> bool:
    return any(
        connection.type() == ConnectorType.LDAP
        for _connection_id, connection in active_connections()
    )


def locked_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific locked attributes"""
    return _get_attributes(connection_id, lambda c: c.locked_attributes())


def multisite_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific multisite attributes"""
    return _get_attributes(connection_id, lambda c: c.multisite_attributes())


def non_contact_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific non contact attributes"""
    return _get_attributes(connection_id, lambda c: c.non_contact_attributes())


def _get_attributes(
    connection_id: str | None, selector: Callable[[UserConnector], Sequence[str]]
) -> Sequence[str]:
    connection = get_connection(connection_id)
    return selector(connection) if connection else []


def _check_login_timeout(username: UserId, session_duration: float, idle_time: float) -> None:
    _handle_max_duration(username, session_duration)
    _handle_idle_timeout(username, idle_time)


def _handle_max_duration(username: UserId, session_duration: float) -> None:
    if (
        max_duration := active_config.session_mgmt.get("max_duration", {}).get("enforce_reauth")
    ) and session_duration > max_duration:
        raise MKAuthException(
            f"{username} login timed out (Maximum session duration of {max_duration / 60} minutes exceeded)"
        )


def _handle_idle_timeout(username: UserId, idle_time: float) -> None:
    idle_timeout = load_custom_attr(
        user_id=username, key="idle_timeout", parser=convert_idle_timeout
    )
    if idle_timeout is None:
        idle_timeout = active_config.session_mgmt.get("user_idle_timeout")
    if idle_timeout is not None and idle_timeout is not False and idle_time > idle_timeout:
        raise MKAuthException(
            f"{username} login timed out (Maximum inactivity of {idle_timeout / 60} minutes exceeded)"
        )


# userdb.need_to_change_pw returns either None or the reason description why the
# password needs to be changed
def need_to_change_pw(username: UserId, now: datetime) -> str | None:
    # Don't require password change for users from other connections, their passwords are not
    # managed here.
    user = load_user(username)
    if not _is_local_user(user):
        return None

    # Ignore the enforce_pw_change flag for automation users, they cannot change their passwords
    # themselves. (Password age is checked for them below though.)
    if (
        not is_automation_user(user)
        and load_custom_attr(user_id=username, key="enforce_pw_change", parser=utils.saveint) == 1
    ):
        return "enforced"

    last_pw_change = load_custom_attr(user_id=username, key="last_pw_change", parser=utils.saveint)
    max_pw_age = active_config.password_policy.get("max_age")
    if not max_pw_age:
        return None
    if not last_pw_change:
        # The age of the password is unknown. Assume the user has just set
        # the password to have the first access after enabling password aging
        # as starting point for the password period. This bewares all users
        # from needing to set a new password after enabling aging.
        save_custom_attr(username, "last_pw_change", str(int(now.timestamp())))
        return None
    if now.timestamp() - last_pw_change > max_pw_age:
        return "expired"
    return None


def is_two_factor_login_enabled(user_id: UserId) -> bool:
    """Whether or not 2FA is enabled for the given user"""
    return bool(
        load_two_factor_credentials(user_id)["webauthn_credentials"]
        or load_two_factor_credentials(user_id)["totp_credentials"]
    )


def disable_two_factor_authentication(user_id: UserId) -> None:
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["webauthn_credentials"].clear()
    credentials["totp_credentials"].clear()
    save_two_factor_credentials(user_id, credentials)


def load_two_factor_credentials(user_id: UserId, lock: bool = False) -> TwoFactorCredentials:
    cred = load_custom_attr(
        user_id=user_id, key="two_factor_credentials", parser=ast.literal_eval, lock=lock
    )
    return (
        TwoFactorCredentials(webauthn_credentials={}, backup_codes=[], totp_credentials={})
        if cred is None
        else cred
    )


def make_two_factor_backup_codes(
    *, rounds: int | None = None
) -> list[tuple[Password, PasswordHash]]:
    """Creates a set of new two factor backup codes

    The codes are returned in plain form for displaying and in hashed+salted form for storage
    """
    return [
        (password, password_hashing.hash_password(password))
        for password in (Password.random(10) for _ in range(10))
    ]


def is_two_factor_backup_code_valid(user_id: UserId, code: Password) -> bool:
    """Verifies whether or not the given backup code is valid and invalidates the code"""
    credentials = load_two_factor_credentials(user_id)
    matched_code = None

    for stored_code in credentials["backup_codes"]:
        try:
            password_hashing.verify(code, stored_code)
            matched_code = stored_code
            break
        except (password_hashing.PasswordInvalidError, ValueError):
            continue

    if matched_code is None:
        return False

    # Invalidate the just used code
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["backup_codes"].remove(matched_code)
    save_two_factor_credentials(user_id, credentials)

    return True


def _is_local_user(user: UserSpec) -> bool:
    return user.get("connector", "htpasswd") == "htpasswd"


def is_automation_user(user: UserSpec) -> bool:
    return "automation_secret" in user


class _UserSelection(DropdownChoice[UserId]):
    """Dropdown for choosing a multisite user"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        only_contacts: bool = False,
        only_automation: bool = False,
        none: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[UserId] = DEF_VALUE,
    ) -> None:
        super().__init__(
            choices=self._generate_wato_users_elements_function(
                none, only_contacts=only_contacts, only_automation=only_automation
            ),
            invalid_choice="complain",
            title=title,
            help=help,
            default_value=default_value,
        )

    def _generate_wato_users_elements_function(
        self,
        none_value: str | None,
        only_contacts: bool = False,
        only_automation: bool = False,
    ) -> Callable[[], list[tuple[UserId | None, str]]]:
        def get_wato_users(nv: str | None) -> list[tuple[UserId | None, str]]:
            users = load_users()
            elements: list[tuple[UserId | None, str]] = sorted(
                (name, "{} - {}".format(name, us.get("alias", name)))
                for (name, us) in users.items()
                if (not only_contacts or us.get("contactgroups"))
                and (not only_automation or us.get("automation_secret"))
            )
            if nv is not None:
                elements.insert(0, (None, nv))
            return elements

        return lambda: get_wato_users(none_value)

    def value_to_html(self, value: Any) -> ValueSpecText:
        return str(super().value_to_html(value)).rsplit(" - ", 1)[-1]


def UserSelection(  # pylint: disable=redefined-builtin
    only_contacts: bool = False,
    only_automation: bool = False,
    none: str | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[UserId] = DEF_VALUE,
) -> Transform[UserId | None]:
    return Transform(
        valuespec=_UserSelection(
            only_contacts=only_contacts,
            only_automation=only_automation,
            none=none,
            title=title,
            help=help,
            default_value=default_value,
        ),
        to_valuespec=lambda raw_str: None if raw_str is None else UserId(raw_str),
        from_valuespec=lambda uid: None if uid is None else str(uid),
    )


def on_failed_login(username: UserId, now: datetime) -> None:
    users = load_users(lock=True)
    if user := users.get(username):
        user["num_failed_logins"] = user.get("num_failed_logins", 0) + 1
        if active_config.lock_on_logon_failures:
            if user["num_failed_logins"] >= active_config.lock_on_logon_failures:
                user["locked"] = True
        save_users(users, now)

    if active_config.log_logon_failures:
        if user:
            existing = "Yes"
            log_msg_until_locked = str(
                bool(active_config.lock_on_logon_failures) - user["num_failed_logins"]
            )
            if not user.get("locked"):
                log_msg_locked = "No"
            elif log_msg_until_locked == "0":
                log_msg_locked = "Yes (now)"
            else:
                log_msg_locked = "Yes"
        else:
            existing = "No"
            log_msg_until_locked = "N/A"
            log_msg_locked = "N/A"
        auth_logger.warning(
            "Login failed for username: %s (existing: %s, locked: %s, failed logins until locked: %s), client: %s",
            username,
            existing,
            log_msg_locked,
            log_msg_until_locked,
            request.remote_ip,
        )


def on_access(username: UserId, session_id: str, now: datetime) -> None:
    """

    Raises:
        - MKAuthException: when the session given by session_id is not valid
        - MKAuthException: when the user has been idle for too long

    """
    session_infos = load_session_infos(username)
    if not is_valid_user_session(username, session_infos, session_id):
        raise MKAuthException("Invalid user session")

    # Check whether there is an idle timeout configured, delete cookie and
    # require the user to renew the log when the timeout exceeded.
    session_info = session_infos[session_id]
    _check_login_timeout(
        username,
        now.timestamp() - session_info.started_at,
        now.timestamp() - session_info.last_activity,
    )


# .
#   .-Users----------------------------------------------------------------.
#   |                       _   _                                          |
#   |                      | | | |___  ___ _ __ ___                        |
#   |                      | | | / __|/ _ \ '__/ __|                       |
#   |                      | |_| \__ \  __/ |  \__ \                       |
#   |                       \___/|___/\___|_|  |___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class GenericUserAttribute(UserAttribute):
    def __init__(
        self,
        user_editable: bool,
        show_in_table: bool,
        add_custom_macro: bool,
        domain: str,
        permission: str | None,
        from_config: bool,
    ) -> None:
        super().__init__()
        self._user_editable = user_editable
        self._show_in_table = show_in_table
        self._add_custom_macro = add_custom_macro
        self._domain = domain
        self._permission = permission
        self._from_config = from_config

    def from_config(self) -> bool:
        return self._from_config

    def user_editable(self) -> bool:
        return self._user_editable

    def permission(self) -> None | str:
        return self._permission

    def show_in_table(self) -> bool:
        return self._show_in_table

    def add_custom_macro(self) -> bool:
        return self._add_custom_macro

    def domain(self) -> str:
        return self._domain

    @classmethod
    def is_custom(cls) -> bool:
        return False


# .
#   .-Custom-Attrs.--------------------------------------------------------.
#   |   ____          _                          _   _   _                 |
#   |  / ___|   _ ___| |_ ___  _ __ ___         / \ | |_| |_ _ __ ___      |
#   | | |  | | | / __| __/ _ \| '_ ` _ \ _____ / _ \| __| __| '__/ __|     |
#   | | |__| |_| \__ \ || (_) | | | | | |_____/ ___ \ |_| |_| |  \__ \_    |
#   |  \____\__,_|___/\__\___/|_| |_| |_|    /_/   \_\__|\__|_|  |___(_)   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mange custom attributes of users (in future hosts etc.)              |
#   '----------------------------------------------------------------------'
def register_custom_user_attributes(attributes: list[dict[str, Any]]) -> None:
    for attr in attributes:
        if attr["type"] != "TextAscii":
            raise NotImplementedError()

        @user_attribute_registry.register
        class _LegacyUserAttribute(GenericUserAttribute):
            # Play safe: Grab all necessary data at class construction time,
            # it's highly unclear if the attr dict is mutated later or not.
            _name = attr["name"]
            _valuespec = TextInput(title=attr["title"], help=attr["help"])
            _topic = attr.get("topic", "personal")
            _user_editable = attr["user_editable"]
            _show_in_table = attr.get("show_in_table", False)
            _add_custom_macro = attr.get("add_custom_macro", False)

            @classmethod
            def name(cls) -> str:
                return cls._name

            def valuespec(self) -> ValueSpec:
                return self._valuespec

            def topic(self) -> str:
                return self._topic

            def __init__(self) -> None:
                super().__init__(
                    user_editable=self._user_editable,
                    show_in_table=self._show_in_table,
                    add_custom_macro=self._add_custom_macro,
                    domain="multisite",
                    permission=None,
                    from_config=True,
                )

            @classmethod
            def is_custom(cls) -> bool:
                return True

    cmk.gui.userdb.ldap_connector.register_user_attribute_sync_plugins()


def update_config_based_user_attributes() -> None:
    _clear_config_based_user_attributes()
    register_custom_user_attributes(active_config.wato_user_attrs)


def _clear_config_based_user_attributes() -> None:
    for _name, attr in get_user_attributes():
        if attr.from_config():
            user_attribute_registry.unregister(attr.name())
