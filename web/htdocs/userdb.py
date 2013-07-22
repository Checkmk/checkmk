#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import config, defaults, hooks
from lib import *
import time, os, pprint, shutil
from valuespec import *

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Custom user attributes
user_attributes = {}

# Load all login plugins
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    # declare & initialize global vars
    global multisite_user_connectors ; multisite_user_connectors = []

    load_web_plugins("userdb", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language


def list_user_connectors():
    return [ (c['id'], c['title']) for c in multisite_user_connectors ]

def connector_enabled(connector_id):
    return connector_id in config.user_connectors

def enabled_connectors():
    connectors = []
    for connector in multisite_user_connectors:
        if connector['id'] in config.user_connectors:
            connectors.append(connector)
    return connectors

def get_connector_id(connector_id):
    if connector_id is None:
        connector_id = 'htpasswd'
    return connector_id

# Returns the connector dictionary of the given id
def get_connector(connector_id):
    connector_id = get_connector_id(connector_id)
    for connector in enabled_connectors():
        if connector['id'] == connector_id:
            return connector
    return {}

# Returns a list of locked attributes
def locked_attributes(connector_id):
    connector = get_connector(connector_id)
    return connector.get('locked_attributes', lambda: [])()

# Returns a list of multisite attributes
def multisite_attributes(connector_id):
    connector = get_connector(connector_id)
    return connector.get('multisite_attributes', lambda: [])()

# Returns a list of non contact attributes
def non_contact_attributes(connector_id):
    connector = get_connector(connector_id)
    return connector.get('non_contact_attributes', lambda: [])()

def new_user_template(connector_id):
    new_user = {
        'serial':        0,
        'connector':     connector_id,
    }

    # Apply the default user profile
    new_user.update(config.default_user_profile)
    return new_user

def create_non_existing_user(connector_id, username):
    users = load_users()
    if username in users:
        return # User exists. Nothing to do...

    users[username] = new_user_template(connector_id)
    save_users(users)

    # Call the sync function for this new user
    hook_sync(connector_id = connector_id, only_username = username)

def user_locked(username):
    users = load_users()
    return users[username].get('locked', False)



root_dir      = defaults.check_mk_configdir + "/wato/"
multisite_dir = defaults.default_config_dir + "/multisite.d/wato/"

#   .--Users---------------------------------------------------------------.
#   |                       _   _                                          |
#   |                      | | | |___  ___ _ __ ___                        |
#   |                      | | | / __|/ _ \ '__/ __|                       |
#   |                      | |_| \__ \  __/ |  \__ \                       |
#   |                       \___/|___/\___|_|  |___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def get_user_attributes():
    return user_attributes.items()

def reset_user_attributes():
    global user_attributes
    user_attributes = {}

def load_users():
    filename = root_dir + "contacts.mk"

    # Make sure that the file exists without modifying it, *if* it exists.
    # Note the lock will be released at end of page request automatically.
    file(filename, "a")
    aquire_lock(filename)

    # First load monitoring contacts from Check_MK's world. If this is
    # the first time, then the file will be empty, which is no problem.
    # Execfile will the simply leave contacts = {} unchanged.
    try:
        vars = { "contacts" : {} }
        execfile(filename, vars, vars)
        contacts = vars["contacts"]
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_users: Problem while loading contacts (%s - %s). '
                     'Initializing structure...' % (filename, e))
        contacts = {}

    # Now add information about users from the Web world
    filename = multisite_dir + "users.mk"
    if os.path.exists(filename):
        try:
            vars = { "multisite_users" : {} }
            execfile(filename, vars, vars)
            users = vars["multisite_users"]
        except Exception, e:
            if config.debug:
                raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                              (filename, e)))
            else:
                html.log('load_users: Problem while loading users (%s - %s). '
                         'Initializing structure...' % (filename, e))
            users = {}
    else:
        users = {}

    # Merge them together. Monitoring users not known to Multisite
    # will be added later as normal users.
    result = {}
    for id, user in users.items():
        profile = contacts.get(id, {})
        profile.update(user)
        result[id] = profile

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

    filename = defaults.htpasswd_file
    if os.path.exists(filename):
        for line in file(filename):
            line = line.strip()
            if ':' in line:
                id, password = line.strip().split(":")[:2]
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
    serials_file = '%s/auth.serials' % os.path.dirname(defaults.htpasswd_file)
    if os.path.exists(serials_file):
        for line in file(serials_file):
            line = line.strip()
            if ':' in line:
                user_id, serial = line.split(':')[:2]
                if user_id in result:
                    result[user_id]['serial'] = saveint(serial)

    # Now read the user specific files
    dir = defaults.var_dir + "/web/"
    for d in os.listdir(dir):
        if d[0] != '.':
            id = d

            # read automation secrets and add them to existing
            # users or create new users automatically
            secret_file = dir + d + "/automation.secret"
            if os.path.exists(secret_file):
                secret = file(secret_file).read().strip()
                if id in result:
                    result[id]["automation_secret"] = secret
                else:
                    result[id] = {
                        "roles" : ["guest"],
                        "automation_secret" : secret,
                    }

    return result

