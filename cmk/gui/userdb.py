#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# TODO: Rework connection management and multiplexing

from typing import Any, Dict, List, Optional, Tuple  # pylint: disable=unused-import
import time
import os
import traceback
import copy

import pathlib2 as pathlib
import six

import cmk.utils
import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.hooks as hooks
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
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

from cmk.gui.plugins.userdb.utils import (  # pylint: disable=unused-import
    user_attribute_registry, user_connector_registry, UserConnector,
)

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

auth_logger = logger.getChild("auth")


# Load all userdb plugins
def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    utils.load_web_plugins("userdb", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


def _all_connections():
    # type: () -> List[Tuple[str, UserConnector]]
    return _get_connections_for(_get_connection_configs())


def active_connections():
    # type: () -> List[Tuple[str, UserConnector]]
    enabled_configs = [
        cfg  #
        for cfg in _get_connection_configs()
        if not cfg['disabled']
    ]
    return [
        (connection_id, connection)  #
        for connection_id, connection in _get_connections_for(enabled_configs)
        if connection.is_enabled()
    ]


def _get_connections_for(configs):
    # type: (List[Dict[str, Any]]) -> List[Tuple[str, UserConnector]]
    return [(cfg['id'], user_connector_registry[cfg['type']](cfg)) for cfg in configs]


def _get_connection_configs():
    # type: () -> List[Dict[str, Any]]
    # The htpasswd connector is enabled by default and always executed first.
    return [_HTPASSWD_CONNECTION] + config.user_connections


_HTPASSWD_CONNECTION = {
    'type': 'htpasswd',
    'id': 'htpasswd',
    'disabled': False,
}


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


def connection_choices():
    # type: () -> List[Tuple[str, str]]
    return sorted([(connection_id, "%s (%s)" % (connection_id, connection.type()))
                   for connection_id, connection in _all_connections()
                   if connection.type() == "ldap"],
                  key=lambda id_and_description: id_and_description[1])


# When at least one LDAP connection is defined and active a sync is possible
def sync_possible():
    # type: () -> bool
    return any(connection.type() == "ldap" for _connection_id, connection in active_connections())


def cleanup_connection_id(connection_id):
    # type: (Optional[str]) -> str
    if connection_id is None:
        return 'htpasswd'

    # Old Check_MK used a static "ldap" connector id for all LDAP users.
    # Since Check_MK now supports multiple LDAP connections, the ID has
    # been changed to "default". But only transform this when there is
    # no connection existing with the id LDAP.
    if connection_id == 'ldap' and not get_connection('ldap'):
        return 'default'

    return connection_id


# Returns the connection object of the requested connection id. This function
# maintains a cache that for a single connection_id only one object per request
# is created.
def get_connection(connection_id):
    # type: (str) -> Optional[UserConnector]
    if 'user_connections' not in g:
        g.user_connections = {}

    if connection_id not in g.user_connections:
        connections_with_id = [c for cid, c in _all_connections() if cid == connection_id]
        # NOTE: We cache even failed lookups.
        g.user_connections[connection_id] = connections_with_id[0] if connections_with_id else None

    return g.user_connections[connection_id]


# Returns a list of connection specific locked attributes
def locked_attributes(connection_id):
    return get_attributes(connection_id, "locked_attributes")


# Returns a list of connection specific multisite attributes
def multisite_attributes(connection_id):
    return get_attributes(connection_id, "multisite_attributes")


# Returns a list of connection specific non contact attributes
def non_contact_attributes(connection_id):
    return get_attributes(connection_id, "non_contact_attributes")


def get_attributes(connection_id, what):
    connection = get_connection(connection_id)
    if connection:
        return getattr(connection, what)()
    return []


def new_user_template(connection_id):
    new_user = {
        'serial': 0,
        'connector': connection_id,
    }

    # Apply the default user profile
    new_user.update(config.default_user_profile)
    return new_user


def create_non_existing_user(connection_id, username):
    if user_exists(username):
        return  # User exists. Nothing to do...

    users = load_users(lock=True)
    users[username] = new_user_template(connection_id)
    save_users(users)

    # Call the sync function for this new user
    connection = get_connection(connection_id)
    try:
        connection.do_sync(add_to_changelog=False, only_username=username)
    except cmk.gui.plugins.userdb.ldap_connector.MKLDAPException as e:
        show_exception(connection_id, _("Error during sync"), e, debug=config.debug)
    except Exception as e:
        show_exception(connection_id, _("Error during sync"), e)


def is_customer_user_allowed_to_login(user_id):
    if not cmk.is_managed_edition():
        return True

    import cmk.gui.cme.managed as managed
    user = config.LoggedInUser(user_id)
    customer_id = managed.get_customer_id(user.attributes)

    if managed.is_global(customer_id):
        return True

    return managed.is_current_customer(customer_id)


# This function is called very often during regular page loads so it has to be efficient
# even when having a lot of users.
#
# When using the multisite authentication with just by WATO created users it would be
# easy, but we also need to deal with users which are only existant in the htpasswd
# file and don't have a profile directory yet.
def user_exists(username):
    if _user_exists_according_to_profile(username):
        return True

    return Htpasswd(pathlib.Path(cmk.utils.paths.htpasswd_file)).exists(username)


def _user_exists_according_to_profile(username):
    base_path = config.config_dir + "/" + username.encode("utf-8") + "/"
    return os.path.exists(base_path + "transids.mk") \
            or os.path.exists(base_path + "serial.mk")


def user_locked(username):
    users = load_users()
    return users[username].get('locked', False)


def login_timed_out(username, last_activity):
    idle_timeout = load_custom_attr(username, "idle_timeout", convert_idle_timeout, None)
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
    if not config.save_user_access_times:
        return
    save_custom_attr(username, 'last_seen', repr(time.time()))


def on_succeeded_login(username):
    num_failed_logins = load_custom_attr(username, 'num_failed_logins', utils.saveint)
    if num_failed_logins is not None and num_failed_logins != 0:
        save_custom_attr(username, 'num_failed_logins', '0')

    update_user_access_time(username)


# userdb.need_to_change_pw returns either False or the reason description why the
# password needs to be changed
def need_to_change_pw(username):
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
        elif time.time() - last_pw_change > max_pw_age:
            return 'expired'
    return False


def on_failed_login(username):
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
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def _multisite_dir():
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# Old vs:
#ListChoice(
#    title = _('Automatic User Synchronization'),
#    help  = _('By default the users are synchronized automatically in several situations. '
#              'The sync is started when opening the "Users" page in configuration and '
#              'during each page rendering. Each connector can then specify if it wants to perform '
#              'any actions. For example the LDAP connector will start the sync once the cached user '
#              'information are too old.'),
#    default_value = [ 'wato_users', 'page', 'wato_pre_activate_changes', 'wato_snapshot_pushed' ],
#    choices       = [
#        ('page',                      _('During regular page processing')),
#        ('wato_users',                _('When opening the users\' configuration page')),
#        ('wato_pre_activate_changes', _('Before activating the changed configuration')),
#        ('wato_snapshot_pushed',      _('On a remote site, when it receives a new configuration')),
#    ],
#    allow_empty   = True,
#),
def transform_userdb_automatic_sync(val):
    if val == []:
        # legacy compat - disabled
        return None

    elif isinstance(val, list) and val:
        # legacy compat - all connections
        return "all"

    return val


class UserSelection(DropdownChoice):
    """Dropdown for choosing a multisite user"""
    def __init__(self, **kwargs):
        only_contacts = kwargs.get("only_contacts", False)
        only_automation = kwargs.get("only_automation", False)
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
                               (not only_automation or us.get("automation_secret"))])
            if nv is not None:
                elements = [(None, none_value)] + elements
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
    if config.single_user_session is None:
        return True  # No login session limitation enabled, no validation

    session_info = load_session_info(username)
    if session_info is None:
        return False  # no session active
    else:
        active_session_id, last_activity = session_info

    if session_id == active_session_id:
        return True  # Current session. Fine.

    auth_logger.debug("%s session_id not valid (timed out?) (Inactive for %d seconds)" %
                      (username, time.time() - last_activity))

    return False


