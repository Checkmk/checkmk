#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
import copy
import itertools
import os
import traceback
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast, Literal, TypeVar

from cmk.ccc.store import (
    acquire_lock,
    load_from_mk_file,
    load_text_from_file,
    mkdir,
    release_lock,
    save_text_to_file,
    save_to_mk_file,
)

import cmk.utils.paths
from cmk.utils.local_secrets import AutomationUserSecret
from cmk.utils.paths import htpasswd_file, var_dir
from cmk.utils.user import UserId

import cmk.gui.pages
from cmk.gui import hooks, utils
from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser, save_user_file
from cmk.gui.type_defs import (
    SessionInfo,
    TwoFactorCredentials,
    UserContactDetails,
    UserDetails,
    Users,
    UserSpec,
)
from cmk.gui.utils.htpasswd import Htpasswd
from cmk.gui.utils.roles import AutomationUserFile, roles_of_user

from cmk.crypto import password_hashing
from cmk.crypto.password import Password

from ._connections import active_connections, get_connection
from ._connector import UserConnector
from ._user_attribute import get_user_attributes
from ._user_spec import add_internal_attributes

T = TypeVar("T")

_ContactgroupName = str


def load_custom_attr(
    *,
    user_id: UserId,
    key: str,
    parser: Callable[[str], T],
    lock: bool = False,
) -> T | None:
    """This function can be called thousands of times during a single request
    The load_text_from_file adds additional overhead(cpu load) that is not required
    for simple read-only operations.
    In addition to providing the data, the task of this function is to check whether
    load_text_from_file can be replaced by a simpler operation
    """
    attr_path = custom_attr_path(user_id, key)
    if not os.path.exists(attr_path):
        return None

    if lock:
        result = load_text_from_file(Path(attr_path), lock=lock)
    else:
        # Simpler operation if no lock is required. Does NOT check file permissions
        # These are only considered critical in case of pickled data
        # Files in the ~/var/check_mk/web/{username} do and WILL never contain pickled data
        try:
            with open(str(attr_path)) as file_object:
                result = file_object.read()
        except (FileNotFoundError, OSError):
            return None
    return None if result == "" else parser(result.strip())


def custom_attr_path(userid: UserId, key: str) -> str:
    return var_dir + "/web/" + userid + "/" + key + ".mk"


def save_custom_attr(userid: UserId, key: str, val: Any) -> None:
    path = custom_attr_path(userid, key)
    mkdir(os.path.dirname(path))
    save_text_to_file(path, "%s\n" % val)


def save_two_factor_credentials(user_id: UserId, credentials: TwoFactorCredentials) -> None:
    save_custom_attr(user_id, "two_factor_credentials", repr(credentials))


def rewrite_users(now: datetime) -> None:
    save_users(load_users(lock=True), now)


def _root_dir() -> str:
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def _multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


def get_authserials_lines() -> list[str]:
    authserials_path = Path(cmk.utils.paths.htpasswd_file).with_name("auth.serials")
    if not authserials_path.exists():
        return []
    with authserials_path.open(encoding="utf-8") as f:
        return f.readlines()


def load_users_uncached(lock: bool = False) -> Users:
    return _load_users(lock)


@request_memoize()
def load_users(lock: bool = False) -> Users:
    return _load_users(lock)


