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

import config, hooks
from lib import *
from log import logger
import time, os, pprint, shutil, traceback
from valuespec import *
import cmk.paths
import cmk.store as store

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Custom user attributes
user_attributes  = {}
builtin_user_attribute_names = []

# Connection configuration
connection_dict = {}
# Connection object dictionary
g_connections   = {}
auth_logger = logger.getChild("auth")

# declare lobal vars
multisite_user_connectors = {}

# Load all userdb plugins
def load_plugins(force):
    global builtin_user_attribute_names

    # Do not cache the custom user attributes. They can be created by the user
    # during runtime, means they need to be loaded during each page request.
    # But delete the old definitions before to also apply removals of attributes
    if user_attributes:
        declare_custom_user_attrs()

    connection_dict.clear()
    for connection in config.user_connections:
        connection_dict[connection['id']] = connection

    # Cleanup eventual still open connections
    if g_connections:
        g_connections.clear()

    global loaded_with_language
    if loaded_with_language == current_language and not force:
        return

    # clear global vars
    user_attributes.clear()
    multisite_user_connectors.clear()

    load_web_plugins("userdb", globals())
    builtin_user_attribute_names = user_attributes.keys()
    declare_custom_user_attrs()

    # Connectors have the option to perform migration of configuration options
    # while the initial loading is performed
    for connector_class in multisite_user_connectors.values():
        connector_class.migrate_config()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language


# Cleans up at the end of a request: Cleanup eventual open connections
def finalize():
    if g_connections:
        g_connections.clear()


# Returns a list of two part tuples where the first element is the unique
# connection id and the second element the connector specification dict
def get_connections(only_enabled=False):
    connections = []
    for connector_id, connector_class in multisite_user_connectors.items():
        if connector_id == 'htpasswd':
            # htpasswd connector is enabled by default and always executed first
            connections.insert(0, ('htpasswd', connector_class({})))
        else:
            for connection_config in config.user_connections:
                if only_enabled and connection_config.get('disabled'):
                    continue

                connection = connector_class(connection_config)

                if only_enabled and not connection.is_enabled():
                    continue

                connections.append((connection_config['id'], connection))
    return connections


def active_connections():
    return get_connections(only_enabled=True)


def connection_choices():
    return sorted([ (cid, "%s (%s)" % (cid, c.type())) for cid, c in get_connections(only_enabled=False)
                     if c.type() == "ldap" ],
                  key=lambda (x, y): y)


# When at least one LDAP connection is defined and active a sync is possible
def sync_possible():
    for connection_id, connection in active_connections():
        if connection.type() == "ldap":
            return True
    return False


def cleanup_connection_id(connection_id):
    if connection_id is None:
        connection_id = 'htpasswd'

    # Old Check_MK used a static "ldap" connector id for all LDAP users.
    # Since Check_MK now supports multiple LDAP connections, the ID has
    # been changed to "default". But only transform this when there is
    # no connection existing with the id LDAP.
    if connection_id == 'ldap' and not get_connection('ldap'):
        connection_id = 'default'

    return connection_id


# Returns the connection object of the requested connection id. This function
# maintains a cache that for a single connection_id only one object per request
# is created.
def get_connection(connection_id):
    if connection_id in g_connections:
        return g_connections[connection_id]

    connection = dict(get_connections()).get(connection_id)

    if connection:
        g_connections[connection_id] = connection

    return connection


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
    else:
        return []


def new_user_template(connection_id):
    new_user = {
        'serial':        0,
        'connector':     connection_id,
    }

    # Apply the default user profile
    new_user.update(config.default_user_profile)
    return new_user


def create_non_existing_user(connection_id, username):
    users = load_users(lock = True)
    if username in users:
        return # User exists. Nothing to do...

    users[username] = new_user_template(connection_id)
    save_users(users)

    # Call the sync function for this new user
    hook_sync(connection_id = connection_id, only_username = username)


def is_automation_user(user_id):
    return os.path.isfile(cmk.paths.var_dir + "/web/" + user_id.encode("utf-8") + "/automation.secret")