def ensure_user_can_init_session(username):
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


# Creates a new user login session (if single user session mode is enabled) and
# returns the session_id of the new session.
def initialize_session(username):
    if not config.single_user_session:
        return ""

    session_id = create_session_id()
    save_session_info(username, session_id)
    return session_id


# Creates a random session id for the user and returns it.
def create_session_id():
    return utils.gen_id()


# Updates the current session of the user and returns the session_id or only
# returns an empty string when single user session mode is not enabled.
def refresh_session(username):
    if not config.single_user_session:
        return ""

    session_info = load_session_info(username)
    if session_info is None:
        return  # Don't refresh. Session is not valid anymore

    session_id = session_info[0]
    save_session_info(username, session_id)


def invalidate_session(username):
    remove_custom_attr(username, "session_info")


# Saves the current session_id and the current time (last activity)
def save_session_info(username, session_id):
    save_custom_attr(username, "session_info", "%s|%s" % (session_id, int(time.time())))


# Returns either None (when no session_id available) or a two element
# tuple where the first element is the sesssion_id and the second the
# timestamp of the last activity.
def load_session_info(username):
    return load_custom_attr(username, "session_info", convert_session_info)


def convert_session_info(value):
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
        super(GenericUserAttribute, self).__init__()
        self._user_editable = user_editable
        self._show_in_table = show_in_table
        self._add_custom_macro = add_custom_macro
        self._domain = domain
        self._permission = permission
        self._from_config = from_config

    def from_config(self):
        return self._from_config

    def user_editable(self):
        return self._user_editable

    def permission(self):
        return self._permission

    def show_in_table(self):
        return self._show_in_table

    def add_custom_macro(self):
        return self._add_custom_macro

    def domain(self):
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
            return cls._name

        @classmethod
        def valuespec(cls):
            return cls._valuespec

        @classmethod
        def topic(cls):
            return cls._topic

        def __init__(self):
            super(LegacyUserAttribute, self).__init__(
                user_editable=user_editable,
                show_in_table=show_in_table,
                add_custom_macro=add_custom_macro,
                domain=domain,
                permission=permission,
                from_config=from_config,
            )