def _load_users(lock: bool = False) -> Users:
    if lock:
        # Note: the lock will be released on next save_users() call or at
        #       end of page request automatically.
        acquire_lock(_contacts_filepath())

    # First load monitoring contacts from Checkmk's world. If this is
    # the first time, then the file will be empty, which is no problem.
    # Execfile will the simply leave contacts = {} unchanged.
    # ? exact type of keys and items returned from load_mk_file seems to be unclear
    contacts = load_contacts()

    # Now load information about users from the GUI config world
    # ? can users dict be modified in load_mk_file function call and the type of keys str be changed?
    users = load_multisite_users()

    # Merge them together. Monitoring users not known to Multisite
    # will be added later as normal users.
    result: Users = _merge_users_and_contacts(users, contacts)

    # This loop is only necessary if someone has edited
    # contacts.mk manually. But we want to support that as
    # far as possible.
    for uid, contact in contacts.items():
        if (uid := UserId(uid)) not in result:
            # making the use of cast since we are handling a legacy support case
            user_profile: UserSpec = cast(UserSpec, contact)
            result[uid] = user_profile
            result[uid]["roles"] = ["user"]
            result[uid]["locked"] = True
            result[uid]["password"] = password_hashing.PasswordHash("")

    # Passwords are read directly from the apache htpasswd-file.
    # That way heroes of the command line will still be able to
    # change passwords with htpasswd. Users *only* appearing
    # in htpasswd will also be loaded and assigned to the role
    # they are getting according to the multisite old-style
    # configuration variables.

    result = _add_passwords(result)

    # Now read the serials, only process for existing users

    result = _add_serials(result)

    attributes: list[
        tuple[
            # This verbose type is required for accessing `result[uid][attr]` below
            Literal[
                "num_failed_logins",
                "last_pw_change",
                "enforce_pw_change",
                "idle_timeout",
                "session_info",
                "start_url",
                "ui_theme",
                "two_factor_credentials",
                "ui_sidebar_position",
                "ui_saas_onboarding_button_toggle",
                "last_login",
            ],
            Callable,
        ]
    ] = [
        ("num_failed_logins", utils.saveint),
        ("last_pw_change", utils.saveint),
        ("enforce_pw_change", lambda x: bool(utils.saveint(x))),
        ("idle_timeout", convert_idle_timeout),
        ("session_info", convert_session_info),
        ("start_url", _convert_start_url),
        ("ui_theme", lambda x: x),
        ("two_factor_credentials", ast.literal_eval),
        ("ui_sidebar_position", lambda x: None if x == "None" else x),
        ("ui_saas_onboarding_button_toggle", lambda x: None if x == "None" else x),
        ("last_login", ast.literal_eval),
    ]

    # Now read the user specific files
    for user_dir in os.listdir(cmk.utils.paths.profile_dir):
        if user_dir[0] == ".":
            continue

        uid = UserId(user_dir)
        if uid not in result:
            continue

        # read special values from own files
        for attr, conv_func in attributes:
            val = load_custom_attr(user_id=uid, key=attr, parser=conv_func)
            if val is not None:
                result[uid][attr] = val

        result[uid]["store_automation_secret"] = AutomationUserSecret(uid).exists()
        # The AutomationUserFile was added with 2.4. Previously the info to decide if a user is an
        # automation user was the automation secret. Instead of creating an update action let's
        # check both.
        result[uid]["is_automation_user"] = (
            AutomationUserSecret(uid).exists() or AutomationUserFile(uid).load()
        )

    return result


def _merge_users_and_contacts(
    users: dict[str, UserDetails], contacts: dict[str, UserContactDetails]
) -> Users:
    result: Users = {}
    for uid, user in users.items():
        profile: dict[str, object] = {}
        if (contact := contacts.get(uid)) is not None:
            profile.update(contact)

        profile.update(user)

        # Convert non unicode mail addresses
        if "email" in profile:
            # TODO: according to UserDetails & UserContactDetails, email can only come from
            #  UserContactDetails. We keep this just in case UserDetails is incomplete and perform
            #  the cast to str. Once verified, the condition can be switched to
            #  `if "email" in contact`.
            email = cast(str, profile["email"])
            profile["email"] = email

        # see TODO in UserSpec why the cast is currently necessary
        result[UserId(uid)] = cast(UserSpec, profile)
    return result


def _add_passwords(users: Users) -> Users:
    htpwd_entries = Htpasswd(Path(cmk.utils.paths.htpasswd_file)).load(allow_missing_file=True)
    for uid, password in htpwd_entries.items():
        if password.startswith("!"):
            locked = True
            password = password_hashing.PasswordHash(password[1:])
        else:
            locked = False

        if uid in users:
            users[uid]["password"] = password
            users[uid]["locked"] = locked
        else:
            # Create entry if this is an admin user
            new_user = UserSpec(
                roles=roles_of_user(uid),
                password=password,
                locked=False,
                connector="htpasswd",
            )

            add_internal_attributes(new_user)

            users[uid] = new_user
        # Make sure that the user has an alias
        users[uid].setdefault("alias", uid)
    return users