def is_customer_user_allowed_to_login(user_id):
    if not cmk.is_managed_edition():
       return True

    import managed
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

    return _user_exists_htpasswd(username)


def _user_exists_according_to_profile(username):
    base_path = config.config_dir + "/" + username.encode("utf-8") + "/"
    return os.path.exists(base_path + "transids.mk") \
            or os.path.exists(base_path + "serial.mk")


def _user_exists_htpasswd(username):
    for line in open(cmk.paths.htpasswd_file):
        l = line.decode("utf-8")
        if l.startswith("%s:" % username):
            return True
    return False


def user_locked(username):
    users = load_users()
    return users[username].get('locked', False)


def login_timed_out(username, last_activity):
    idle_timeout = load_custom_attr(username, "idle_timeout", convert_idle_timeout, None)
    if idle_timeout == None:
        idle_timeout = config.user_idle_timeout

    if idle_timeout in [ None, False ]:
        return False # no timeout activated at all

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
    num_failed_logins = load_custom_attr(username, 'num_failed_logins', saveint)
    if num_failed_logins != None and num_failed_logins != 0:
        save_custom_attr(username, 'num_failed_logins', '0')

    update_user_access_time(username)


# userdb.need_to_change_pw returns either False or the reason description why the
# password needs to be changed
def need_to_change_pw(username):
    if load_custom_attr(username, 'enforce_pw_change', saveint) == 1:
        return 'enforced'

    last_pw_change = load_custom_attr(username, 'last_pw_change', saveint)
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
    users = load_users(lock = True)
    if username in users:
        if "num_failed_logins" in users[username]:
            users[username]["num_failed_logins"] += 1
        else:
            users[username]["num_failed_logins"] = 1

        if config.lock_on_logon_failures:
            if users[username]["num_failed_logins"] >= config.lock_on_logon_failures:
                users[username]["locked"] = True

        save_users(users)

root_dir      = cmk.paths.check_mk_config_dir + "/wato/"
multisite_dir = cmk.paths.default_config_dir + "/multisite.d/wato/"

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

    elif type(val) == list and val:
        # legacy compat - all connections
        return "all"

    else:
        return val

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
    if config.single_user_session == None:
        return True # No login session limitation enabled, no validation

    session_info = load_session_info(username)
    if session_info == None:
        return False # no session active
    else:
        active_session_id, last_activity = session_info

    if session_id == active_session_id:
        return True # Current session. Fine.

    auth_logger.debug("%s session_id not valid (timed out?) (Inactive for %d seconds)" %
                                    (username, time.time() - last_activity))

    return False


def ensure_user_can_init_session(username):
    if config.single_user_session == None:
        return True # No login session limitation enabled, no validation

    session_timeout = config.single_user_session

    session_info = load_session_info(username)
    if session_info == None:
        return True # No session active

    last_activity = session_info[1]
    if (time.time() - last_activity) > session_timeout:
        return True # Former active session timed out

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
    return gen_id()


# Updates the current session of the user and returns the session_id or only
# returns an empty string when single user session mode is not enabled.
def refresh_session(username):
    if not config.single_user_session:
        return ""

    session_info = load_session_info(username)
    if session_info == None:
        return # Don't refresh. Session is not valid anymore

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
    else:
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

def declare_user_attribute(name, vs, user_editable = True, permission = None,
                           show_in_table = False, topic = None, add_custom_macro = False,
                           domain = "multisite"):

    user_attributes[name] = {
        'valuespec'         : vs,
        'user_editable'     : user_editable,
        'show_in_table'     : show_in_table,
        'topic'             : topic and topic or 'personal',
        'add_custom_macro'  : add_custom_macro,
        'domain'            : domain,
    }

    # Permission needed for editing this attribute
    if permission:
        user_attributes[name]["permission"] = permission

def get_user_attributes():
    return user_attributes.items()