def get_user_attributes():
    return [(k, v()) for k, v in user_attribute_registry.items()]


def load_users(lock=False):
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
        if isinstance(uid, str):
            uid = uid.decode("utf-8")

        profile = contacts.get(uid, {})
        profile.update(user)
        result[uid] = profile

        # Convert non unicode mail addresses
        if isinstance(profile.get("email"), str):
            profile["email"] = profile["email"].decode("utf-8")

    # This loop is only neccessary if someone has edited
    # contacts.mk manually. But we want to support that as
    # far as possible.
    for uid, contact in contacts.items():
        # Transform user IDs which were stored with a wrong type
        if isinstance(uid, str):
            uid = uid.decode("utf-8")

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
            return file(f)
        except IOError:
            return []

    # FIXME TODO: Consolidate with htpasswd user connector
    filename = cmk.utils.paths.htpasswd_file
    for line in readlines(filename):
        line = line.strip()
        if ':' in line:
            uid, password = line.strip().split(":")[:2]
            uid = uid.decode("utf-8")
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
            user_id = user_id.decode("utf-8")
            if user_id in result:
                result[user_id]['serial'] = utils.saveint(serial)

    # Now read the user specific files
    directory = cmk.utils.paths.var_dir + "/web/"
    for d in os.listdir(directory):
        if d[0] != '.':
            uid = d.decode("utf-8")

            # read special values from own files
            if uid in result:
                for attr, conv_func in [
                    ('num_failed_logins', utils.saveint),
                    ('last_pw_change', utils.saveint),
                    ('last_seen', utils.savefloat),
                    ('enforce_pw_change', lambda x: bool(utils.saveint(x))),
                    ('idle_timeout', convert_idle_timeout),
                    ('session_id', convert_session_info),
                ]:
                    val = load_custom_attr(uid, attr, conv_func)
                    if val is not None:
                        result[uid][attr] = val

            # read automation secrets and add them to existing
            # users or create new users automatically
            try:
                secret = file(directory + d + "/automation.secret").read().strip()
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
    return cmk.utils.paths.var_dir + "/web/" + cmk.utils.make_utf8(userid) + "/" + key + ".mk"


