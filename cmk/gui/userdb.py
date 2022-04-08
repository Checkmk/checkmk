#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Rework connection management and multiplexing

import ast
import copy
import os
import shutil
import time
import traceback
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from six import ensure_str

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import ContactgroupName, UserId

import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.hooks as hooks
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.config import register_post_config_load_hook
from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.globals import active_config, html, request, response
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.plugins.userdb.htpasswd import Htpasswd
from cmk.gui.plugins.userdb.ldap_connector import MKLDAPException
from cmk.gui.plugins.userdb.utils import (
    active_connections,
    add_internal_attributes,
    get_connection,
    get_user_attributes,
    load_cached_profile,
    new_user_template,
    release_users_lock,
    save_cached_profile,
    user_attribute_registry,
    user_sync_config,
    UserAttribute,
    UserConnector,
)
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import SessionInfo, TwoFactorCredentials, UserSpec
from cmk.gui.utils.roles import roles_of_user
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import (
    DEF_VALUE,
    DropdownChoice,
    DropdownChoiceModel,
    TextInput,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
)

auth_logger = logger.getChild("auth")

Users = Dict[UserId, UserSpec]  # TODO: Improve this type


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


register_post_config_load_hook(_fix_user_connections)


# When at least one LDAP connection is defined and active a sync is possible
def sync_possible() -> bool:
    return any(connection.type() == "ldap" for _connection_id, connection in active_connections())


def locked_attributes(connection_id: Optional[str]) -> List[str]:
    """Returns a list of connection specific locked attributes"""
    return _get_attributes(connection_id, lambda c: c.locked_attributes())


def multisite_attributes(connection_id: Optional[str]) -> List[str]:
    """Returns a list of connection specific multisite attributes"""
    return _get_attributes(connection_id, lambda c: c.multisite_attributes())


def non_contact_attributes(connection_id: Optional[str]) -> List[str]:
    """Returns a list of connection specific non contact attributes"""
    return _get_attributes(connection_id, lambda c: c.non_contact_attributes())


def _get_attributes(
    connection_id: Optional[str], selector: Callable[[UserConnector], List[str]]
) -> List[str]:
    connection = get_connection(connection_id)
    return selector(connection) if connection else []


def create_non_existing_user(connection_id: str, username: UserId) -> None:
    # Since user_exists also looks into the htpasswd and treats all users that can be found there as
    # "existing users", we don't care about partially known users here and don't create them ad-hoc.
    # The load_users() method will handle this kind of users (TODO: Consolidate this!).
    # Which makes this function basically relevant for users that authenticate using an LDAP
    # connection and do not exist yet.
    if user_exists(username):
        return  # User exists. Nothing to do...

    users = load_users(lock=True)
    users[username] = new_user_template(connection_id)
    save_users(users)

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
# When using the multisite authentication with just by WATO created users it would be
# easy, but we also need to deal with users which are only existant in the htpasswd
# file and don't have a profile directory yet.
def user_exists(username: UserId) -> bool:
    if _user_exists_according_to_profile(username):
        return True

    return Htpasswd(Path(cmk.utils.paths.htpasswd_file)).exists(username)


def _user_exists_according_to_profile(username: UserId) -> bool:
    base_path = cmk.utils.paths.profile_dir / username
    return base_path.joinpath("transids.mk").exists() or base_path.joinpath("serial.mk").exists()


def _login_timed_out(username: UserId, last_activity: int) -> bool:
    idle_timeout = load_custom_attr(username, "idle_timeout", _convert_idle_timeout, None)
    if idle_timeout is None:
        idle_timeout = active_config.user_idle_timeout

    if idle_timeout in [None, False]:
        return False  # no timeout activated at all

    timed_out = (time.time() - last_activity) > idle_timeout
    return timed_out


def _reset_failed_logins(username: UserId) -> None:
    """Login succeeded: Set failed login counter to 0"""
    num_failed_logins = _load_failed_logins(username)
    if num_failed_logins != 0:
        _save_failed_logins(username, 0)


def _load_failed_logins(username: UserId) -> int:
    return load_custom_attr(username, "num_failed_logins", utils.saveint)


def _save_failed_logins(username: UserId, count: int) -> None:
    save_custom_attr(username, "num_failed_logins", str(count))


# userdb.need_to_change_pw returns either False or the reason description why the
# password needs to be changed
def need_to_change_pw(username: UserId) -> Union[bool, str]:
    if not _is_local_user(username):
        return False

    if load_custom_attr(username, "enforce_pw_change", utils.saveint) == 1:
        return "enforced"

    last_pw_change = load_custom_attr(username, "last_pw_change", utils.saveint)
    max_pw_age = active_config.password_policy.get("max_age")
    if max_pw_age:
        if not last_pw_change:
            # The age of the password is unknown. Assume the user has just set
            # the password to have the first access after enabling password aging
            # as starting point for the password period. This bewares all users
            # from needing to set a new password after enabling aging.
            save_custom_attr(username, "last_pw_change", str(int(time.time())))
            return False
        if time.time() - last_pw_change > max_pw_age:
            return "expired"
    return False


def is_two_factor_login_enabled(user_id: UserId) -> bool:
    """Whether or not 2FA is enabled for the given user"""
    return bool(load_two_factor_credentials(user_id)["webauthn_credentials"])