def load_users(lock = False):
    filename = root_dir + "contacts.mk"

    if lock:
        # Note: the lock will be released on next save_users() call or at
        #       end of page request automatically.
        store.aquire_lock(filename)

    if html.is_cached('users'):
        return html.get_cached('users')

    # First load monitoring contacts from Check_MK's world. If this is
    # the first time, then the file will be empty, which is no problem.
    # Execfile will the simply leave contacts = {} unchanged.
    contacts = store.load_from_mk_file(filename, "contacts", {})

    # Now load information about users from the GUI config world
    filename = multisite_dir + "users.mk"
    users = store.load_from_mk_file(multisite_dir + "users.mk", "multisite_users", {})

    # Merge them together. Monitoring users not known to Multisite
    # will be added later as normal users.
    result = {}
    for id, user in users.items():
        profile = contacts.get(id, {})
        profile.update(user)
        result[id] = profile

        # Convert non unicode mail addresses
        if type(profile.get("email")) == str:
            profile["email"] = profile["email"].decode("utf-8")

    # This loop is only neccessary if someone has edited
    # contacts.mk manually. But we want to support that as
    # far as possible.
    for id, contact in contacts.items():
        if id not in result:
            result[id] = contact
            result[id]["roles"] = [ "user" ]
            result[id]["locked"] = True
            result[id]["password"] = ""

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
    filename = cmk.paths.htpasswd_file
    for line in readlines(filename):
        line = line.strip()
        if ':' in line:
            id, password = line.strip().split(":")[:2]
            id = id.decode("utf-8")
            if password.startswith("!"):
                locked = True
                password = password[1:]
            else:
                locked = False
            if id in result:
                result[id]["password"] = password
                result[id]["locked"] = locked
            else:
                # Create entry if this is an admin user
                new_user = {
                    "roles"    : config.roles_of_user(id),
                    "password" : password,
                    "locked"   : False,
                }
                result[id] = new_user
            # Make sure that the user has an alias
            result[id].setdefault("alias", id)
        # Other unknown entries will silently be dropped. Sorry...

    # Now read the serials, only process for existing users
    serials_file = '%s/auth.serials' % os.path.dirname(cmk.paths.htpasswd_file)
    for line in readlines(serials_file):
        line = line.strip()
        if ':' in line:
            user_id, serial = line.split(':')[:2]
            user_id = user_id.decode("utf-8")
            if user_id in result:
                result[user_id]['serial'] = saveint(serial)

    # Now read the user specific files
    dir = cmk.paths.var_dir + "/web/"
    for d in os.listdir(dir):
        if d[0] != '.':
            id = d.decode("utf-8")

            # read special values from own files
            if id in result:
                for attr, conv_func in [
                        ('num_failed_logins', saveint),
                        ('last_pw_change',    saveint),
                        ('last_seen',         savefloat),
                        ('enforce_pw_change', lambda x: bool(saveint(x))),
                        ('idle_timeout',      convert_idle_timeout),
                        ('session_id',        convert_session_info),
                    ]:
                    val = load_custom_attr(id, attr, conv_func)
                    if val != None:
                        result[id][attr] = val

            # read automation secrets and add them to existing
            # users or create new users automatically
            try:
                secret = file(dir + d + "/automation.secret").read().strip()
            except IOError:
                secret = None
            if secret:
                if id in result:
                    result[id]["automation_secret"] = secret
                else:
                    result[id] = {
                        "roles" : ["guest"],
                        "automation_secret" : secret,
                    }

    # populate the users cache
    html.set_cache('users', result)

    return result


def custom_attr_path(userid, key):
    return cmk.paths.var_dir + "/web/" + make_utf8(userid) + "/" + key + ".mk"


def load_custom_attr(userid, key, conv_func, default = None):
    path = custom_attr_path(userid, key)
    try:
        return conv_func(file(path).read().strip())
    except IOError:
        return default


def save_custom_attr(userid, key, val):
    path = custom_attr_path(userid, key)
    make_nagios_directory(os.path.dirname(path))
    store.save_file(path, '%s\n' % val)


def remove_custom_attr(userid, key):
    try:
        os.unlink(custom_attr_path(userid, key))
    except OSError:
        pass # Ignore non existing files