def load_custom_attr(userid, key, conv_func, default=None):
    path = custom_attr_path(userid, key)
    try:
        return conv_func(file(path).read().strip())
    except IOError:
        return default


def save_custom_attr(userid, key, val):
    path = custom_attr_path(userid, key)
    store.mkdir(os.path.dirname(path))
    store.save_file(path, '%s\n' % val)


def remove_custom_attr(userid, key):
    try:
        os.unlink(custom_attr_path(userid, key))
    except OSError:
        pass  # Ignore non existing files


def get_online_user_ids():
    online_threshold = time.time() - config.user_online_maxage
    users = []
    for user_id, user in load_users(lock=False).items():
        if user.get('last_seen', 0) >= online_threshold:
            users.append(user_id)
    return users


def split_dict(d, keylist, positive):
    return dict([(k, v) for (k, v) in d.items() if (k in keylist) == positive])


def save_users(profiles):
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


def release_users_lock():
    store.release_lock(_root_dir() + "contacts.mk")


# TODO: Isn't this needed only while generating the contacts.mk?
#       Check this and move it to the right place
def _add_custom_macro_attributes(profiles):
    updated_profiles = copy.deepcopy(profiles)

    # Add custom macros
    core_custom_macros = set(k for k, o in get_user_attributes() if o.add_custom_macro())
    for user in updated_profiles.keys():
        for macro in core_custom_macros:
            if macro in updated_profiles[user]:
                updated_profiles[user]['_' + macro] = updated_profiles[user][macro]

    return updated_profiles


# Write user specific files
def _save_user_profiles(updated_profiles):
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()

    for user_id, user in updated_profiles.items():
        user_dir = cmk.utils.paths.var_dir + "/web/" + user_id.encode("utf-8")
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

        save_cached_profile(user_id, user, multisite_keys, non_contact_keys)


# During deletion of users we don't delete files which might contain user settings
# and e.g. customized views which are not easy to reproduce. We want to keep the
# files which are the result of a lot of work even when e.g. the LDAP sync deletes
# a user by accident. But for some internal files it is ok to delete them.
#
# Be aware: The user_exists() function relies on these files to be deleted.
def _cleanup_old_user_profiles(updated_profiles):
    profile_files_to_delete = [
        "automation.secret",
        "transids.mk",
        "serial.mk",
    ]
    directory = cmk.utils.paths.var_dir + "/web"
    for user_dir in os.listdir(cmk.utils.paths.var_dir + "/web"):
        if user_dir not in ['.', '..'] and user_dir.decode("utf-8") not in updated_profiles:
            entry = directory + "/" + user_dir
            if not os.path.isdir(entry):
                continue

            for to_delete in profile_files_to_delete:
                if os.path.exists(entry + '/' + to_delete):
                    os.unlink(entry + '/' + to_delete)