def split_dict(d, keylist, positive):
    return dict([(k,v) for (k,v) in d.items() if (k in keylist) == positive])


def save_users(profiles):
    custom_values = user_attributes.keys()

    # Keys not to put into contact definitions for Check_MK
    non_contact_keys = [
        "roles",
        "password",
        "locked",
        "automation_secret",
        "language",
        "serial",
        "connector",
    ] + custom_values

    # Keys to put into multisite configuration
    multisite_keys   = [
        "roles",
        "locked",
        "automation_secret",
        "alias",
        "language",
        "connector",
    ] + custom_values

    # Remove multisite keys in contacts.
    contacts = dict(
        e for e in
            [ (id, split_dict(user, non_contact_keys + non_contact_attributes(user.get('connector')), False))
               for (id, user)
               in profiles.items() ])

    # Only allow explicitely defined attributes to be written to multisite config
    users = {}
    for uid, profile in profiles.items():
        users[uid] = dict([ (p, val)
                            for p, val in profile.items()
                            if p in multisite_keys + multisite_attributes(profile.get('connector'))])

    filename = root_dir + "contacts.mk"

    # Check_MK's monitoring contacts
    out = create_user_file(filename, "w")
    out.write("# Written by Multisite UserDB\n# encoding: utf-8\n\n")
    out.write("contacts.update(\n%s\n)\n" % pprint.pformat(contacts))
    out.close()

    # Users with passwords for Multisite
    make_nagios_directory(multisite_dir)
    filename = multisite_dir + "users.mk"
    out = create_user_file(filename, "w")
    out.write("# Written by Multisite UserDB\n# encoding: utf-8\n\n")
    out.write("multisite_users = \\\n%s\n" % pprint.pformat(users))
    out.close()

    # Execute user connector save hooks
    hook_save(profiles)

    # Write out the users serials
    serials_file = '%s/auth.serials' % os.path.dirname(defaults.htpasswd_file)
    out = create_user_file(serials_file, "w")
    for user_id, user in profiles.items():
        out.write('%s:%d\n' % (user_id, user.get('serial', 0)))
    out.close()

    # Write user specific files
    for id, user in profiles.items():
        user_dir = defaults.var_dir + "/web/" + id
        make_nagios_directory(user_dir)

        # authentication secret for local processes
        auth_file = user_dir + "/automation.secret"
        if "automation_secret" in user:
            create_user_file(auth_file, "w").write("%s\n" % user["automation_secret"])
        elif os.path.exists(auth_file):
            os.remove(auth_file)

        # Write out the users serial
        serial_file = user_dir + '/serial.mk'
        create_user_file(serial_file, 'w').write('%d\n' % user.get('serial', 0))

    # Remove settings directories of non-existant users.
    # Beware: we removed this since it leads to violent destructions
    # if the user database is out of the scope of Check_MK. This is
    # e.g. the case, if mod_ldap is used for user authentication.
    # dir = defaults.var_dir + "/web"
    # for e in os.listdir(dir):
    #     if e not in ['.', '..'] and e not in profiles:
    #         entry = dir + "/" + e
    #         if os.path.isdir(entry):
    #             shutil.rmtree(entry)
    # But for the automation.secret this is ok, since automation users are not
    # created by other sources in common cases
    dir = defaults.var_dir + "/web"
    for user_dir in os.listdir(defaults.var_dir + "/web"):
        if user_dir not in ['.', '..'] and user_dir not in profiles:
            entry = dir + "/" + user_dir
            if os.path.isdir(entry) and os.path.exists(entry + '/automation.secret'):
                os.unlink(entry + '/automation.secret')

    # Call the users_saved hook
    hooks.call("users-saved", users)

#   .-Roles----------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

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
    if not os.path.exists(filename):
        return roles

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

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_roles: Problem while loading roles (%s - %s). '
                     'Initializing structure...' % (filename, e))
        return roles

#   .-Groups---------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+