def get_online_user_ids():
    online_threshold = time.time() - config.user_online_maxage
    users = []
    for user_id, user in load_users(lock = False).items():
        if user.get('last_seen', 0) >= online_threshold:
            users.append(user_id)
    return users

def split_dict(d, keylist, positive):
    return dict([(k,v) for (k,v) in d.items() if (k in keylist) == positive])


def determine_save_users_data(profiles):
    import copy
    updated_profiles = copy.deepcopy(profiles)

    # Add custom macros
    core_custom_macros =  [ k for k,o in user_attributes.items() if o.get('add_custom_macro') ]
    for user in updated_profiles.keys():
        for macro in core_custom_macros:
            if macro in updated_profiles[user]:
                updated_profiles[user]['_'+macro] = updated_profiles[user][macro]

    multisite_custom_values = [ k for k,v in user_attributes.items() if v["domain"] == "multisite" ]

    # Keys not to put into contact definitions for Check_MK
    non_contact_keys = [
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
    ] + multisite_custom_values

    # Keys to put into multisite configuration
    multisite_keys   = [
        "roles",
        "locked",
        "automation_secret",
        "alias",
        "language",
        "connector",
    ] + multisite_custom_values

    return non_contact_keys, multisite_keys, updated_profiles


def save_users(profiles):
    write_contacts_and_users_file(profiles)

    # Execute user connector save hooks
    hook_save(profiles)

    non_contact_keys, multisite_keys, updated_profiles = determine_save_users_data(profiles)

    # Write out the users serials
    serials = ""
    for user_id, user in updated_profiles.items():
        serials += '%s:%d\n' % (make_utf8(user_id), user.get('serial', 0))
    store.save_file('%s/auth.serials' % os.path.dirname(cmk.paths.htpasswd_file), serials)

    # Write user specific files
    for user_id, user in updated_profiles.items():
        user_dir = cmk.paths.var_dir + "/web/" + user_id.encode("utf-8")
        make_nagios_directory(user_dir)

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
        save_custom_attr(user_id, 'enforce_pw_change', str(int(user.get('enforce_pw_change', False))))
        save_custom_attr(user_id, 'last_pw_change', str(user.get('last_pw_change', int(time.time()))))

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
    profile_files_to_delete = [
        "automation.secret",
        "transids.mk",
        "serial.mk",
    ]
    dir = cmk.paths.var_dir + "/web"
    for user_dir in os.listdir(cmk.paths.var_dir + "/web"):
        if user_dir not in ['.', '..'] and user_dir.decode("utf-8") not in updated_profiles:
            entry = dir + "/" + user_dir
            if not os.path.isdir(entry):
                continue

            for to_delete in profile_files_to_delete:
                if os.path.exists(entry + '/' + to_delete):
                    os.unlink(entry + '/' + to_delete)

    # Release the lock to make other threads access possible again asap
    # This lock is set by load_users() only in the case something is expected
    # to be written (like during user syncs, wato, ...)
    release_lock(root_dir + "contacts.mk")

    # populate the users cache
    html.set_cache('users', updated_profiles)

    # Call the users_saved hook
    hooks.call("users-saved", updated_profiles)


def write_contacts_and_users_file(profiles, custom_default_config_dir = None):
    non_contact_keys, multisite_keys, updated_profiles = determine_save_users_data(profiles)

    if custom_default_config_dir:
        check_mk_config_dir  = "%s/conf.d/wato" %      custom_default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % custom_default_config_dir
    else:
        check_mk_config_dir  = "%s/conf.d/wato" %      cmk.paths.default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % cmk.paths.default_config_dir


    # Remove multisite keys in contacts.
    contacts = dict(
        e for e in
            [ (id, split_dict(user, non_contact_keys + non_contact_attributes(user.get('connector')), False))
               for (id, user)
               in updated_profiles.items() ])

    # Only allow explicitely defined attributes to be written to multisite config
    users = {}
    for uid, profile in updated_profiles.items():
        users[uid] = dict([ (p, val)
                            for p, val in profile.items()
                            if p in multisite_keys + multisite_attributes(profile.get('connector'))])


    # Check_MK's monitoring contacts
    store.save_to_mk_file("%s/%s" % (check_mk_config_dir, "contacts.mk"), "contacts", contacts)

    # GUI specific user configuration
    store.save_to_mk_file("%s/%s" % (multisite_config_dir, "users.mk"), "multisite_users", users)


