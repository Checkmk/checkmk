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
from datetime import datetime, timedelta
from logging import Logger
from pathlib import Path
from typing import Any, Literal

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.crypto import password_hashing
from cmk.utils.crypto.password import Password, PasswordHash
from cmk.utils.type_defs import UserId

import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundProcessInterface,
    InitialStatusArgs,
    job_registry,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.plugins.userdb.utils import (
    active_connections,
    ConnectorType,
    get_connection,
    get_user_attributes,
    new_user_template,
    user_attribute_registry,
    user_sync_config,
    UserAttribute,
    UserConnector,
)
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import TwoFactorCredentials, Users
from cmk.gui.userdb import user_attributes
from cmk.gui.userdb.htpasswd import Htpasswd
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
    UserSpec,
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

__all__ = [
    "contactgroups_of_user",
    "create_cmk_automation_user",
    "custom_attr_path",
    "get_last_activity",
    "get_online_user_ids",
    "load_contacts",
    "load_custom_attr",
    "load_multisite_users",
    "load_users",
    "remove_custom_attr",
    "rewrite_users",
    "save_custom_attr",
    "Users",
    "UserSpec",
    "write_contacts_and_users_file",
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


def create_non_existing_user(connection_id: str, username: UserId, now: datetime) -> None:
    # Since user_exists also looks into the htpasswd and treats all users that can be found there as
    # "existing users", we don't care about partially known users here and don't create them ad-hoc.
    # The load_users() method will handle this kind of users (TODO: Consolidate this!).
    # Which makes this function basically relevant for users that authenticate using an LDAP
    # connection and do not exist yet.
    if user_exists(username):
        return  # User exists. Nothing to do...

    users = load_users(lock=True)
    users[username] = new_user_template(connection_id)
    save_users(users, now)

    # Call the sync function for this new user
    connection = get_connection(connection_id)
    try:
        if connection is None:
            raise MKUserError(None, _("Invalid user connection: %s") % connection_id)

        connection.do_sync(
            add_to_changelog=False,
            only_username=username,
            load_users_func=load_users,
            save_users_func=save_users,
        )
    except MKLDAPException as e:
        show_exception(connection_id, _("Error during sync"), e, debug=active_config.debug)
    except Exception as e:
        show_exception(connection_id, _("Error during sync"), e)


def is_customer_user_allowed_to_login(user_id: UserId) -> bool:
    if not cmk_version.is_managed_edition():
        return True

    try:
        import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
    except ImportError:
        return True

    user = LoggedInUser(user_id)
    if managed.is_global(user.customer_id):
        return True

    return managed.is_current_customer(user.customer_id)


# This function is called very often during regular page loads so it has to be efficient
# even when having a lot of users.
#
# When using the multisite authentication with just by Setup created users it would be
# easy, but we also need to deal with users which are only existant in the htpasswd
# file and don't have a profile directory yet.
def user_exists(username: UserId) -> bool:
    if _user_exists_according_to_profile(username):
        return True

    return Htpasswd(Path(cmk.utils.paths.htpasswd_file)).exists(username)


def _user_exists_according_to_profile(username: UserId) -> bool:
    base_path = cmk.utils.paths.profile_dir / username
    return base_path.joinpath("transids.mk").exists() or base_path.joinpath("serial.mk").exists()


def _check_login_timeout(username: UserId, idle_time: float) -> None:
    idle_timeout = load_custom_attr(
        user_id=username, key="idle_timeout", parser=convert_idle_timeout
    )
    if idle_timeout is None:
        idle_timeout = active_config.user_idle_timeout
    if idle_timeout is not None and idle_timeout is not False and idle_time > idle_timeout:
        raise MKAuthException(f"{username} login timed out (Inactivity exceeded {idle_timeout})")


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
    return bool(load_two_factor_credentials(user_id)["webauthn_credentials"])


def disable_two_factor_authentication(user_id: UserId) -> None:
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["webauthn_credentials"].clear()
    save_two_factor_credentials(user_id, credentials)


def load_two_factor_credentials(user_id: UserId, lock: bool = False) -> TwoFactorCredentials:
    cred = load_custom_attr(
        user_id=user_id, key="two_factor_credentials", parser=ast.literal_eval, lock=lock
    )
    return TwoFactorCredentials(webauthn_credentials={}, backup_codes=[]) if cred is None else cred


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


def user_locked(user_id: UserId) -> bool:
    return bool(load_user(user_id).get("locked"))


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
    _check_login_timeout(username, now.timestamp() - session_info.last_activity)


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


# .
#   .-Hooks----------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_credentials(
    username: UserId, password: Password, now: datetime
) -> UserId | Literal[False]:
    """Verify the credentials given by a user using all auth connections"""
    for connection_id, connection in active_connections():
        # None        -> User unknown, means continue with other connectors
        # '<user_id>' -> success
        # False       -> failed
        result = connection.check_credentials(username, password)

        if result is False:
            return False

        if result is None:
            continue

        user_id: UserId = result
        if not isinstance(user_id, str):
            raise MKInternalError(
                _("The username returned by the %s connector is not of type string (%r).")
                % (connection_id, user_id)
            )

        # Check whether or not the user exists (and maybe create it)
        #
        # We have the cases where users exist "partially"
        # a) The htpasswd file of the site may have a username:pwhash data set
        #    and Checkmk does not have a user entry yet
        # b) LDAP authenticates a user and Checkmk does not have a user entry yet
        #
        # In these situations a user account with the "default profile" should be created
        create_non_existing_user(connection_id, user_id, now)

        if not is_customer_user_allowed_to_login(user_id):
            # A CME not assigned with the current sites customer
            # is not allowed to login
            auth_logger.debug("User '%s' is not allowed to login: Invalid customer" % user_id)
            return False

        # Now, after successfull login (and optional user account creation), check whether or
        # not the user is locked.
        if user_locked(user_id):
            auth_logger.debug("User '%s' is not allowed to login: Account locked" % user_id)
            return False  # The account is locked

        return user_id

    return False