def write_contacts_and_users_file(profiles, custom_default_config_dir=None):
    non_contact_keys = _non_contact_keys()
    multisite_keys = _multisite_keys()
    updated_profiles = _add_custom_macro_attributes(profiles)

    if custom_default_config_dir:
        check_mk_config_dir = "%s/conf.d/wato" % custom_default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % custom_default_config_dir
    else:
        check_mk_config_dir = "%s/conf.d/wato" % cmk.utils.paths.default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % cmk.utils.paths.default_config_dir

    non_contact_attributes_cache = {}
    multisite_attributes_cache = {}
    for user_settings in updated_profiles.itervalues():
        connector = user_settings.get("connector")
        if connector not in non_contact_attributes_cache:
            non_contact_attributes_cache[connector] = non_contact_attributes(
                user_settings.get('connector'))
        if connector not in multisite_attributes_cache:
            multisite_attributes_cache[connector] = multisite_attributes(
                user_settings.get('connector'))

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
        users[uid] = dict([
            (p, val)
            for p, val in profile.items()
            if p in multisite_keys + multisite_attributes_cache[profile.get('connector')]
        ])

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


# User attributes not to put into contact definitions for Check_MK
def _non_contact_keys():
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


# User attributes to put into multisite configuration
def _multisite_keys():
    return [
        "roles",
        "locked",
        "automation_secret",
        "alias",
        "language",
        "connector",
    ] + _get_multisite_custom_variable_names()


def _get_multisite_custom_variable_names():
    return [k for k, v in get_user_attributes() if v.domain() == "multisite"]