def rewrite_users():
    users = load_users(lock=True)
    save_users(users)


def create_cmk_automation_user():
    secret = gen_id()

    users = load_users(lock=True)
    users["automation"] = {
        'alias'                 : u"Check_MK Automation - used for calling web services",
        'contactgroups'         : [],
        'automation_secret'     : secret,
        'password'              : encrypt_password(secret),
        'roles'                 : ['admin'],
        'locked'                : False,
        'serial'                : 0,
        'email'                 : '',
        'pager'                 : '',
        'notifications_enabled' : False,
        'language'              : 'en',
    }
    save_users(users)


def save_cached_profile(user_id, user, multisite_keys, non_contact_keys):
    # Only save contact AND multisite attributes to the profile. Not the
    # infos that are stored in the custom attribute files.
    cache = {}
    for key in user.keys():
        if key in multisite_keys or key not in non_contact_keys:
            cache[key] = user[key]

    config.save_user_file("cached_profile", cache, user=user_id)


def load_cached_profile():
    return config.user.load_file("cached_profile", None)


def contactgroups_of_user(user_id):
    user = load_cached_profile()
    if user == None:
        # No cached profile present. Load all users to get the users data
        user = load_users(lock=False)[user_id]

    return user.get("contactgroups", [])


def convert_idle_timeout(value):
    return value != "False" and int(value) or False


#.
#   .-Roles----------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# TODO: Use store. methods. Don't initialize strucutres on corrupted files.
def load_roles():
    # Fake builtin roles into user roles.
    builtin_role_names = {  # Default names for builtin roles
        "admin" : _("Administrator"),
        "user"  : _("Normal monitoring user"),
        "guest" : _("Guest user"),
    }
    roles = dict([(id, {
         "alias" : builtin_role_names.get(id, id),
         "permissions" : {}, # use default everywhere
         "builtin": True})
                  for id in config.builtin_role_ids ])

    filename = multisite_dir + "roles.mk"
    try:
        vars = { "roles" : roles }
        execfile(filename, vars, vars)
        # Make sure that "general." is prefixed to the general permissions
        # (due to a code change that converted "use" into "general.use", etc.
        for role in roles.values():
            for pname, pvalue in role["permissions"].items():
                if "." not in pname:
                    del role["permissions"][pname]
                    role["permissions"]["general." + pname] = pvalue

        # Reflect the data in the roles dict kept in the config module needed
        # for instant changes in current page while saving modified roles.
        # Otherwise the hooks would work with old data when using helper
        # functions from the config module
        config.roles.update(vars['roles'])

        return vars["roles"]

    except IOError:
        return roles # Use empty structure, not existing file is ok!
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") %
                          (filename, e))
        else:
            auth_logger.error('load_roles: Problem while loading roles (%s - %s). '
                     'Initializing structure...' % (filename, e))
        return roles

#.
#   .-Groups---------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
# TODO: Contact groups are fine here, but service / host groups?

# TODO: Use store. methods. Don't initialize strucutres on corrupted files.
def load_group_information():
    try:
        # Load group information from Check_MK world
        vars = {}
        for what in ["host", "service", "contact" ]:
            vars["define_%sgroups" % what] = {}

        filename = root_dir + "groups.mk"
        try:
            execfile(filename, vars, vars)
        except IOError:
            return {} # skip on not existing file

        # Now load information from the Web world
        multisite_vars = {}
        for what in ["host", "service", "contact" ]:
            multisite_vars["multisite_%sgroups" % what] = {}

        filename = multisite_dir + "groups.mk"
        try:
            execfile(filename, multisite_vars, multisite_vars)
        except IOError:
            pass

        # Merge information from Check_MK and Multisite worlds together
        groups = {}
        for what in ["host", "service", "contact" ]:
            groups[what] = {}
            for id, alias in vars['define_%sgroups' % what].items():
                groups[what][id] = {
                    'alias': alias
                }
                if id in multisite_vars['multisite_%sgroups' % what]:
                    groups[what][id].update(multisite_vars['multisite_%sgroups' % what][id])

        return groups

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") %
                          (filename, e))
        else:
            auth_logger.error('load_group_information: Problem while loading groups (%s - %s). '
                     'Initializing structure...' % (filename, e))
        return {}