def _add_serials(users: Users) -> Users:
    serials_file = Path(cmk.utils.paths.htpasswd_file).with_name("auth.serials")
    try:
        for line in serials_file.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                user_id, serial = line.split(":")[:2]
                if (user_id := UserId(user_id)) in users:
                    users[user_id]["serial"] = utils.saveint(serial)
    except OSError:  # file not found
        pass

    return users


def remove_custom_attr(userid: UserId, key: str) -> None:
    try:
        os.unlink(custom_attr_path(userid, key))
    except OSError:
        pass  # Ignore non existing files


def get_online_user_ids(now: datetime) -> list[UserId]:
    online_threshold = now.timestamp() - active_config.user_online_maxage
    return [
        user_id
        for user_id, user in load_users(lock=False).items()
        if get_last_activity(user) >= online_threshold
    ]


def get_last_activity(user: UserSpec) -> int:
    return max([s.last_activity for s in user.get("session_info", {}).values()] + [0])


def get_last_seen(user: UserSpec) -> tuple[int, str]:
    """
    The function returns information about the last activity of a user.
    For those users who log in to the website, the information is obtained
    from their active sessions. In the case of REST API authentication,
    the last_login custom attribute is taken into account.

    As a user can authenticate using both methods, this function obtains
    information from both sources and returns the most recent one.
    """

    timestamp = 0
    auth_type = ""

    for s in user.get("session_info", {}).values():
        if s.last_activity > timestamp:
            timestamp = s.last_activity
            auth_type = "" if s.auth_type is None else s.auth_type

    if ((last_login_info := user.get("last_login")) is not None) and last_login_info[
        "timestamp"
    ] > timestamp:
        timestamp = last_login_info["timestamp"]
        auth_type = last_login_info["auth_type"]

    return timestamp, auth_type


def split_dict(d: Mapping[str, Any], keylist: list[str], positive: bool) -> dict[str, Any]:
    return {k: v for k, v in d.items() if (k in keylist) == positive}


def save_users(profiles: Users, now: datetime) -> None:
    write_contacts_and_users_file(profiles)

    # Execute user connector save hooks
    hook_save(profiles)

    updated_profiles = _add_custom_macro_attributes(profiles)

    _save_auth_serials(updated_profiles)
    _save_user_profiles(updated_profiles, now)
    _cleanup_old_user_profiles(updated_profiles)

    # Release the lock to make other threads access possible again asap
    # This lock is set by load_users() only in the case something is expected
    # to be written (like during user syncs, wato, ...)
    release_users_lock()

    # Invalidate the users memoized data
    # The magic attribute has been added by the lru_cache decorator.
    load_users.cache_clear()  # type: ignore[attr-defined]

    # Call the users_saved hook
    hooks.call("users-saved", updated_profiles)


# TODO: Isn't this needed only while generating the contacts.mk?
#       Check this and move it to the right place
def _add_custom_macro_attributes(profiles: Users) -> Users:
    updated_profiles = copy.deepcopy(profiles)

    # Add custom macros
    core_custom_macros = {
        name
        for name, attr in get_user_attributes()
        if attr.add_custom_macro()  #
    }
    for user in updated_profiles.keys():
        for macro in core_custom_macros:
            if macro in updated_profiles[user]:
                # UserSpec is now a TypedDict, unfortunately not complete yet,
                # thanks to such constructs.
                updated_profiles[user]["_" + macro] = updated_profiles[user][macro]  # type: ignore[literal-required]

    return updated_profiles