def show_exception(connection_id: str, title: str, e: Exception, debug: bool = True) -> None:
    html.show_error(
        "<b>" + connection_id + " - " + title + "</b>"
        "<pre>%s</pre>" % (debug and traceback.format_exc() or e)
    )


def execute_userdb_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    if not userdb_sync_job_enabled():
        return

    job = UserSyncBackgroundJob()
    if job.is_active():
        gui_logger.debug("Another synchronization job is already running: Skipping this sync")
        return

    job.start(
        lambda job_interface: job.do_sync(
            job_interface=job_interface,
            add_to_changelog=False,
            enforce_sync=False,
            load_users_func=load_users,
            save_users_func=save_users,
        )
    )


def userdb_sync_job_enabled() -> bool:
    cfg = user_sync_config()

    if cfg is None:
        return False  # not enabled at all

    if cfg == "master" and is_wato_slave_site():
        return False

    return True


@cmk.gui.pages.register("ajax_userdb_sync")
def ajax_sync() -> None:
    try:
        job = UserSyncBackgroundJob()
        try:
            job.start(
                lambda job_interface: job.do_sync(
                    job_interface=job_interface,
                    add_to_changelog=False,
                    enforce_sync=True,
                    load_users_func=load_users,
                    save_users_func=save_users,
                )
            )
        except BackgroundJobAlreadyRunning as e:
            raise MKUserError(None, _("Another user synchronization is already running: %s") % e)
        response.set_data("OK Started synchronization\n")
    except Exception as e:
        gui_logger.exception("error synchronizing user DB")
        if active_config.debug:
            raise
        response.set_data("ERROR %s\n" % e)


@job_registry.register
class UserSyncBackgroundJob(BackgroundJob):
    job_prefix = "user_sync"

    @classmethod
    def gui_title(cls) -> str:
        return _("User synchronization")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                stoppable=False,
            ),
        )

    def _back_url(self) -> str:
        return makeuri_contextless(request, [("mode", "users")], filename="wato.py")

    def do_sync(
        self,
        job_interface: BackgroundProcessInterface,
        add_to_changelog: bool,
        enforce_sync: bool,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
    ) -> None:
        job_interface.send_progress_update(_("Synchronization started..."))
        if self._execute_sync_action(
            job_interface,
            add_to_changelog,
            enforce_sync,
            load_users_func,
            save_users_func,
            datetime.now(),
        ):
            job_interface.send_result_message(_("The user synchronization completed successfully."))
        else:
            job_interface.send_exception(_("The user synchronization failed."))

    def _execute_sync_action(
        self,
        job_interface: BackgroundProcessInterface,
        add_to_changelog: bool,
        enforce_sync: bool,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
        now: datetime,
    ) -> bool:
        for connection_id, connection in active_connections():
            try:
                if not enforce_sync and not connection.sync_is_needed():
                    continue

                job_interface.send_progress_update(
                    _("[%s] Starting sync for connection") % connection_id
                )
                connection.do_sync(
                    add_to_changelog=add_to_changelog,
                    only_username=None,
                    load_users_func=load_users,
                    save_users_func=save_users,
                )
                job_interface.send_progress_update(
                    _("[%s] Finished sync for connection") % connection_id
                )
            except Exception as e:
                job_interface.send_exception(_("[%s] Exception: %s") % (connection_id, e))
                gui_logger.error(
                    "Exception (%s, userdb_job): %s", connection_id, traceback.format_exc()
                )

        job_interface.send_progress_update(_("Finalizing synchronization"))
        general_userdb_job(now)
        return True