def load_group_information():
    try:
        filename = root_dir + "groups.mk"
        if not os.path.exists(filename):
            return {}

        vars = {}
        for what in ["host", "service", "contact" ]:
            vars["define_%sgroups" % what] = {}

        execfile(filename, vars, vars)
        groups = {}
        for what in ["host", "service", "contact" ]:
            groups[what] = vars.get("define_%sgroups" % what, {})
        return groups

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_group_information: Problem while loading groups (%s - %s). '
                     'Initializing structure...' % (filename, e))
        return {}

#   .----------------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# This hook is called to validate the login credentials provided by a user
def hook_login(username, password):
    for connector in enabled_connectors():
        handler = connector.get('login', None)
        if not handler:
            continue

        result = handler(username, password)
        # None        -> User unknown, means continue with other connectors
        # '<user_id>' -> success
        # False       -> failed
        if result not in [ False, None ]:
            username = result
            if type(username) != str:
                raise MKInternalError(_("The username returned by the %s "
                    "connector is not of type string (%r).") % (connector['id'], username))
            # Check wether or not the user exists (and maybe create it)
            create_non_existing_user(connector['id'], username)

            # Now, after successfull login (and optional user account
            # creation), check wether or not the user is locked.
            # In e.g. htpasswd connector this is checked by validating the
            # password against the hash in the htpasswd file prefixed with
            # a "!". But when using other conectors it might be neccessary
            # to validate the user "locked" attribute.
            lock_handler = connector.get('locked', None)
            if lock_handler and lock_handler(username):
                return False # The account is locked

            return result

        elif result == False:
            return result

# Hook function can be registered here to be executed to synchronize all users.
# Is called on:
#   a) before rendering the user management page in WATO
#   b) a user is created during login (only for this user)
def hook_sync(connector_id = None, add_to_changelog = False, only_username = None):
    if connector_id:
        connectors = [ get_connector(connector_id) ]
    else:
        connectors = enabled_connectors()

    for connector in connectors:
        handler = connector.get('sync', None)
        if handler:
            try:
                handler(add_to_changelog, only_username)
            except MKLDAPException, e:
                if config.debug:
                    import traceback
                    html.show_error(
                        "<h3>" + _("Error executing sync hook") + "</h3>"
                        "<pre>%s</pre>" % (traceback.format_exc())
                    )
                else:
                    html.show_error(
                        "<h3>" + _("Error executing sync hook") + "</h3>"
                        "<pre>%s</pre>" % (e)
                    )
            except:
                import traceback
                html.show_error(
                    "<h3>" + _("Error executing sync hook") + "</h3>"
                    "<pre>%s</pre>" % (traceback.format_exc())
                )

# Hook function can be registered here to be executed during saving of the
# new user construct
def hook_save(users):
    for connector in enabled_connectors():
        handler = connector.get('save', None)
        if not handler:
            continue
        try:
            handler(users)
        except:
            if config.debug:
                import traceback
                html.show_error(
                    "<h3>" + _("Error executing sync hook") + "</h3>"
                    "<pre>%s</pre>" % (traceback.format_exc())
                )
            else:
                raise

# This function registers general stuff, which is independet of the single
# connectors to each page load. It is exectued AFTER all other page hooks.
def general_page_hook():
    # Working around the problem that the auth.php file needed for multisite based
    # authorization of external addons might not exist when setting up a new installation
    # We assume: Each user must visit this login page before using the multisite based
    #            authorization. So we can easily create the file here if it is missing.
    # This is a good place to replace old api based files in the future.
    auth_php = defaults.var_dir + '/wato/auth/auth.php'
    if not os.path.exists(auth_php) or os.path.getsize(auth_php) == 0:
        create_auth_file("page_hook", load_users())

    # Create initial auth.serials file, same issue as auth.php above
    serials_file = '%s/auth.serials' % os.path.dirname(defaults.htpasswd_file)
    if not os.path.exists(serials_file) or os.path.getsize(serials_file) == 0:
        save_users(load_users())

# Hook function can be registered here to execute actions on a "regular" base without
# user triggered action. This hook is called on each page load.
# Catch all exceptions and log them to apache error log. Let exceptions raise trough
# when debug mode is enabled.
def hook_page():
    for connector in enabled_connectors():
        handler = connector.get('page', None)
        if not handler:
            continue
        try:
            handler()
        except:
            if config.debug:
                raise
            else:
                import traceback
                html.log('Exception (%s, page handler): %s' %
                            (connector['id'], traceback.format_exc()))

    general_page_hook()