def disable_two_factor_authentication(user_id: UserId) -> None:
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["webauthn_credentials"].clear()
    save_two_factor_credentials(user_id, credentials)


def is_two_factor_completed() -> bool:
    """Whether or not the user has completed the 2FA challenge"""
    return session.session_info.two_factor_completed


def set_two_factor_completed() -> None:
    session.session_info.two_factor_completed = True


def load_two_factor_credentials(user_id: UserId, lock: bool = False) -> TwoFactorCredentials:
    return load_custom_attr(
        user_id,
        "two_factor_credentials",
        conv_func=ast.literal_eval,
        default=TwoFactorCredentials(
            {
                "webauthn_credentials": {},
                "backup_codes": [],
            }
        ),
        lock=lock,
    )


def save_two_factor_credentials(user_id: UserId, credentials: TwoFactorCredentials) -> None:
    save_custom_attr(user_id, "two_factor_credentials", repr(credentials))


def make_two_factor_backup_codes() -> Tuple[List[str], List[str]]:
    """Creates a set of new two factor backup codes

    The codes are returned in plain form for displaying and in hashed+salted form for storage
    """
    display_codes = []
    store_codes = []
    for _index in range(10):
        code = utils.get_random_string(10)
        display_codes.append(code)
        store_codes.append(cmk.gui.plugins.userdb.htpasswd.hash_password(code))
    return display_codes, store_codes


def is_two_factor_backup_code_valid(user_id: UserId, code: str) -> bool:
    """Verifies whether or not the given backup code is valid and invalidates the code"""
    credentials = load_two_factor_credentials(user_id)
    matched_code = ""
    for stored_code in credentials["backup_codes"]:
        if cmk.gui.plugins.userdb.htpasswd.check_password(code, stored_code):
            matched_code = stored_code
            break

    if not matched_code:
        return False

    # Invalidate the just used code
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["backup_codes"].remove(matched_code)
    save_two_factor_credentials(user_id, credentials)

    return True


def load_user(user_id: UserId) -> UserSpec:
    """Loads of a single user profile

    This is called during regular page processing. We must not load the whole user database, because
    that would take too much time. To optimize this, we have the "cached user profile" files which
    are read normally when working with a single user.
    """
    user = load_cached_profile(user_id)
    if user is None:
        # No cached profile present. Load all users to get the users data
        user = load_users(lock=False).get(user_id, {})
        assert user is not None  # help mypy
    return user


def _is_local_user(user_id: UserId) -> bool:
    return load_user(user_id).get("connector", "htpasswd") == "htpasswd"


def user_locked(user_id: UserId) -> bool:
    return load_user(user_id).get("locked", False)


