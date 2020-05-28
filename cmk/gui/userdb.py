#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Rework connection management and multiplexing

from typing import cast, Union, Any, Callable, Dict, List, Optional, Tuple
import time
import os
import traceback
import copy
from pathlib import Path

import six

import cmk.utils.version as cmk_version
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.type_defs import UserId, ContactgroupName
from cmk.utils.encoding import ensure_text

import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.hooks as hooks
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.valuespec import ValueSpec
from cmk.gui.exceptions import MKUserError, MKInternalError
from cmk.gui.log import logger
from cmk.gui.valuespec import (
    TextAscii,
    DropdownChoice,
)
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import g, html
import cmk.gui.plugins.userdb
from cmk.gui.plugins.userdb.htpasswd import Htpasswd
from cmk.gui.plugins.userdb.ldap_connector import MKLDAPException

# TODO: Cleanup references and point directly to cmk.gui.plugins.userdb.utils
from cmk.gui.plugins.userdb.utils import (  # noqa: F401 # pylint: disable=unused-import
    user_attribute_registry,  #
    get_user_attributes,  #
    UserConnector,  #
    user_connector_registry,  #
    user_sync_config,  #
    load_roles,  #
    Roles,  #
    RoleSpec,  #
    UserSpec,  #
    new_user_template,  #
    load_cached_profile,  #
    get_connection,  #
    active_connections,  #
    connection_choices,  #
    cleanup_connection_id,  #
    release_users_lock,  #
)

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False  # type: Union[bool, None, str]

auth_logger = logger.getChild("auth")

Users = Dict[UserId, UserSpec]  # TODO: Improve this type