class GroupChoice(DualListChoice):
    def __init__(self, what, **kwargs):
        DualListChoice.__init__(self, **kwargs)
        self.what = what
        self._choices = lambda: self.load_groups()

    def load_groups(self):
        all_groups = load_group_information()
        this_group = all_groups.get(self.what, {})
        return [ (k, t['alias'] and t['alias'] or k) for (k, t) in this_group.items() ]


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

def declare_custom_user_attrs():
    # First remove all previously registered custom host attributes
    for attr_name in user_attributes.keys():
        if attr_name not in builtin_user_attribute_names:
            del user_attributes[attr_name]

    # now declare the custom attributes
    for attr in config.wato_user_attrs:
        vs = globals()[attr['type']](title = attr['title'], help = attr['help'])
        declare_user_attribute(attr['name'], vs,
            user_editable = attr['user_editable'],
            show_in_table = attr.get('show_in_table', False),
            topic = attr.get('topic', 'personal'),
            add_custom_macro = attr.get('add_custom_macro', False )
        )

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

def load_connection_config():
    user_connections = []

    filename = multisite_dir + "user_connections.mk"
    if not os.path.exists(filename):
        return user_connections

    try:
        context = {
            "user_connections": user_connections,
        }
        execfile(filename, context, context)
        return context["user_connections"]

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") %
                          (filename, e))
        return user_connections


def save_connection_config(connections, base_dir=None):
    if not base_dir:
        base_dir = multisite_dir

    output  = "# Written by Multisite UserDB\n# encoding: utf-8\n\n"
    output += "user_connections = \\\n%s\n\n" % pprint.pformat(connections)

    make_nagios_directory(base_dir)
    store.save_file(os.path.join(base_dir, "user_connections.mk"), output)

#.
#   .--ConnectorAPI--------------------------------------------------------.
#   |     ____                            _              _    ____ ___     |
#   |    / ___|___  _ __  _ __   ___  ___| |_ ___  _ __ / \  |  _ \_ _|    |
#   |   | |   / _ \| '_ \| '_ \ / _ \/ __| __/ _ \| '__/ _ \ | |_) | |     |
#   |   | |__| (_) | | | | | | |  __/ (__| || (_) | | / ___ \|  __/| |     |
#   |    \____\___/|_| |_|_| |_|\___|\___|\__\___/|_|/_/   \_\_|  |___|    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Implements the base class for User Connector classes. It implements  |
#   | basic mechanisms and default methods which might/should be           |
#   | overridden by the specific connector classes.                        |
#   '----------------------------------------------------------------------'