# Write user specific files
def _save_user_profiles(
    updated_profiles: Users,
    now: datetime,
) -> None:
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()

    for user_id, user in updated_profiles.items():
        mkdir(cmk.utils.paths.profile_dir / user_id)

        # authentication secret for local processes
        secret = AutomationUserSecret(user_id)
        if user.get("store_automation_secret", False) and "automation_secret" in user:
            secret.save(user["automation_secret"])
        elif not user.get("store_automation_secret", False):
            secret.delete()

        AutomationUserFile(user_id).save(user.get("is_automation_user", False))

        # Write out user attributes which are written to dedicated files in the user
        # profile directory. The primary reason to have separate files, is to reduce
        # the amount of data to be loaded during regular page processing
        save_custom_attr(user_id, "serial", str(user.get("serial", 0)))
        save_custom_attr(user_id, "num_failed_logins", str(user.get("num_failed_logins", 0)))
        save_custom_attr(
            user_id, "enforce_pw_change", str(int(bool(user.get("enforce_pw_change"))))
        )
        save_custom_attr(
            user_id, "last_pw_change", str(user.get("last_pw_change", int(now.timestamp())))
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

        if "ui_saas_onboarding_button_toggle" in user:
            save_custom_attr(
                user_id,
                "ui_saas_onboarding_button_toggle",
                user["ui_saas_onboarding_button_toggle"],
            )
        else:
            remove_custom_attr(user_id, "ui_saas_onboarding_button_toggle")

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
    for user_dir in os.listdir(directory):
        if user_dir in [".", ".."] or user_dir in updated_profiles:
            continue

        entry = directory + "/" + user_dir
        if not os.path.isdir(entry):
            continue

        for to_delete in profile_files_to_delete:
            if os.path.exists(entry + "/" + to_delete):
                os.unlink(entry + "/" + to_delete)


def write_contacts_and_users_file(
    profiles: Users,
    custom_default_config_dir: str | None = None,
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

    non_contact_attributes_cache: dict[str | None, Sequence[str]] = {}
    multisite_attributes_cache: dict[str | None, Sequence[str]] = {}
    for user_settings in updated_profiles.values():
        connector = user_settings.get("connector")
        if connector not in non_contact_attributes_cache:
            non_contact_attributes_cache[connector] = non_contact_attributes(connector)
        if connector not in multisite_attributes_cache:
            multisite_attributes_cache[connector] = multisite_attributes(connector)

    # Remove multisite keys in contacts.
    # TODO: Clean this up. Just improved the performance, but still have no idea what its actually doing...
    contacts: dict[str, Any] = dict(
        e
        for e in [
            (
                id,
                split_dict(
                    user,
                    list(
                        itertools.chain(
                            non_contact_keys,
                            non_contact_attributes_cache[user.get("connector")],
                        )
                    ),
                    False,
                ),
            )
            for (id, user) in updated_profiles.items()
        ]
    )

    # Only allow explicitely defined attributes to be written to multisite config
    users: dict[str, Any] = {}
    for uid, profile in updated_profiles.items():
        users[uid] = {
            p: val
            for p, val in profile.items()
            if p in multisite_keys or p in multisite_attributes_cache[profile.get("connector")]
        }

    # Checkmk's monitoring contacts
    save_to_mk_file(
        "{}/{}".format(check_mk_config_dir, "contacts.mk"),
        "contacts",
        contacts,
        pprint_value=active_config.wato_pprint_config,
    )

    # GUI specific user configuration
    save_to_mk_file(
        "{}/{}".format(multisite_config_dir, "users.mk"),
        "multisite_users",
        users,
        pprint_value=active_config.wato_pprint_config,
    )


def non_contact_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific non contact attributes"""
    return _get_attributes(connection_id, lambda c: c.non_contact_attributes())


def multisite_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific multisite attributes"""
    return _get_attributes(connection_id, lambda c: c.multisite_attributes())


def _get_attributes(
    connection_id: str | None, selector: Callable[[UserConnector], Sequence[str]]
) -> Sequence[str]:
    connection = get_connection(connection_id)
    return selector(connection) if connection else []


def _non_contact_keys() -> list[str]:
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


def _multisite_keys() -> list[str]:
    """User attributes to put into multisite configuration"""
    multisite_variables = [
        var
        for var in _get_multisite_custom_variable_names()
        if var
        not in ("start_url", "ui_theme", "ui_sidebar_position", "ui_saas_onboarding_button_toggle")
    ]
    return [
        "roles",
        "locked",
        "alias",
        "language",
        "connector",
    ] + multisite_variables


def _get_multisite_custom_variable_names() -> list[str]:
    return [name for name, attr in get_user_attributes() if attr.domain() == "multisite"]  #


def _save_auth_serials(updated_profiles: Users) -> None:
    """Write out the users serials"""
    # Write out the users serials
    serials = ""
    for user_id, user in updated_profiles.items():
        serials += "%s:%d\n" % (user_id, user.get("serial", 0))
    save_text_to_file("%s/auth.serials" % os.path.dirname(cmk.utils.paths.htpasswd_file), serials)


def create_cmk_automation_user(
    now: datetime, name: str, alias: str, role: str, store_secret: bool
) -> None:
    secret = Password.random(24)
    users = load_users(lock=True)
    users[UserId(name)] = {
        "alias": alias,
        "contactgroups": [],
        "automation_secret": secret.raw,
        "store_automation_secret": store_secret,
        "is_automation_user": True,
        "password": password_hashing.hash_password(secret),
        "roles": [role],
        "locked": False,
        "serial": 0,
        "email": "",
        "pager": "",
        "notifications_enabled": False,
        "language": "en",
        "connector": "htpasswd",
    }
    save_users(users, now)


def _save_cached_profile(
    user_id: UserId, user: UserSpec, multisite_keys: list[str], non_contact_keys: list[str]
) -> None:
    # Only save contact AND multisite attributes to the profile. Not the
    # infos that are stored in the custom attribute files.
    cache = UserSpec()
    for key in user.keys():
        if key in ("automation_secret",):
            # Stripping away sensitive information
            continue
        if key in multisite_keys or key not in non_contact_keys:
            # UserSpec is now a TypedDict, unfortunately not complete yet, thanks to such constructs.
            cache[key] = user[key]  # type: ignore[literal-required]

    save_user_file("cached_profile", cache, user_id=user_id)


def load_cached_profile(user_id: UserId) -> UserSpec | None:
    return LoggedInUser(user_id).load_file("cached_profile", None)


def contactgroups_of_user(user_id: UserId) -> list[_ContactgroupName]:
    return load_user(user_id).get("contactgroups", [])


def convert_idle_timeout(value: str) -> int | bool | None:
    try:
        return False if value == "False" else int(value)  # disabled or set
    except ValueError:
        return None  # Invalid value -> use global setting


def load_contacts() -> dict[str, UserContactDetails]:
    return load_from_mk_file(_contacts_filepath(), "contacts", {})


def _contacts_filepath() -> str:
    return _root_dir() + "contacts.mk"


def load_multisite_users() -> dict[str, UserDetails]:
    return load_from_mk_file(_multisite_dir() + "users.mk", "multisite_users", {})


def _convert_start_url(value: str) -> str:
    # TODO in Version 2.0.0 and 2.0.0p1 the value was written without repr(),
    # remove the if condition one day
    if value.startswith("'") and value.endswith("'"):
        return ast.literal_eval(value)
    return value


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


def general_userdb_job(now: datetime) -> None:
    """This function registers general stuff, which is independet of the single
    connectors to each page load. It is exectued AFTER all other connections jobs."""

    hooks.call("userdb-job")

    # Create initial auth.serials file, same issue as auth.php above
    serials_file = "%s/auth.serials" % os.path.dirname(htpasswd_file)
    if not os.path.exists(serials_file) or os.path.getsize(serials_file) == 0:
        rewrite_users(now)


def convert_session_info(value: str) -> dict[str, SessionInfo]:
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


def release_users_lock() -> None:
    release_lock(cmk.utils.paths.check_mk_config_dir + "/wato/contacts.mk")