def execute_user_profile_cleanup_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    job = UserProfileCleanupBackgroundJob()
    if job.is_active():
        gui_logger.debug("Job is already running: Skipping this time")
        return

    interval = 3600
    with suppress(FileNotFoundError):
        if time.time() - UserProfileCleanupBackgroundJob.last_run_path().stat().st_mtime < interval:
            gui_logger.debug("Job was already executed within last %d seconds", interval)
            return

    job.start(job.do_execute)


@job_registry.register
class UserProfileCleanupBackgroundJob(BackgroundJob):
    job_prefix = "user_profile_cleanup"

    @staticmethod
    def last_run_path() -> Path:
        return Path(cmk.utils.paths.var_dir, "wato", "last_user_profile_cleanup.mk")

    @classmethod
    def gui_title(cls) -> str:
        return _("User profile cleanup")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                lock_wato=False,
                stoppable=False,
            ),
        )

    def do_execute(self, job_interface: BackgroundProcessInterface) -> None:
        try:
            cleanup_abandoned_profiles(self._logger, datetime.now(), timedelta(days=30))
            job_interface.send_result_message(_("Job finished"))
        finally:
            UserProfileCleanupBackgroundJob.last_run_path().touch(exist_ok=True)


def cleanup_abandoned_profiles(logger: Logger, now: datetime, max_age: timedelta) -> None:
    """Cleanup abandoned profile directories

    The cleanup is done like this:

    - Load the userdb to get the list of locally existing users
    - Iterate over all use profile directories and find all directories that don't belong to an
      existing user
    - For each of these directories find the most recent written file
    - In case the most recent written file is older than max_age days delete the profile directory
    - Create an audit log entry for each removed directory
    """
    users = set(load_users().keys())
    if not users:
        logger.warning("Found no users. Be careful and not cleaning up anything.")
        return

    profile_base_dir = cmk.utils.paths.profile_dir
    # Some files like ldap_*_sync_time.mk can be placed in
    # ~/var/check_mk/web, causing error entries in web.log while trying to
    # delete a dir
    profiles = {
        profile_dir.name for profile_dir in profile_base_dir.iterdir() if profile_dir.is_dir()
    }

    abandoned_profiles = sorted(profiles - users)
    if not abandoned_profiles:
        logger.debug("Found no abandoned profile.")
        return

    logger.info("Found %d abandoned profiles", len(abandoned_profiles))
    logger.debug("Profiles: %s", ", ".join(abandoned_profiles))

    for profile_name in abandoned_profiles:
        profile_dir = profile_base_dir / profile_name
        last_mtime = datetime.fromtimestamp(
            max((p.stat().st_mtime for p in profile_dir.glob("*.mk")), default=0.0)
        )
        if now - last_mtime > max_age:
            try:
                logger.info("Removing abandoned profile directory: %s", profile_name)
                shutil.rmtree(profile_dir)
            except OSError:
                logger.debug("Could not delete %s", profile_dir, exc_info=True)


def _register_user_attributes() -> None:
    user_attribute_registry.register(user_attributes.TemperatureUnitUserAttribute)
    user_attribute_registry.register(user_attributes.ForceAuthUserUserAttribute)
    user_attribute_registry.register(user_attributes.DisableNotificationsUserAttribute)
    user_attribute_registry.register(user_attributes.StartURLUserAttribute)
    user_attribute_registry.register(user_attributes.UIThemeUserAttribute)
    user_attribute_registry.register(user_attributes.UISidebarPosition)
    user_attribute_registry.register(user_attributes.UIIconTitle)
    user_attribute_registry.register(user_attributes.UIIconPlacement)
    user_attribute_registry.register(user_attributes.UIBasicAdvancedToggle)


_register_user_attributes()