# FIXME: How to declare methods/attributes forced to be overridden?
class UserConnector(object):
    def __init__(self, config):
        super(UserConnector, self).__init__()
        self._config = config

    @classmethod
    def type(self):
        return None

    # The string representing this connector to humans
    @classmethod
    def title(self):
        return None


    @classmethod
    def short_title(self):
        return _('htpasswd')

    #
    # USERDB API METHODS
    #

    @classmethod
    def migrate_config(self):
        pass

    # Optional: Hook function can be registered here to be executed
    # to validate a login issued by a user.
    # Gets parameters: username, password
    # Has to return either:
    #     '<user_id>' -> Login succeeded
    #     False       -> Login failed
    #     None        -> Unknown user
    def check_credentials(self, user_id, password):
        return None

    # Optional: Hook function can be registered here to be executed
    # to synchronize all users.
    def do_sync(self, add_to_changelog, only_username):
        pass

    # Optional: Tells whether or not the given user is currently
    # locked which would mean that he is not allowed to login.
    def is_locked(self, user_id):
        return False

    # Optional: Hook function can be registered here to be executed
    # on each call to the multisite cron job page which is normally
    # executed once a minute.
    def on_cron_job(self):
        pass

    # Optional: Hook function can be registered here to be xecuted
    # to save all users.
    def save_users(self, users):
        pass

    # List of user attributes locked for all users attached to this
    # connection. Those locked attributes are read-only in WATO.
    def locked_attributes(self):
        return []

    def multisite_attributes(self):
        return []

    def non_contact_attributes(self):
        return []


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
        if result not in [ False, None ]:
            username = result
            if type(username) not in [ str, unicode ]:
                raise MKInternalError(_("The username returned by the %s "
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
                return False # The account is locked

            return result

        elif result == False:
            return result


def show_exception(connection_id, title, e, debug=True):
    html.show_error(
        "<b>" + connection_id + ' - ' + title + "</b>"
        "<pre>%s</pre>" % (debug and traceback.format_exc() or e)
    )


# Hook function can be registered here to be executed to synchronize all users.
# Is called on:
#   a) before rendering the user management page in WATO
#   b) a user is created during login (only for this user)
#   c) Before activating the changes in WATO
def hook_sync(connection_id = None, add_to_changelog = False, only_username = None, raise_exc = False):
    if connection_id:
        connections = [ (connection_id, get_connection(connection_id)) ]
    else:
        connections = active_connections()

    no_errors = True
    for connection_id, connection in connections:
        try:
            connection.do_sync(add_to_changelog, only_username)
        except MKLDAPException, e:
            if raise_exc:
                raise
            show_exception(connection_id, _("Error during sync"), e, debug=config.debug)
            no_errors = False
        except Exception, e:
            if raise_exc:
                raise
            show_exception(connection_id, _("Error during sync"), e)
            no_errors = False
    return no_errors

# Hook function can be registered here to be executed during saving of the
# new user construct
def hook_save(users):
    for connection_id, connection in active_connections():
        try:
            connection.save_users(users)
        except Exception, e:
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
    auth_php = cmk.paths.var_dir + '/wato/auth/auth.php'
    if not os.path.exists(auth_php) or os.path.getsize(auth_php) == 0:
        create_auth_file("page_hook", load_users())

    # Create initial auth.serials file, same issue as auth.php above
    serials_file = '%s/auth.serials' % os.path.dirname(cmk.paths.htpasswd_file)
    if not os.path.exists(serials_file) or os.path.getsize(serials_file) == 0:
        save_users(load_users(lock = True))


# Hook function can be registered here to execute actions on a "regular" base without
# user triggered action. This hook is called on each page load.
# Catch all exceptions and log them to apache error log. Let exceptions raise trough
# when debug mode is enabled.
def execute_userdb_job():
    if not userdb_sync_job_enabled():
        return

    for connection_id, connection in active_connections():
        try:
            connection.on_cron_job()
        except:
            if config.debug:
                raise
            else:
                auth_logger.error('Exception (%s, userdb_job): %s' %
                                  (connection_id, traceback.format_exc()))

    general_userdb_job()


# Legacy option config.userdb_automatic_sync defaulted to "master".
# Can be: None: (no sync), "all": all sites sync, "master": only master site sync
# Take that option into account for compatibility reasons.
# For remote sites in distributed setups, the default is to do no sync.
def user_sync_default_config(site_name):
    global_user_sync = transform_userdb_automatic_sync(config.userdb_automatic_sync)
    if global_user_sync == "master":
        import wato # FIXME: Cleanup!
        if config.site_is_local(site_name) and not wato.is_wato_slave_site():
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

    if cfg == None:
        return False # not enabled at all

    import wato # FIXME: Cleanup!
    if cfg == "master" and wato.is_wato_slave_site():
        return False

    return True


def ajax_sync():
    try:
        hook_sync(add_to_changelog = False, raise_exc = True)
        html.write('OK\n')
    except Exception, e:
        log_exception()
        if config.debug:
            raise
        else:
            html.write('ERROR %s\n' % e)