def _save_auth_serials(updated_profiles):
    # Write out the users serials
    serials = ""
    for user_id, user in updated_profiles.items():
        serials += '%s:%d\n' % (cmk.utils.make_utf8(user_id), user.get('serial', 0))
    store.save_file('%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file), serials)


def rewrite_users():
    users = load_users(lock=True)
    save_users(users)


def create_cmk_automation_user():
    secret = utils.gen_id()

    users = load_users(lock=True)
    users["automation"] = {
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


def save_cached_profile(user_id, user, multisite_keys, non_contact_keys):
    # Only save contact AND multisite attributes to the profile. Not the
    # infos that are stored in the custom attribute files.
    cache = {}
    for key in user.keys():
        if key in multisite_keys or key not in non_contact_keys:
            cache[key] = user[key]

    config.save_user_file("cached_profile", cache, user_id=user_id)


def load_cached_profile():
    return config.user.load_file("cached_profile", None)


def contactgroups_of_user(user_id):
    user = load_cached_profile()
    if user is None:
        # No cached profile present. Load all users to get the users data
        user = load_users(lock=False).get(user_id, {})

    return user.get("contactgroups", [])


def convert_idle_timeout(value):
    if value == "False":
        return False  # Idle timeout disabled

    try:
        return int(value)
    except ValueError:
        return None  # Invalid value -> use global setting


#.
#   .-Roles----------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def load_roles():
    roles = store.load_from_mk_file(
        _multisite_dir() + "roles.mk",
        "roles",
        default=_get_builtin_roles(),
    )

    # Make sure that "general." is prefixed to the general permissions
    # (due to a code change that converted "use" into "general.use", etc.
    # TODO: Can't we drop this? This seems to be from very early days of the GUI
    for role in roles.values():
        for pname, pvalue in role["permissions"].items():
            if "." not in pname:
                del role["permissions"][pname]
                role["permissions"]["general." + pname] = pvalue

    # Reflect the data in the roles dict kept in the config module needed
    # for instant changes in current page while saving modified roles.
    # Otherwise the hooks would work with old data when using helper
    # functions from the config module
    # TODO: load_roles() should not update global structures
    config.roles.update(roles)

    return roles


def _get_builtin_roles():
    """Returns a role dictionary containing the bultin default roles"""
    builtin_role_names = {
        "admin": _("Administrator"),
        "user": _("Normal monitoring user"),
        "guest": _("Guest user"),
    }
    return {
        rid: {
            "alias": builtin_role_names.get(rid, rid),
            "permissions": {},  # use default everywhere
            "builtin": True,
        } for rid in config.builtin_role_ids
    }


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

    cmk.gui.plugins.userdb.ldap_connector.register_user_attribute_sync_plugins(
        user_attribute_registry)


def _clear_config_based_user_attributes():
    for attr_class in user_attribute_registry.values():
        attr = attr_class()
        if attr.from_config():
            del user_attribute_registry[attr.name()]


# Make the config module initialize the user attributes after loading the config
config.register_post_config_load_hook(update_config_based_user_attributes)

#.
#   .--ConnectorCfg--------------------------------------------------------.
#   |    ____                            _              ____  __           |
#   |   / ___|___  _ __  _ __   ___  ___| |_ ___  _ __ / ___|/ _| __ _     |
#   |  | |   / _ \| '_ \| '_ \ / _ \/ __| __/ _ \| '__| |   | |_ / _` |    |
#   |  | |__| (_) | | | | | | |  __/ (__| || (_) | |  | |___|  _| (_| |    |
#   |   \____\___/|_| |_|_| |_|\___|\___|\__\___/|_|   \____|_|  \__, |    |
#   |                                                            |___/     |
#   +----------------------------------------------------------------------+
#   | The user can enable and configure a list of user connectors which    |
#   | are then used by the userdb to fetch user / group information from   |
#   | external sources like LDAP servers.                                  |
#   '----------------------------------------------------------------------'


def load_connection_config(lock=False):
    filename = os.path.join(_multisite_dir(), "user_connections.mk")
    return store.load_from_mk_file(filename, "user_connections", default=[], lock=lock)


def save_connection_config(connections, base_dir=None):
    if not base_dir:
        base_dir = _multisite_dir()
    store.mkdir(base_dir)
    store.save_to_mk_file(os.path.join(base_dir, "user_connections.mk"), "user_connections",
                          connections)

    for connector_class in user_connector_registry.values():
        connector_class.config_changed()


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
    for connection_id, connection in active_connections():
        result = connection.check_credentials(username, password)
        # None        -> User unknown, means continue with other connectors
        # '<user_id>' -> success
        # False       -> failed
        if result not in [False, None]:
            username = result
            if not isinstance(username, six.string_types):
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

            # Now, after successfull login (and optional user account
            # creation), check whether or not the user is locked.
            # In e.g. htpasswd connector this is checked by validating the
            # password against the hash in the htpasswd file prefixed with
            # a "!". But when using other conectors it might be neccessary
            # to validate the user "locked" attribute.
            if connection.is_locked(username):
                auth_logger.debug("User '%s' is not allowed to login: Account locked" % username)
                return False  # The account is locked

            return result

        elif result is False:
            return result


def show_exception(connection_id, title, e, debug=True):
    html.show_error("<b>" + connection_id + ' - ' + title + "</b>"
                    "<pre>%s</pre>" % (debug and traceback.format_exc() or e))


# Hook function can be registered here to be executed during saving of the
# new user construct
def hook_save(users):
    for connection_id, connection in active_connections():
        try:
            connection.save_users(users)
        except Exception as e:
            if config.debug:
                raise
            else:
                show_exception(connection_id, _("Error during saving"), e)


# This function registers general stuff, which is independet of the single
# connectors to each page load. It is exectued AFTER all other connections jobs.
def general_userdb_job():
    # Working around the problem that the auth.php file needed for multisite based
    # authorization of external addons might not exist when setting up a new installation
    # We assume: Each user must visit this login page before using the multisite based
    #            authorization. So we can easily create the file here if it is missing.
    # This is a good place to replace old api based files in the future.
    auth_php = cmk.utils.paths.var_dir + '/wato/auth/auth.php'
    if not os.path.exists(auth_php) or os.path.getsize(auth_php) == 0:
        cmk.gui.plugins.userdb.hook_auth.create_auth_file("page_hook", load_users())

    # Create initial auth.serials file, same issue as auth.php above
    serials_file = '%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file)
    if not os.path.exists(serials_file) or os.path.getsize(serials_file) == 0:
        rewrite_users()


def execute_userdb_job():
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log. """
    if not userdb_sync_job_enabled():
        return

    job = UserSyncBackgroundJob()
    if job.is_active():
        logger.debug("Another synchronization job is already running: Skipping this sync")
        return

    job.set_function(job.do_sync, add_to_changelog=False, enforce_sync=False)
    job.start()


# Legacy option config.userdb_automatic_sync defaulted to "master".
# Can be: None: (no sync), "all": all sites sync, "master": only master site sync
# Take that option into account for compatibility reasons.
# For remote sites in distributed setups, the default is to do no sync.
def user_sync_default_config(site_name):
    global_user_sync = transform_userdb_automatic_sync(config.userdb_automatic_sync)
    if global_user_sync == "master":
        if config.site_is_local(site_name) and not config.is_wato_slave_site():
            user_sync_default = "all"
        else:
            user_sync_default = None
    else:
        user_sync_default = global_user_sync

    return user_sync_default


def user_sync_config():
    # use global option as default for reading legacy options and on remote site
    # for reading the value set by the WATO master site
    default_cfg = user_sync_default_config(config.omd_site())
    return config.site(config.omd_site()).get("user_sync", default_cfg)


def userdb_sync_job_enabled():
    cfg = user_sync_config()

    if cfg is None:
        return False  # not enabled at all

    if cfg == "master" and config.is_wato_slave_site():
        return False

    return True


@cmk.gui.pages.register("ajax_userdb_sync")
def ajax_sync():
    try:
        job = UserSyncBackgroundJob()
        job.set_function(job.do_sync, add_to_changelog=False, enforce_sync=True)
        try:
            job.start()
        except background_job.BackgroundJobAlreadyRunning as e:
            raise MKUserError(None, _("Another user synchronization is already running: %s") % e)
        html.write('OK Started synchronization\n')
    except Exception as e:
        logger.exception("error synchronizing user DB")
        if config.debug:
            raise
        else:
            html.write('ERROR %s\n' % e)


@gui_background_job.job_registry.register
class UserSyncBackgroundJob(gui_background_job.GUIBackgroundJob):
    job_prefix = "user_sync"

    @classmethod
    def gui_title(cls):
        return _("User synchronization")

    def __init__(self):
        kwargs = {}
        kwargs["title"] = self.gui_title()
        kwargs["deletable"] = False
        kwargs["stoppable"] = False

        super(UserSyncBackgroundJob, self).__init__(self.job_prefix, **kwargs)

    def _back_url(self):
        return html.makeuri_contextless([("mode", "users")], filename="wato.py")

    def do_sync(self, job_interface, add_to_changelog, enforce_sync):
        job_interface.send_progress_update(_("Synchronization started..."))
        if self._execute_sync_action(job_interface, add_to_changelog, enforce_sync):
            job_interface.send_result_message(_("The user synchronization completed successfully."))
        else:
            job_interface.send_exception(_("The user synchronization failed."))

    def _execute_sync_action(self, job_interface, add_to_changelog, enforce_sync):
        for connection_id, connection in active_connections():
            try:
                if not enforce_sync and not connection.sync_is_needed():
                    continue

                job_interface.send_progress_update(
                    _("[%s] Starting sync for connection") % connection_id)
                connection.do_sync(add_to_changelog=add_to_changelog, only_username=False)
                job_interface.send_progress_update(
                    _("[%s] Finished sync for connection") % connection_id)
            except Exception as e:
                job_interface.send_exception(_("[%s] Exception: %s") % (connection_id, e))
                logger.error('Exception (%s, userdb_job): %s', connection_id,
                             traceback.format_exc())

        job_interface.send_progress_update(_("Finalizing synchronization"))
        general_userdb_job()
        return True