def _root_dir() -> str:
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def _multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# TODO: Change to factory
class UserSelection(DropdownChoice):
    """Dropdown for choosing a multisite user"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        only_contacts: bool = False,
        only_automation: bool = False,
        none: Optional[str] = None,
        # ValueSpec
        title: Optional[str] = None,
        help: Optional[ValueSpecHelp] = None,
        default_value: ValueSpecDefault[DropdownChoiceModel] = DEF_VALUE,
    ) -> None:
        DropdownChoice.__init__(
            self,
            choices=self._generate_wato_users_elements_function(
                none, only_contacts=only_contacts, only_automation=only_automation
            ),
            invalid_choice="complain",
            title=title,
            help=help,
            default_value=default_value,
        )

    def _generate_wato_users_elements_function(
        self, none_value: Optional[str], only_contacts: bool = False, only_automation: bool = False
    ):
        def get_wato_users(nv: Optional[str]) -> List[Tuple[Optional[UserId], str]]:
            users = load_users()
            elements: List[Tuple[Optional[UserId], str]] = sorted(
                [
                    (name, "%s - %s" % (name, us.get("alias", name)))
                    for (name, us) in users.items()
                    if (not only_contacts or us.get("contactgroups"))
                    and (not only_automation or us.get("automation_secret"))
                ]
            )
            if nv is not None:
                elements.insert(0, (None, nv))
            return elements

        return lambda: get_wato_users(none_value)

    def value_to_html(self, value: Any) -> ValueSpecText:
        return str(super().value_to_html(value)).rsplit(" - ", 1)[-1]


def on_succeeded_login(username: UserId) -> str:
    _ensure_user_can_init_session(username)
    _reset_failed_logins(username)

    return _initialize_session(username)


def on_failed_login(username: UserId) -> None:
    users = load_users(lock=True)
    if username in users:
        if "num_failed_logins" in users[username]:
            users[username]["num_failed_logins"] += 1
        else:
            users[username]["num_failed_logins"] = 1

        if active_config.lock_on_logon_failures:
            if users[username]["num_failed_logins"] >= active_config.lock_on_logon_failures:
                users[username]["locked"] = True

        save_users(users)

    if active_config.log_logon_failures:
        log_details: List[str] = []
        if users.get(username):
            log_msg_until_locked: int = (
                active_config.lock_on_logon_failures - users[username]["num_failed_logins"]
            )
            log_msg_locked: str = "No"
            if users[username].get("locked"):
                log_msg_locked = "Yes"
                if log_msg_until_locked == 0:
                    log_msg_locked += " (now)"

            log_details.extend(
                [
                    "existing: Yes",
                    "locked: %s" % log_msg_locked,
                    "failed logins until locked: %d" % log_msg_until_locked,
                ]
            )
        else:
            log_details.extend(["existing: No", "locked: N/A", "failed logins until locked: N/A"])

        auth_logger.warning(
            "Login failed for username: %s (%s), client: %s",
            username,
            ", ".join(log_details),
            request.remote_ip,
        )


def on_logout(username: UserId, session_id: str) -> None:
    _invalidate_session(username, session_id)


def on_access(username: UserId, session_id: str) -> None:
    session_infos = _load_session_infos(username)

    if not _is_valid_user_session(username, session_infos, session_id):
        raise MKAuthException("Invalid user session")

    # Check whether or not there is an idle timeout configured, delete cookie and
    # require the user to renew the log when the timeout exceeded.
    session_info = session_infos[session_id]
    timed_out = _login_timed_out(username, session_info.last_activity)
    if timed_out:
        raise MKAuthException(
            "%s login timed out (Inactivity exceeded %r)"
            % (username, active_config.user_idle_timeout)
        )

    _set_session(username, session_info)


def on_end_of_request(user_id: UserId) -> None:
    if not session:
        return  # Nothing to be done in case there is no session

    assert user_id == session.user_id
    session_infos = _load_session_infos(user_id, lock=True)
    if session_infos:
        _refresh_session(user_id, session.session_info)
        session_infos[session.session_info.session_id] = session.session_info

    _save_session_infos(user_id, session_infos)


# .
#   .--User Session--------------------------------------------------------.
#   |       _   _                 ____                _                    |
#   |      | | | |___  ___ _ __  / ___|  ___  ___ ___(_) ___  _ __         |
#   |      | | | / __|/ _ \ '__| \___ \ / _ \/ __/ __| |/ _ \| '_ \        |
#   |      | |_| \__ \  __/ |     ___) |  __/\__ \__ \ | (_) | | | |       |
#   |       \___/|___/\___|_|    |____/ \___||___/___/_|\___/|_| |_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | When single users sessions are activated, a user an only login once  |
#   | a time. In case a user tries to login a second time, an error is     |
#   | shown to the later login.                                            |
#   |                                                                      |
#   | To make this feature possible a session ID is computed during login, |
#   | saved in the users cookie and stored in the user profile together    |
#   | with the current time as "last activity" timestamp. This timestamp   |
#   | is updated during each user activity in the GUI.                     |
#   |                                                                      |
#   | Once a user logs out or the "last activity" is older than the        |
#   | configured session timeout, the session is invalidated. The user     |
#   | can then login again from the same client or another one.            |
#   '----------------------------------------------------------------------'


@dataclass
class Session:
    """Container object for encapsulating the session of the currently logged in user"""

    user_id: UserId
    session_info: SessionInfo


session: Session = request_local_attr("session")


def _is_valid_user_session(
    username: UserId, session_infos: Dict[str, SessionInfo], session_id: str
) -> bool:
    """Return True in case this request is done with a currently valid user session"""
    if not session_infos:
        return False  # no session active

    if session_id not in session_infos:
        auth_logger.debug(
            "%s session_id %s not valid (logged out or timed out?)", username, session_id
        )
        return False

    return True


def _ensure_user_can_init_session(username: UserId) -> bool:
    """When single user session mode is enabled, check that there is not another active session"""
    if active_config.single_user_session is None:
        return True  # No login session limitation enabled, no validation

    session_timeout = active_config.single_user_session

    for session_info in _load_session_infos(username).values():
        if (time.time() - session_info.last_activity) > session_timeout:
            continue  # Former active session timed out

        auth_logger.debug(
            "%s another session is active (inactive for: %d seconds)"
            % (username, time.time() - session_info.last_activity)
        )

        raise MKUserError(None, _("Another session is active"))

    return True  # No session active


def _initialize_session(username: UserId) -> str:
    """Creates a new user login session (if single user session mode is enabled) and
    returns the session_id of the new session."""
    session_infos = _cleanup_old_sessions(_load_session_infos(username, lock=True))

    session_id = _create_session_id()
    now = int(time.time())
    session_info = SessionInfo(
        session_id=session_id,
        started_at=now,
        last_activity=now,
        flashes=[],
    )

    _set_session(username, session_info)
    session_infos[session_id] = session_info

    # Save once right after initialization. It may be saved another time later, in case something
    # was modified during the request (e.g. flashes were added)
    _save_session_infos(username, session_infos)

    return session_id


def _set_session(user_id: UserId, session_info: SessionInfo) -> None:
    request_local_attr().session = Session(user_id=user_id, session_info=session_info)


def _cleanup_old_sessions(session_infos: Dict[str, SessionInfo]) -> Dict[str, SessionInfo]:
    """Remove invalid / outdated sessions

    In single user session mode all sessions are removed. In regular mode, the sessions are limited
    to 20 per user. Sessions with an inactivity > 7 days are also removed.
    """
    if active_config.single_user_session:
        # In single user session mode there is only one session allowed at a time. Once we
        # reach this place, we can be sure that we are allowed to remove all existing ones.
        return {}

    return {
        s.session_id: s
        for s in sorted(session_infos.values(), key=lambda s: s.last_activity, reverse=True)[:20]
        if time.time() - s.last_activity < 86400 * 7
    }


def _create_session_id() -> str:
    """Creates a random session id for the user and returns it."""
    return utils.gen_id()


def _refresh_session(username: UserId, session_info: SessionInfo) -> None:
    """Updates the current session of the user"""
    session_info.last_activity = int(time.time())


def _invalidate_session(username: UserId, session_id: str) -> None:
    session_infos = _load_session_infos(username, lock=True)
    with suppress(KeyError):
        del session_infos[session_id]
        _save_session_infos(username, session_infos)


def _save_session_infos(username: UserId, session_infos: Dict[str, SessionInfo]) -> None:
    """Saves the sessions for the current user"""
    save_custom_attr(
        username, "session_info", repr({k: asdict(v) for k, v in session_infos.items()})
    )


def _load_session_infos(username: UserId, lock: bool = False) -> Dict[str, SessionInfo]:
    """Returns the stored sessions of the given user"""
    return load_custom_attr(username, "session_info", _convert_session_info, lock=lock) or {}


def _convert_session_info(value: str) -> Dict[str, SessionInfo]:
    if value == "":
        return {}

    if value.startswith("{"):
        return {k: SessionInfo(**v) for k, v in ast.literal_eval(value).items()}

    # Transform pre 2.0 values
    session_id, last_activity = value.split("|", 1)
    return {
        session_id: SessionInfo(
            session_id=session_id,
            # We don't have that information. The best guess is to use the last activitiy
            started_at=int(last_activity),
            last_activity=int(last_activity),
            flashes=[],
        ),
    }


def _convert_start_url(value: str) -> str:
    # TODO in Version 2.0.0 and 2.0.0p1 the value was written without repr(),
    # remove the if condition one day
    if value.startswith("'") and value.endswith("'"):
        return ast.literal_eval(value)
    return value


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
        permission: Optional[str],
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

    def permission(self) -> Optional[str]:
        return self._permission

    def show_in_table(self) -> bool:
        return self._show_in_table

    def add_custom_macro(self) -> bool:
        return self._add_custom_macro

    def domain(self) -> str:
        return self._domain


# TODO: Legacy plugin API. Converts to new internal structure. Drop this with 1.6 or later.
def declare_user_attribute(
    name: str,
    vs: ValueSpec,
    user_editable: bool = True,
    permission: Optional[str] = None,
    show_in_table: bool = False,
    topic: Optional[str] = None,
    add_custom_macro: bool = False,
    domain: str = "multisite",
    from_config: bool = False,
) -> None:

    # FIXME: The classmethods "name" and "topic" shadow the arguments from the function scope.
    # Any use off "name" and "topic" inside the class will result in a NameError.
    attr_name = name
    attr_topic = topic

    @user_attribute_registry.register
    class _LegacyUserAttribute(GenericUserAttribute):
        _name = attr_name
        _valuespec = vs
        _topic = attr_topic if attr_topic else "personal"

        @classmethod
        def name(cls) -> str:
            return cls._name

        @classmethod
        def valuespec(cls) -> ValueSpec:
            return cls._valuespec

        @classmethod
        def topic(cls) -> str:
            return cls._topic

        def __init__(self) -> None:
            super().__init__(
                user_editable=user_editable,
                show_in_table=show_in_table,
                add_custom_macro=add_custom_macro,
                domain=domain,
                permission=permission,
                from_config=from_config,
            )


def load_contacts() -> Dict[str, Any]:
    return store.load_from_mk_file(_contacts_filepath(), "contacts", {})


def _contacts_filepath() -> str:
    return _root_dir() + "contacts.mk"


def load_users_sanitized(lock: bool = False) -> Users:
    """load users but do not return some UserSpec attributes"""

    users = copy.deepcopy(load_users(lock=lock))
    for user_spec in users.values():
        user_spec.pop("automation_secret", None)
        user_spec.pop("password", None)
        user_spec.pop("session_info", None)
        user_spec.pop("two_factor_credentials", None)
    return users


@request_memoize()
def load_users(lock: bool = False) -> Users:
    if lock:
        # Note: the lock will be released on next save_users() call or at
        #       end of page request automatically.
        store.aquire_lock(_contacts_filepath())

    # First load monitoring contacts from Checkmk's world. If this is
    # the first time, then the file will be empty, which is no problem.
    # Execfile will the simply leave contacts = {} unchanged.
    # ? exact type of keys and items returned from load_mk_file seems to be unclear
    contacts = load_contacts()

    # Now load information about users from the GUI config world
    # ? can users dict be modified in load_mk_file function call and the type of keys str be changed?
    users = store.load_from_mk_file(_multisite_dir() + "users.mk", "multisite_users", {})

    # Merge them together. Monitoring users not known to Multisite
    # will be added later as normal users.
    result = {}
    for uid, user in users.items():
        # Transform user IDs which were stored with a wrong type
        uid = ensure_str(uid)  # pylint: disable= six-ensure-str-bin-call

        profile = contacts.get(uid, {})
        profile.update(user)
        result[uid] = profile

        # Convert non unicode mail addresses
        if "email" in profile:
            profile["email"] = ensure_str(  # pylint: disable= six-ensure-str-bin-call
                profile["email"]
            )

    # This loop is only neccessary if someone has edited
    # contacts.mk manually. But we want to support that as
    # far as possible.
    for uid, contact in contacts.items():

        if uid not in result:
            result[uid] = contact
            result[uid]["roles"] = ["user"]
            result[uid]["locked"] = True
            result[uid]["password"] = ""

    # Passwords are read directly from the apache htpasswd-file.
    # That way heroes of the command line will still be able to
    # change passwords with htpasswd. Users *only* appearing
    # in htpasswd will also be loaded and assigned to the role
    # they are getting according to the multisite old-style
    # configuration variables.

    def readlines(f: str) -> Iterable[str]:
        try:
            return Path(f).open(encoding="utf-8")
        except IOError:
            return []

    # FIXME TODO: Consolidate with htpasswd user connector
    for line in readlines(cmk.utils.paths.htpasswd_file):
        line = line.strip()
        if ":" in line:
            uid, password = line.strip().split(":")[:2]
            if password.startswith("!"):
                locked = True
                password = password[1:]
            else:
                locked = False
            if uid in result:
                result[uid]["password"] = password
                result[uid]["locked"] = locked
            else:
                # Create entry if this is an admin user
                new_user = UserSpec(
                    roles=roles_of_user(uid),
                    password=password,
                    locked=False,
                    connector="htpasswd",
                )

                add_internal_attributes(new_user)

                result[uid] = new_user
            # Make sure that the user has an alias
            result[uid].setdefault("alias", uid)
        # Other unknown entries will silently be dropped. Sorry...

    # Now read the serials, only process for existing users
    serials_file = "%s/auth.serials" % os.path.dirname(cmk.utils.paths.htpasswd_file)
    for line in readlines(serials_file):
        line = line.strip()
        if ":" in line:
            user_id, serial = line.split(":")[:2]
            if user_id in result:
                result[user_id]["serial"] = utils.saveint(serial)

    attributes: List[Tuple[str, Callable]] = [
        ("num_failed_logins", utils.saveint),
        ("last_pw_change", utils.saveint),
        ("enforce_pw_change", lambda x: bool(utils.saveint(x))),
        ("idle_timeout", _convert_idle_timeout),
        ("session_info", _convert_session_info),
        ("start_url", _convert_start_url),
        ("ui_theme", lambda x: x),
        ("two_factor_credentials", ast.literal_eval),
        ("ui_sidebar_position", lambda x: None if x == "None" else x),
    ]

    # Now read the user specific files
    directory = cmk.utils.paths.var_dir + "/web/"
    for uid in os.listdir(directory):
        if uid[0] != ".":

            # read special values from own files
            if uid in result:
                for attr, conv_func in attributes:
                    val = load_custom_attr(uid, attr, conv_func)
                    if val is not None:
                        result[uid][attr] = val

            # read automation secrets and add them to existing
            # users or create new users automatically
            try:
                user_secret_path = Path(directory) / uid / "automation.secret"
                with user_secret_path.open(encoding="utf-8") as f:
                    secret: Optional[str] = f.read().strip()
            except IOError:
                secret = None

            if secret:
                if uid in result:
                    result[uid]["automation_secret"] = secret
                else:
                    result[uid] = {
                        "roles": ["guest"],
                        "automation_secret": secret,
                    }

    return result


def custom_attr_path(userid: UserId, key: str) -> str:
    return cmk.utils.paths.var_dir + "/web/" + userid + "/" + key + ".mk"


def load_custom_attr(
    userid: UserId,
    key: str,
    conv_func: Callable[[str], Any],
    default: Optional[Any] = None,
    lock: bool = False,
) -> Any:
    path = Path(custom_attr_path(userid, key))
    result = store.load_text_from_file(path, default=default, lock=lock)  # type: ignore[arg-type]
    if result == default:
        return result
    return conv_func(result.strip())


def save_custom_attr(userid: UserId, key: str, val: Any) -> None:
    path = custom_attr_path(userid, key)
    store.mkdir(os.path.dirname(path))
    store.save_text_to_file(path, "%s\n" % val)


def remove_custom_attr(userid: UserId, key: str) -> None:
    try:
        os.unlink(custom_attr_path(userid, key))
    except OSError:
        pass  # Ignore non existing files


def get_online_user_ids() -> List[UserId]:
    online_threshold = time.time() - active_config.user_online_maxage
    users = []
    for user_id, user in load_users(lock=False).items():
        if get_last_activity(user) >= online_threshold:
            users.append(user_id)
    return users


def get_last_activity(user: UserSpec) -> int:
    return max([s.last_activity for s in user.get("session_info", {}).values()] + [0])


def split_dict(d: Mapping[str, Any], keylist: List[str], positive: bool) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if (k in keylist) == positive}


def save_users(profiles: Users) -> None:
    write_contacts_and_users_file(profiles)

    # Execute user connector save hooks
    hook_save(profiles)

    updated_profiles = _add_custom_macro_attributes(profiles)

    _save_auth_serials(updated_profiles)
    _save_user_profiles(updated_profiles)
    _cleanup_old_user_profiles(updated_profiles)

    # Release the lock to make other threads access possible again asap
    # This lock is set by load_users() only in the case something is expected
    # to be written (like during user syncs, wato, ...)
    release_users_lock()

    # Invalidate the users memoized data
    load_users.cache_clear()

    # Call the users_saved hook
    hooks.call("users-saved", updated_profiles)


# TODO: Isn't this needed only while generating the contacts.mk?
#       Check this and move it to the right place
def _add_custom_macro_attributes(profiles: Users) -> Users:
    updated_profiles = copy.deepcopy(profiles)

    # Add custom macros
    core_custom_macros = set(
        name for name, attr in get_user_attributes() if attr.add_custom_macro()  #
    )
    for user in updated_profiles.keys():
        for macro in core_custom_macros:
            if macro in updated_profiles[user]:
                # UserSpec is now a TypedDict, unfortunately not complete yet,
                # thanks to such constructs.
                updated_profiles[user]["_" + macro] = updated_profiles[user][macro]  # type: ignore[literal-required]

    return updated_profiles


# Write user specific files
def _save_user_profiles(updated_profiles: Users) -> None:
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()

    for user_id, user in updated_profiles.items():
        user_dir = cmk.utils.paths.var_dir + "/web/" + user_id
        store.mkdir(user_dir)

        # authentication secret for local processes
        auth_file = user_dir + "/automation.secret"
        if "automation_secret" in user:
            store.save_text_to_file(auth_file, "%s\n" % user["automation_secret"])
        elif os.path.exists(auth_file):
            os.unlink(auth_file)

        # Write out user attributes which are written to dedicated files in the user
        # profile directory. The primary reason to have separate files, is to reduce
        # the amount of data to be loaded during regular page processing
        save_custom_attr(user_id, "serial", str(user.get("serial", 0)))
        save_custom_attr(user_id, "num_failed_logins", str(user.get("num_failed_logins", 0)))
        save_custom_attr(
            user_id, "enforce_pw_change", str(int(user.get("enforce_pw_change", False)))
        )
        save_custom_attr(
            user_id, "last_pw_change", str(user.get("last_pw_change", int(time.time())))
        )

        if "idle_timeout" in user:
            save_custom_attr(user_id, "idle_timeout", user["idle_timeout"])
        else:
            remove_custom_attr(user_id, "idle_timeout")

        if user.get("start_url") is not None:
            save_custom_attr(user_id, "start_url", repr(user["start_url"]))
        else:
            remove_custom_attr(user_id, "start_url")

        if user.get("two_factor_credentials") is not None:
            save_two_factor_credentials(user_id, user["two_factor_credentials"])
        else:
            remove_custom_attr(user_id, "two_factor_credentials")

        # Is None on first load
        if user.get("ui_theme") is not None:
            save_custom_attr(user_id, "ui_theme", user["ui_theme"])
        else:
            remove_custom_attr(user_id, "ui_theme")

        if "ui_sidebar_position" in user:
            save_custom_attr(user_id, "ui_sidebar_position", user["ui_sidebar_position"])
        else:
            remove_custom_attr(user_id, "ui_sidebar_position")

        _save_cached_profile(user_id, user, multisite_keys, non_contact_keys)


# During deletion of users we don't delete files which might contain user settings
# and e.g. customized views which are not easy to reproduce. We want to keep the
# files which are the result of a lot of work even when e.g. the LDAP sync deletes
# a user by accident. But for some internal files it is ok to delete them.
#
# Be aware: The user_exists() function relies on these files to be deleted.
def _cleanup_old_user_profiles(updated_profiles: Users) -> None:
    profile_files_to_delete = [
        "automation.secret",
        "transids.mk",
        "serial.mk",
    ]
    directory = cmk.utils.paths.var_dir + "/web"
    for user_dir in os.listdir(cmk.utils.paths.var_dir + "/web"):
        if user_dir not in [".", ".."] and user_dir not in updated_profiles:
            entry = directory + "/" + user_dir
            if not os.path.isdir(entry):
                continue

            for to_delete in profile_files_to_delete:
                if os.path.exists(entry + "/" + to_delete):
                    os.unlink(entry + "/" + to_delete)


def write_contacts_and_users_file(
    profiles: Users, custom_default_config_dir: Optional[str] = None
) -> None:
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()
    updated_profiles = _add_custom_macro_attributes(profiles)

    if custom_default_config_dir:
        check_mk_config_dir = "%s/conf.d/wato" % custom_default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % custom_default_config_dir
    else:
        check_mk_config_dir = "%s/conf.d/wato" % cmk.utils.paths.default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % cmk.utils.paths.default_config_dir

    non_contact_attributes_cache: Dict[Optional[str], List[str]] = {}
    multisite_attributes_cache: Dict[Optional[str], List[str]] = {}
    for user_settings in updated_profiles.values():
        connector = cast(Optional[str], user_settings.get("connector"))
        if connector not in non_contact_attributes_cache:
            non_contact_attributes_cache[connector] = non_contact_attributes(connector)
        if connector not in multisite_attributes_cache:
            multisite_attributes_cache[connector] = multisite_attributes(connector)

    # Remove multisite keys in contacts.
    # TODO: Clean this up. Just improved the performance, but still have no idea what its actually doing...
    contacts = dict(
        e
        for e in [
            (
                id,
                split_dict(
                    user,
                    non_contact_keys + non_contact_attributes_cache[user.get("connector")],
                    False,
                ),
            )
            for (id, user) in updated_profiles.items()
        ]
    )

    # Only allow explicitely defined attributes to be written to multisite config
    users = {}
    for uid, profile in updated_profiles.items():
        users[uid] = {
            p: val
            for p, val in profile.items()
            if p in multisite_keys + multisite_attributes_cache[profile.get("connector")]
        }

    # Checkmk's monitoring contacts
    store.save_to_mk_file(
        "%s/%s" % (check_mk_config_dir, "contacts.mk"),
        "contacts",
        contacts,
        pprint_value=active_config.wato_pprint_config,
    )

    # GUI specific user configuration
    store.save_to_mk_file(
        "%s/%s" % (multisite_config_dir, "users.mk"),
        "multisite_users",
        users,
        pprint_value=active_config.wato_pprint_config,
    )


def _non_contact_keys() -> List[str]:
    """User attributes not to put into contact definitions for Check_MK"""
    return [
        "automation_secret",
        "connector",
        "enforce_pw_change",
        "idle_timeout",
        "language",
        "last_pw_change",
        "locked",
        "num_failed_logins",
        "password",
        "roles",
        "serial",
        "session_info",
        "two_factor_credentials",
    ] + _get_multisite_custom_variable_names()


def _multisite_keys() -> List[str]:
    """User attributes to put into multisite configuration"""
    multisite_variables = [
        var
        for var in _get_multisite_custom_variable_names()
        if var not in ("start_url", "ui_theme", "ui_sidebar_position")
    ]
    return [
        "roles",
        "locked",
        "automation_secret",
        "alias",
        "language",
        "connector",
    ] + multisite_variables


def _get_multisite_custom_variable_names() -> List[str]:
    return [name for name, attr in get_user_attributes() if attr.domain() == "multisite"]  #


def _save_auth_serials(updated_profiles: Users) -> None:
    """Write out the users serials"""
    # Write out the users serials
    serials = ""
    for user_id, user in updated_profiles.items():
        serials += "%s:%d\n" % (user_id, user.get("serial", 0))
    store.save_text_to_file(
        "%s/auth.serials" % os.path.dirname(cmk.utils.paths.htpasswd_file), serials
    )


def rewrite_users() -> None:
    users = load_users(lock=True)
    save_users(users)


def create_cmk_automation_user() -> None:
    secret = utils.gen_id()

    users = load_users(lock=True)
    users[UserId("automation")] = {
        "alias": "Check_MK Automation - used for calling web services",
        "contactgroups": [],
        "automation_secret": secret,
        "password": cmk.gui.plugins.userdb.htpasswd.hash_password(secret),
        "roles": ["admin"],
        "locked": False,
        "serial": 0,
        "email": "",
        "pager": "",
        "notifications_enabled": False,
        "language": "en",
        "connector": "htpasswd",
    }
    save_users(users)


def _save_cached_profile(
    user_id: UserId, user: UserSpec, multisite_keys: List[str], non_contact_keys: List[str]
) -> None:
    # Only save contact AND multisite attributes to the profile. Not the
    # infos that are stored in the custom attribute files.
    cache = UserSpec()
    for key in user.keys():
        if key in multisite_keys or key not in non_contact_keys:
            # UserSpec is now a TypedDict, unfortunately not complete yet, thanks to such constructs.
            cache[key] = user[key]  # type: ignore[literal-required]

    save_cached_profile(user_id, cache)


def contactgroups_of_user(user_id: UserId) -> List[ContactgroupName]:
    return load_user(user_id).get("contactgroups", [])


def _convert_idle_timeout(value: str) -> Union[int, bool, None]:
    if value == "False":
        return False  # Idle timeout disabled

    try:
        return int(value)
    except ValueError:
        return None  # Invalid value -> use global setting


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


def update_config_based_user_attributes() -> None:
    _clear_config_based_user_attributes()

    for attr in active_config.wato_user_attrs:
        if attr["type"] == "TextAscii":
            vs = TextInput(title=attr["title"], help=attr["help"])
        else:
            raise NotImplementedError()

        # TODO: This method uses LegacyUserAttribute(). Use another class for
        # this kind of attribute
        declare_user_attribute(
            attr["name"],
            vs,
            user_editable=attr["user_editable"],
            show_in_table=attr.get("show_in_table", False),
            topic=attr.get("topic", "personal"),
            add_custom_macro=attr.get("add_custom_macro", False),
            from_config=True,
        )

    cmk.gui.plugins.userdb.ldap_connector.register_user_attribute_sync_plugins()


def _clear_config_based_user_attributes() -> None:
    for _name, attr in get_user_attributes():
        if attr.from_config():
            user_attribute_registry.unregister(attr.name())


# Make the config module initialize the user attributes after loading the config
register_post_config_load_hook(update_config_based_user_attributes)

# .
#   .-Hooks----------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_credentials(username: UserId, password: str) -> Union[UserId, Literal[False]]:
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
                _("The username returned by the %s " "connector is not of type string (%r).")
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
        create_non_existing_user(connection_id, user_id)

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


def hook_save(users: Users) -> None:
    """Hook function can be registered here to be executed during saving of the
    new user construct"""
    for connection_id, connection in active_connections():
        try:
            connection.save_users(users)
        except Exception as e:
            if active_config.debug:
                raise
            show_exception(connection_id, _("Error during saving"), e)


def general_userdb_job() -> None:
    """This function registers general stuff, which is independet of the single
    connectors to each page load. It is exectued AFTER all other connections jobs."""

    hooks.call("userdb-job")

    # Create initial auth.serials file, same issue as auth.php above
    serials_file = "%s/auth.serials" % os.path.dirname(cmk.utils.paths.htpasswd_file)
    if not os.path.exists(serials_file) or os.path.getsize(serials_file) == 0:
        rewrite_users()


def execute_userdb_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    if not userdb_sync_job_enabled():
        return

    job = UserSyncBackgroundJob()
    if job.is_active():
        logger.debug("Another synchronization job is already running: Skipping this sync")
        return

    job.set_function(
        job.do_sync,
        add_to_changelog=False,
        enforce_sync=False,
        load_users_func=load_users,
        save_users_func=save_users,
    )
    job.start()


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
        job.set_function(
            job.do_sync,
            add_to_changelog=False,
            enforce_sync=True,
            load_users_func=load_users,
            save_users_func=save_users,
        )
        try:
            job.start()
        except background_job.BackgroundJobAlreadyRunning as e:
            raise MKUserError(None, _("Another user synchronization is already running: %s") % e)
        response.set_data("OK Started synchronization\n")
    except Exception as e:
        logger.exception("error synchronizing user DB")
        if active_config.debug:
            raise
        response.set_data("ERROR %s\n" % e)


@gui_background_job.job_registry.register
class UserSyncBackgroundJob(gui_background_job.GUIBackgroundJob):
    job_prefix = "user_sync"

    @classmethod
    def gui_title(cls) -> str:
        return _("User synchronization")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            title=self.gui_title(),
            stoppable=False,
        )

    def _back_url(self) -> str:
        return makeuri_contextless(request, [("mode", "users")], filename="wato.py")

    def do_sync(
        self,
        job_interface: background_job.BackgroundProcessInterface,
        add_to_changelog: bool,
        enforce_sync: bool,
        load_users_func: Callable,
        save_users_func: Callable,
    ) -> None:
        job_interface.send_progress_update(_("Synchronization started..."))
        if self._execute_sync_action(
            job_interface, add_to_changelog, enforce_sync, load_users_func, save_users_func
        ):
            job_interface.send_result_message(_("The user synchronization completed successfully."))
        else:
            job_interface.send_exception(_("The user synchronization failed."))

    def _execute_sync_action(
        self,
        job_interface: background_job.BackgroundProcessInterface,
        add_to_changelog: bool,
        enforce_sync: bool,
        load_users_func: Callable,
        save_users_func: Callable,
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
                    only_username=False,
                    load_users_func=load_users,
                    save_users_func=save_users,
                )
                job_interface.send_progress_update(
                    _("[%s] Finished sync for connection") % connection_id
                )
            except Exception as e:
                job_interface.send_exception(_("[%s] Exception: %s") % (connection_id, e))
                logger.error(
                    "Exception (%s, userdb_job): %s", connection_id, traceback.format_exc()
                )

        job_interface.send_progress_update(_("Finalizing synchronization"))
        general_userdb_job()
        return True


def execute_user_profile_cleanup_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    job = UserProfileCleanupBackgroundJob()
    if job.is_active():
        logger.debug("Job is already running: Skipping this time")
        return

    interval = 3600
    with suppress(FileNotFoundError):
        if time.time() - UserProfileCleanupBackgroundJob.last_run_path().stat().st_mtime < interval:
            logger.debug("Job was already executed within last %d seconds", interval)
            return

    job.set_function(job.do_execute)
    job.start()


@gui_background_job.job_registry.register
class UserProfileCleanupBackgroundJob(gui_background_job.GUIBackgroundJob):
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
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def do_execute(self, job_interface: background_job.BackgroundProcessInterface) -> None:
        try:
            self._do_cleanup()
            job_interface.send_result_message(_("Job finished"))
        finally:
            UserProfileCleanupBackgroundJob.last_run_path().touch(exist_ok=True)

    def _do_cleanup(self) -> None:
        """Cleanup abandoned profile directories

        The cleanup is done like this:

        - Load the userdb to get the list of locally existing users
        - Iterate over all use profile directories and find all directories that don't belong to an
          existing user
        - For each of these directories find the most recent written file
        - In case the most recent written file is older than 30 days delete the profile directory
        - Create an audit log entry for each removed directory
        """
        users = set(load_users().keys())
        if not users:
            self._logger.warning("Found no users. Be careful and not cleaning up anything.")
            return

        profile_base_dir = cmk.utils.paths.profile_dir
        # Some files like ldap_*_sync_time.mk can be placed in
        # ~/var/check_mk/web, causing error entries in web.log while trying to
        # delete a dir
        profiles = set(
            profile_dir.name for profile_dir in profile_base_dir.iterdir() if profile_dir.is_dir()
        )

        abandoned_profiles = sorted(profiles - users)
        if not abandoned_profiles:
            self._logger.debug("Found no abandoned profile.")
            return

        self._logger.info("Found %d abandoned profiles", len(abandoned_profiles))
        self._logger.debug("Profiles: %s", ", ".join(abandoned_profiles))

        for profile_name in abandoned_profiles:
            profile_dir = profile_base_dir / profile_name
            last_mtime = max((p.stat().st_mtime for p in profile_dir.glob("*.mk")), default=0.0)
            if time.time() - last_mtime > 2592000:
                try:
                    self._logger.info("Removing abandoned profile directory: %s", profile_name)
                    shutil.rmtree(profile_dir)
                except OSError:
                    self._logger.debug("Could not delete %s", profile_dir, exc_info=True)