# Load all userdb plugins
def load_plugins(force):
    # type: (bool) -> None
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    utils.load_web_plugins("userdb", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


# The saved configuration for user connections is a bit inconsistent, let's fix
# this here once and for all.
def _fix_user_connections():
    # type: () -> None
    for cfg in config.user_connections:
        # Although our current configuration always seems to have a 'disabled'
        # entry, this might not have always been the case.
        cfg.setdefault('disabled', False)
        # Only migrated configurations have a 'type' entry, all others are
        # implictly LDAP connections.
        cfg.setdefault('type', 'ldap')


config.register_post_config_load_hook(_fix_user_connections)


# When at least one LDAP connection is defined and active a sync is possible
def sync_possible():
    # type: () -> bool
    return any(connection.type() == "ldap" for _connection_id, connection in active_connections())


def locked_attributes(connection_id):
    # type: (Optional[str]) -> List[str]
    """Returns a list of connection specific locked attributes"""
    return _get_attributes(connection_id, lambda c: c.locked_attributes())


def multisite_attributes(connection_id):
    # type: (Optional[str]) -> List[str]
    """Returns a list of connection specific multisite attributes"""
    return _get_attributes(connection_id, lambda c: c.multisite_attributes())


def non_contact_attributes(connection_id):
    # type: (Optional[str]) -> List[str]
    """Returns a list of connection specific non contact attributes"""
    return _get_attributes(connection_id, lambda c: c.non_contact_attributes())


def _get_attributes(connection_id, selector):
    # type: (Optional[str], Callable[[UserConnector], List[str]]) -> List[str]
    connection = get_connection(connection_id)
    return selector(connection) if connection else []


def create_non_existing_user(connection_id, username):
    # type: (str, UserId) -> None
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

        connection.do_sync(add_to_changelog=False,
                           only_username=username,
                           load_users_func=load_users,
                           save_users_func=save_users)
    except MKLDAPException as e:
        show_exception(connection_id, _("Error during sync"), e, debug=config.debug)
    except Exception as e:
        show_exception(connection_id, _("Error during sync"), e)


def is_customer_user_allowed_to_login(user_id):
    # type: (UserId) -> bool
    if not cmk_version.is_managed_edition():
        return True

    user = config.LoggedInUser(user_id)

    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
    if managed.is_global(user.customer_id):
        return True

    return managed.is_current_customer(user.customer_id)


# This function is called very often during regular page loads so it has to be efficient
# even when having a lot of users.
#
# When using the multisite authentication with just by WATO created users it would be
# easy, but we also need to deal with users which are only existant in the htpasswd
# file and don't have a profile directory yet.
def user_exists(username):
    # type: (UserId) -> bool
    if _user_exists_according_to_profile(username):
        return True

    return Htpasswd(Path(cmk.utils.paths.htpasswd_file)).exists(username)


def _user_exists_according_to_profile(username):
    # type: (UserId) -> bool
    base_path = config.config_dir + "/" + six.ensure_str(username) + "/"
    return os.path.exists(base_path + "transids.mk") \
            or os.path.exists(base_path + "serial.mk")


def login_timed_out(username, last_activity):
    # type: (UserId, float) -> bool
    idle_timeout = load_custom_attr(username, "idle_timeout", _convert_idle_timeout, None)
    if idle_timeout is None:
        idle_timeout = config.user_idle_timeout

    if idle_timeout in [None, False]:
        return False  # no timeout activated at all

    timed_out = (time.time() - last_activity) > idle_timeout

    if timed_out:
        auth_logger.debug("%s login timed out (Inactive for %d seconds)" %
                          (username, time.time() - last_activity))

    return timed_out


def update_user_access_time(username):
    # type: (UserId) -> None
    if not config.save_user_access_times:
        return
    save_custom_attr(username, 'last_seen', repr(time.time()))


def on_succeeded_login(username):
    # type: (UserId) -> None
    num_failed_logins = load_custom_attr(username, 'num_failed_logins', utils.saveint)
    if num_failed_logins is not None and num_failed_logins != 0:
        save_custom_attr(username, 'num_failed_logins', '0')

    update_user_access_time(username)


# userdb.need_to_change_pw returns either False or the reason description why the
# password needs to be changed
def need_to_change_pw(username):
    # type: (UserId) -> Union[bool, str]
    if not _is_local_user(username):
        return False

    if load_custom_attr(username, 'enforce_pw_change', utils.saveint) == 1:
        return 'enforced'

    last_pw_change = load_custom_attr(username, 'last_pw_change', utils.saveint)
    max_pw_age = config.password_policy.get('max_age')
    if max_pw_age:
        if not last_pw_change:
            # The age of the password is unknown. Assume the user has just set
            # the password to have the first access after enabling password aging
            # as starting point for the password period. This bewares all users
            # from needing to set a new password after enabling aging.
            save_custom_attr(username, 'last_pw_change', str(int(time.time())))
            return False
        if time.time() - last_pw_change > max_pw_age:
            return 'expired'
    return False


def _is_local_user(user_id):
    # type: (UserId) -> bool
    user = load_cached_profile(user_id)
    if user is None:
        # No cached profile present. Load all users to get the users data
        user = load_users(lock=False).get(user_id, {})
        assert user is not None  # help mypy

    return user.get('connector', 'htpasswd') == 'htpasswd'


def _user_locked(user_id):
    # type: (UserId) -> bool
    user = load_cached_profile(user_id)
    if user is None:
        # No cached profile present. Load all users to get the users data
        user = load_users(lock=False).get(user_id, {})
        assert user is not None  # help mypy

    return user.get('locked', False)


def on_failed_login(username):
    # type: (UserId) -> None
    users = load_users(lock=True)
    if username in users:
        if "num_failed_logins" in users[username]:
            users[username]["num_failed_logins"] += 1
        else:
            users[username]["num_failed_logins"] = 1

        if config.lock_on_logon_failures:
            if users[username]["num_failed_logins"] >= config.lock_on_logon_failures:
                users[username]["locked"] = True

        save_users(users)


def _root_dir():
    # type: () -> str
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def _multisite_dir():
    # type: () -> str
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# TODO: Change to factory
class UserSelection(DropdownChoice):
    """Dropdown for choosing a multisite user"""
    def __init__(self, **kwargs):
        only_contacts = kwargs.pop("only_contacts", False)
        only_automation = kwargs.pop("only_automation", False)
        kwargs["choices"] = self._generate_wato_users_elements_function(
            kwargs.get("none"), only_contacts=only_contacts, only_automation=only_automation)
        kwargs["invalid_choice"] = "complain"  # handle vanished users correctly!
        DropdownChoice.__init__(self, **kwargs)

    def _generate_wato_users_elements_function(self,
                                               none_value,
                                               only_contacts=False,
                                               only_automation=False):
        def get_wato_users(nv):
            users = load_users()
            elements = sorted([(name, "%s - %s" % (name, us.get("alias", name)))
                               for (name, us) in users.items()
                               if (not only_contacts or us.get("contactgroups")) and
                               (not only_automation or us.get("automation_secret"))
                              ])  # type: List[Tuple[Optional[UserId], str]]
            if nv is not None:
                empty = [(None, none_value)]  # type: List[Tuple[Optional[UserId], str]]
                elements = empty + elements
            return elements

        return lambda: get_wato_users(none_value)

    def value_to_text(self, value):
        text = DropdownChoice.value_to_text(self, value)
        return text.split(" - ")[-1]


#.
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


def is_valid_user_session(username, session_id):
    # type: (UserId, str) -> bool
    if config.single_user_session is None:
        return True  # No login session limitation enabled, no validation

    session_info = load_session_info(username)
    if session_info is None:
        return False  # no session active
    active_session_id, last_activity = session_info

    if session_id == active_session_id:
        return True  # Current session. Fine.

    auth_logger.debug("%s session_id not valid (timed out?) (Inactive for %d seconds)" %
                      (username, time.time() - last_activity))

    return False


def ensure_user_can_init_session(username):
    # type: (UserId) -> bool
    if config.single_user_session is None:
        return True  # No login session limitation enabled, no validation

    session_timeout = config.single_user_session

    session_info = load_session_info(username)
    if session_info is None:
        return True  # No session active

    last_activity = session_info[1]
    if (time.time() - last_activity) > session_timeout:
        return True  # Former active session timed out

    auth_logger.debug("%s another session is active (inactive for: %d seconds)" %
                      (username, time.time() - last_activity))

    raise MKUserError(None, _("Another session is active"))


def initialize_session(username):
    # type: (UserId) -> str
    """Creates a new user login session (if single user session mode is enabled) and
    returns the session_id of the new session."""
    if not config.single_user_session:
        return ""

    session_id = create_session_id()
    save_session_info(username, session_id)
    return session_id


def create_session_id():
    # type: () -> str
    """Creates a random session id for the user and returns it."""
    return utils.gen_id()


def refresh_session(username):
    # type: (UserId) -> None
    """Updates the current session of the user and returns the session_id or only
    returns an empty string when single user session mode is not enabled."""
    if not config.single_user_session:
        return  # No session handling at all

    session_info = load_session_info(username)
    if session_info is None:
        return  # Don't refresh. Session is not valid anymore

    session_id = session_info[0]
    save_session_info(username, session_id)


def invalidate_session(username):
    # type: (UserId) -> None
    remove_custom_attr(username, "session_info")


# Saves the current session_id and the current time (last activity)
def save_session_info(username, session_id):
    # type: (UserId, str) -> None
    save_custom_attr(username, "session_info", "%s|%s" % (session_id, int(time.time())))


# Returns either None (when no session_id available) or a two element
# tuple where the first element is the sesssion_id and the second the
# timestamp of the last activity.
def load_session_info(username):
    # type: (UserId) -> Optional[Tuple[str, int]]
    return load_custom_attr(username, "session_info", _convert_session_info)


def _convert_session_info(value):
    # type: (str) -> Optional[Tuple[str, int]]
    if value == "":
        return None

    session_id, last_activity = value.split("|", 1)
    return session_id, int(last_activity)


#.
#   .-Users----------------------------------------------------------------.
#   |                       _   _                                          |
#   |                      | | | |___  ___ _ __ ___                        |
#   |                      | | | / __|/ _ \ '__/ __|                       |
#   |                      | |_| \__ \  __/ |  \__ \                       |
#   |                       \___/|___/\___|_|  |___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class GenericUserAttribute(cmk.gui.plugins.userdb.UserAttribute):
    def __init__(self, user_editable, show_in_table, add_custom_macro, domain, permission,
                 from_config):
        # type: (bool, bool, bool, str, Optional[str], bool) -> None
        super(GenericUserAttribute, self).__init__()
        self._user_editable = user_editable
        self._show_in_table = show_in_table
        self._add_custom_macro = add_custom_macro
        self._domain = domain
        self._permission = permission
        self._from_config = from_config

    def from_config(self):
        # type: () -> bool
        return self._from_config

    def user_editable(self):
        # type: () -> bool
        return self._user_editable

    def permission(self):
        # type: () -> Optional[str]
        return self._permission

    def show_in_table(self):
        # type: () -> bool
        return self._show_in_table

    def add_custom_macro(self):
        # type: () -> bool
        return self._add_custom_macro

    def domain(self):
        # type: () -> str
        return self._domain


# TODO: Legacy plugin API. Converts to new internal structure. Drop this with 1.6 or later.
def declare_user_attribute(name,
                           vs,
                           user_editable=True,
                           permission=None,
                           show_in_table=False,
                           topic=None,
                           add_custom_macro=False,
                           domain="multisite",
                           from_config=False):
    # type: (str, ValueSpec, bool, Optional[str], bool, str, bool, str, bool) -> None

    # FIXME: The classmethods "name" and "topic" shadow the arguments from the function scope.
    # Any use off "name" and "topic" inside the class will result in a NameError.
    attr_name = name
    attr_topic = topic

    @user_attribute_registry.register
    class LegacyUserAttribute(GenericUserAttribute):
        _name = attr_name
        _valuespec = vs
        _topic = attr_topic if attr_topic else 'personal'

        @classmethod
        def name(cls):
            # type: () -> str
            return cls._name

        @classmethod
        def valuespec(cls):
            # type: () -> ValueSpec
            return cls._valuespec

        @classmethod
        def topic(cls):
            # type: () -> str
            return cls._topic

        def __init__(self):
            # type: () -> None
            super(LegacyUserAttribute, self).__init__(
                user_editable=user_editable,
                show_in_table=show_in_table,
                add_custom_macro=add_custom_macro,
                domain=domain,
                permission=permission,
                from_config=from_config,
            )


def load_users(lock=False):
    # type: (bool) -> Users
    filename = _root_dir() + "contacts.mk"

    if lock:
        # Note: the lock will be released on next save_users() call or at
        #       end of page request automatically.
        store.aquire_lock(filename)

    if 'users' in g:
        return g.users

    # First load monitoring contacts from Check_MK's world. If this is
    # the first time, then the file will be empty, which is no problem.
    # Execfile will the simply leave contacts = {} unchanged.
    contacts = store.load_from_mk_file(filename, "contacts", {})

    # Now load information about users from the GUI config world
    filename = _multisite_dir() + "users.mk"
    users = store.load_from_mk_file(_multisite_dir() + "users.mk", "multisite_users", {})

    # Merge them together. Monitoring users not known to Multisite
    # will be added later as normal users.
    result = {}
    for uid, user in users.items():
        # Transform user IDs which were stored with a wrong type
        uid = ensure_text(uid)

        profile = contacts.get(uid, {})
        profile.update(user)
        result[uid] = profile

        # Convert non unicode mail addresses
        if "email" in profile:
            profile["email"] = ensure_text(profile["email"])

    # This loop is only neccessary if someone has edited
    # contacts.mk manually. But we want to support that as
    # far as possible.
    for uid, contact in contacts.items():
        # Transform user IDs which were stored with a wrong type
        uid = ensure_text(uid)

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

    def readlines(f):
        try:
            return Path(f).open(encoding="utf-8")
        except IOError:
            return []

    # FIXME TODO: Consolidate with htpasswd user connector
    filename = cmk.utils.paths.htpasswd_file
    for line in readlines(filename):
        line = line.strip()
        if ':' in line:
            uid, password = line.strip().split(":")[:2]
            uid = ensure_text(uid)
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
                new_user = {
                    "roles": config.roles_of_user(uid),
                    "password": password,
                    "locked": False,
                }
                result[uid] = new_user
            # Make sure that the user has an alias
            result[uid].setdefault("alias", uid)
        # Other unknown entries will silently be dropped. Sorry...

    # Now read the serials, only process for existing users
    serials_file = '%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file)
    for line in readlines(serials_file):
        line = line.strip()
        if ':' in line:
            user_id, serial = line.split(':')[:2]
            user_id = ensure_text(user_id)
            if user_id in result:
                result[user_id]['serial'] = utils.saveint(serial)

    # Now read the user specific files
    directory = cmk.utils.paths.var_dir + "/web/"
    for d in os.listdir(directory):
        if d[0] != '.':
            uid = ensure_text(d)

            # read special values from own files
            if uid in result:
                for attr, conv_func in [
                    ('num_failed_logins', utils.saveint),
                    ('last_pw_change', utils.saveint),
                    ('last_seen', utils.savefloat),
                    ('enforce_pw_change', lambda x: bool(utils.saveint(x))),
                    ('idle_timeout', _convert_idle_timeout),
                    ('session_id', _convert_session_info),
                ]:
                    val = load_custom_attr(uid, attr, conv_func)
                    if val is not None:
                        result[uid][attr] = val

            # read automation secrets and add them to existing
            # users or create new users automatically
            try:
                user_secret_path = Path(directory) / d / "automation.secret"
                with user_secret_path.open(encoding="utf-8") as f:
                    secret = six.ensure_str(f.read().strip())  # type: Optional[str]
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

    # populate the users cache
    g.users = result

    return result


def custom_attr_path(userid, key):
    # type: (UserId, str) -> str
    return cmk.utils.paths.var_dir + "/web/" + six.ensure_str(userid) + "/" + key + ".mk"


def load_custom_attr(userid, key, conv_func, default=None):
    # type: (UserId, str, Callable[[str], Any], Any) -> Any
    path = Path(custom_attr_path(userid, key))
    try:
        with path.open(encoding="utf-8") as f:
            return conv_func(six.ensure_str(f.read().strip()))
    except IOError:
        return default


def save_custom_attr(userid, key, val):
    # type: (UserId, str, Any) -> None
    path = custom_attr_path(userid, key)
    store.mkdir(os.path.dirname(path))
    store.save_file(path, '%s\n' % val)


def remove_custom_attr(userid, key):
    # type: (UserId, str) -> None
    try:
        os.unlink(custom_attr_path(userid, key))
    except OSError:
        pass  # Ignore non existing files


def get_online_user_ids():
    # type: () -> List[UserId]
    online_threshold = time.time() - config.user_online_maxage
    users = []
    for user_id, user in load_users(lock=False).items():
        if user.get('last_seen', 0) >= online_threshold:
            users.append(user_id)
    return users


def split_dict(d, keylist, positive):
    # type: (Dict[str, Any], List[str], bool) -> Dict[str, Any]
    return {k: v for k, v in d.items() if (k in keylist) == positive}


def save_users(profiles):
    # type: (Users) -> None
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

    # populate the users cache
    g.users = updated_profiles

    # Call the users_saved hook
    hooks.call("users-saved", updated_profiles)


# TODO: Isn't this needed only while generating the contacts.mk?
#       Check this and move it to the right place
def _add_custom_macro_attributes(profiles):
    # type: (Users) -> Users
    updated_profiles = copy.deepcopy(profiles)

    # Add custom macros
    core_custom_macros = set(name  #
                             for name, attr in get_user_attributes()
                             if attr.add_custom_macro())
    for user in updated_profiles.keys():
        for macro in core_custom_macros:
            if macro in updated_profiles[user]:
                updated_profiles[user]['_' + macro] = updated_profiles[user][macro]

    return updated_profiles


# Write user specific files
def _save_user_profiles(updated_profiles):
    # type: (Users) -> None
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()

    for user_id, user in updated_profiles.items():
        user_dir = cmk.utils.paths.var_dir + "/web/" + six.ensure_str(user_id)
        store.mkdir(user_dir)

        # authentication secret for local processes
        auth_file = user_dir + "/automation.secret"
        if "automation_secret" in user:
            store.save_file(auth_file, "%s\n" % user["automation_secret"])
        elif os.path.exists(auth_file):
            os.unlink(auth_file)

        # Write out user attributes which are written to dedicated files in the user
        # profile directory. The primary reason to have separate files, is to reduce
        # the amount of data to be loaded during regular page processing
        save_custom_attr(user_id, 'serial', str(user.get('serial', 0)))
        save_custom_attr(user_id, 'num_failed_logins', str(user.get('num_failed_logins', 0)))
        save_custom_attr(user_id, 'enforce_pw_change', str(int(user.get('enforce_pw_change',
                                                                        False))))
        save_custom_attr(user_id, 'last_pw_change', str(user.get('last_pw_change',
                                                                 int(time.time()))))

        if "idle_timeout" in user:
            save_custom_attr(user_id, "idle_timeout", user["idle_timeout"])
        else:
            remove_custom_attr(user_id, "idle_timeout")

        # Write out the last seent time
        if 'last_seen' in user:
            save_custom_attr(user_id, 'last_seen', repr(user['last_seen']))

        _save_cached_profile(user_id, user, multisite_keys, non_contact_keys)


# During deletion of users we don't delete files which might contain user settings
# and e.g. customized views which are not easy to reproduce. We want to keep the
# files which are the result of a lot of work even when e.g. the LDAP sync deletes
# a user by accident. But for some internal files it is ok to delete them.
#
# Be aware: The user_exists() function relies on these files to be deleted.
def _cleanup_old_user_profiles(updated_profiles):
    # type: (Users) -> None
    profile_files_to_delete = [
        "automation.secret",
        "transids.mk",
        "serial.mk",
    ]
    directory = cmk.utils.paths.var_dir + "/web"
    for user_dir in os.listdir(cmk.utils.paths.var_dir + "/web"):
        if user_dir not in ['.', '..'] and ensure_text(user_dir) not in updated_profiles:
            entry = directory + "/" + user_dir
            if not os.path.isdir(entry):
                continue

            for to_delete in profile_files_to_delete:
                if os.path.exists(entry + '/' + to_delete):
                    os.unlink(entry + '/' + to_delete)


def write_contacts_and_users_file(profiles, custom_default_config_dir=None):
    # type: (Users, str) -> None
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()
    updated_profiles = _add_custom_macro_attributes(profiles)

    if custom_default_config_dir:
        check_mk_config_dir = "%s/conf.d/wato" % custom_default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % custom_default_config_dir
    else:
        check_mk_config_dir = "%s/conf.d/wato" % cmk.utils.paths.default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % cmk.utils.paths.default_config_dir

    non_contact_attributes_cache = {}  # type: Dict[Optional[str], List[str]]
    multisite_attributes_cache = {}  # type: Dict[Optional[str], List[str]]
    for user_settings in updated_profiles.values():
        connector = cast(Optional[str], user_settings.get("connector"))
        if connector not in non_contact_attributes_cache:
            non_contact_attributes_cache[connector] = non_contact_attributes(connector)
        if connector not in multisite_attributes_cache:
            multisite_attributes_cache[connector] = multisite_attributes(connector)

    # Remove multisite keys in contacts.
    # TODO: Clean this up. Just improved the performance, but still have no idea what its actually doing...
    contacts = dict(e for e in [(id,
                                 split_dict(
                                     user,
                                     non_contact_keys +
                                     non_contact_attributes_cache[user.get('connector')],
                                     False,
                                 )) for (id, user) in updated_profiles.items()])

    # Only allow explicitely defined attributes to be written to multisite config
    users = {}
    for uid, profile in updated_profiles.items():
        users[uid] = {
            p: val
            for p, val in profile.items()
            if p in multisite_keys + multisite_attributes_cache[profile.get('connector')]
        }

    # Check_MK's monitoring contacts
    store.save_to_mk_file("%s/%s" % (check_mk_config_dir, "contacts.mk"),
                          "contacts",
                          contacts,
                          pprint_value=config.wato_pprint_config)

    # GUI specific user configuration
    store.save_to_mk_file("%s/%s" % (multisite_config_dir, "users.mk"),
                          "multisite_users",
                          users,
                          pprint_value=config.wato_pprint_config)


def _non_contact_keys():
    # type: () -> List[str]
    """User attributes not to put into contact definitions for Check_MK"""
    return [
        "roles",
        "password",
        "locked",
        "automation_secret",
        "language",
        "serial",
        "connector",
        "num_failed_logins",
        "enforce_pw_change",
        "last_pw_change",
        "last_seen",
        "idle_timeout",
    ] + _get_multisite_custom_variable_names()


def _multisite_keys():
    # type: () -> List[str]
    """User attributes to put into multisite configuration"""
    return [
        "roles",
        "locked",
        "automation_secret",
        "alias",
        "language",
        "connector",
    ] + _get_multisite_custom_variable_names()


def _get_multisite_custom_variable_names():
    # type: () -> List[str]
    return [
        name  #
        for name, attr in get_user_attributes()
        if attr.domain() == "multisite"
    ]


def _save_auth_serials(updated_profiles):
    # type: (Users) -> None
    """Write out the users serials"""
    # Write out the users serials
    serials = u""
    for user_id, user in updated_profiles.items():
        serials += u'%s:%d\n' % (user_id, user.get('serial', 0))
    store.save_file('%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file), serials)


def rewrite_users():
    # type: () -> None
    users = load_users(lock=True)
    save_users(users)


def create_cmk_automation_user():
    # type: () -> None
    secret = utils.gen_id()

    users = load_users(lock=True)
    users[UserId(u"automation")] = {
        'alias': u"Check_MK Automation - used for calling web services",
        'contactgroups': [],
        'automation_secret': secret,
        'password': cmk.gui.plugins.userdb.htpasswd.hash_password(secret),
        'roles': ['admin'],
        'locked': False,
        'serial': 0,
        'email': '',
        'pager': '',
        'notifications_enabled': False,
        'language': 'en',
    }
    save_users(users)


def _save_cached_profile(user_id, user, multisite_keys, non_contact_keys):
    # type: (UserId, UserSpec, List[str], List[str]) -> None
    # Only save contact AND multisite attributes to the profile. Not the
    # infos that are stored in the custom attribute files.
    cache = {}
    for key in user.keys():
        if key in multisite_keys or key not in non_contact_keys:
            cache[key] = user[key]

    config.save_user_file("cached_profile", cache, user_id=user_id)


def contactgroups_of_user(user_id):
    # type: (UserId) -> List[ContactgroupName]
    user = load_cached_profile(user_id)
    if user is None:
        # No cached profile present. Load all users to get the users data
        user = load_users(lock=False).get(user_id, {})
        assert user is not None  # help mypy

    return user.get("contactgroups", [])


def _convert_idle_timeout(value):
    # type: (str) -> Union[int, bool, None]
    if value == "False":
        return False  # Idle timeout disabled

    try:
        return int(value)
    except ValueError:
        return None  # Invalid value -> use global setting


#.
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


def update_config_based_user_attributes():
    # type: () -> None
    _clear_config_based_user_attributes()

    for attr in config.wato_user_attrs:
        if attr["type"] == "TextAscii":
            vs = TextAscii(title=attr['title'], help=attr['help'])
        else:
            raise NotImplementedError()

        # TODO: This method uses LegacyUserAttribute(). Use another class for
        # this kind of attribute
        declare_user_attribute(
            attr['name'],
            vs,
            user_editable=attr['user_editable'],
            show_in_table=attr.get('show_in_table', False),
            topic=attr.get('topic', 'personal'),
            add_custom_macro=attr.get('add_custom_macro', False),
            from_config=True,
        )

    cmk.gui.plugins.userdb.ldap_connector.register_user_attribute_sync_plugins()


def _clear_config_based_user_attributes():
    # type: () -> None
    for _name, attr in get_user_attributes():
        if attr.from_config():
            user_attribute_registry.unregister(attr.name())


# Make the config module initialize the user attributes after loading the config
config.register_post_config_load_hook(update_config_based_user_attributes)

#.
#   .-Hooks----------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


# This hook is called to validate the login credentials provided by a user
def hook_login(username, password):
    # type: (UserId, str) -> Union[UserId, bool]
    for connection_id, connection in active_connections():
        result = connection.check_credentials(username, password)
        # None        -> User unknown, means continue with other connectors
        # '<user_id>' -> success
        # False       -> failed
        if result not in [False, None]:
            username = result
            if not isinstance(username, str):
                raise MKInternalError(
                    _("The username returned by the %s "
                      "connector is not of type string (%r).") % (connection_id, username))
            # Check whether or not the user exists (and maybe create it)
            create_non_existing_user(connection_id, username)

            if not is_customer_user_allowed_to_login(username):
                # A CME not assigned with the current sites customer
                # is not allowed to login
                auth_logger.debug("User '%s' is not allowed to login: Invalid customer" % username)
                return False

            # Now, after successfull login (and optional user account creation), check whether or
            # not the user is locked.
            if _user_locked(username):
                auth_logger.debug("User '%s' is not allowed to login: Account locked" % username)
                return False  # The account is locked

            return result

        if result is False:
            return False

    return False


def show_exception(connection_id, title, e, debug=True):
    # type: (str, str, Exception, bool) -> None
    html.show_error("<b>" + connection_id + ' - ' + title + "</b>"
                    "<pre>%s</pre>" % (debug and traceback.format_exc() or e))


def hook_save(users):
    # type: (Users) -> None
    """Hook function can be registered here to be executed during saving of the
    new user construct"""
    for connection_id, connection in active_connections():
        try:
            connection.save_users(users)
        except Exception as e:
            if config.debug:
                raise
            show_exception(connection_id, _("Error during saving"), e)


def general_userdb_job():
    # type: () -> None
    """This function registers general stuff, which is independet of the single
    connectors to each page load. It is exectued AFTER all other connections jobs."""

    hooks.call("userdb-job")

    # Create initial auth.serials file, same issue as auth.php above
    serials_file = '%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file)
    if not os.path.exists(serials_file) or os.path.getsize(serials_file) == 0:
        rewrite_users()


def execute_userdb_job():
    # type: () -> None
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log. """
    if not userdb_sync_job_enabled():
        return

    job = UserSyncBackgroundJob()
    if job.is_active():
        logger.debug("Another synchronization job is already running: Skipping this sync")
        return

    job.set_function(job.do_sync,
                     add_to_changelog=False,
                     enforce_sync=False,
                     load_users_func=load_users,
                     save_users_func=save_users)
    job.start()


def userdb_sync_job_enabled():
    # type: () -> bool
    cfg = user_sync_config()

    if cfg is None:
        return False  # not enabled at all

    if cfg == "master" and config.is_wato_slave_site():
        return False

    return True


@cmk.gui.pages.register("ajax_userdb_sync")
def ajax_sync():
    # type: () -> None
    try:
        job = UserSyncBackgroundJob()
        job.set_function(job.do_sync,
                         add_to_changelog=False,
                         enforce_sync=True,
                         load_users_func=load_users,
                         save_users_func=save_users)
        try:
            job.start()
        except background_job.BackgroundJobAlreadyRunning as e:
            raise MKUserError(None, _("Another user synchronization is already running: %s") % e)
        html.write('OK Started synchronization\n')
    except Exception as e:
        logger.exception("error synchronizing user DB")
        if config.debug:
            raise
        html.write('ERROR %s\n' % e)


@gui_background_job.job_registry.register
class UserSyncBackgroundJob(gui_background_job.GUIBackgroundJob):
    job_prefix = "user_sync"

    @classmethod
    def gui_title(cls):
        # type: () -> str
        return _("User synchronization")

    def __init__(self):
        # type: () -> None
        super(UserSyncBackgroundJob, self).__init__(
            self.job_prefix,
            title=self.gui_title(),
            stoppable=False,
        )

    def _back_url(self):
        # type: () -> str
        return html.makeuri_contextless([("mode", "users")], filename="wato.py")

    def do_sync(self, job_interface, add_to_changelog, enforce_sync, load_users_func,
                save_users_func):
        # type: (background_job.BackgroundProcessInterface, bool, bool, Callable, Callable) -> None
        job_interface.send_progress_update(_("Synchronization started..."))
        if self._execute_sync_action(job_interface, add_to_changelog, enforce_sync, load_users_func,
                                     save_users_func):
            job_interface.send_result_message(_("The user synchronization completed successfully."))
        else:
            job_interface.send_exception(_("The user synchronization failed."))

    def _execute_sync_action(self, job_interface, add_to_changelog, enforce_sync, load_users_func,
                             save_users_func):
        # type: (background_job.BackgroundProcessInterface, bool, bool, Callable, Callable) -> bool
        for connection_id, connection in active_connections():
            try:
                if not enforce_sync and not connection.sync_is_needed():
                    continue

                job_interface.send_progress_update(
                    _("[%s] Starting sync for connection") % connection_id)
                connection.do_sync(add_to_changelog=add_to_changelog,
                                   only_username=False,
                                   load_users_func=load_users,
                                   save_users_func=save_users)
                job_interface.send_progress_update(
                    _("[%s] Finished sync for connection") % connection_id)
            except Exception as e:
                job_interface.send_exception(_("[%s] Exception: %s") % (connection_id, e))
                logger.error('Exception (%s, userdb_job): %s', connection_id,
                             traceback.format_exc())

        job_interface.send_progress_update(_("Finalizing synchronization"))
        general_userdb_job()
        return True
