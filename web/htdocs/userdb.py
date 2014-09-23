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
builtin_user_attribute_names = []

# Load all userdb plugins
def load_plugins():
    global user_attributes
    global multisite_user_connectors

    # Do not cache the custom user attributes. They can be created by the user
    # during runtime, means they need to be loaded during each page request.
    # But delete the old definitions before to also apply removals of attributes
    if user_attributes:
        for attr_name in user_attributes.keys():
            if attr_name not in builtin_user_attribute_names:
                del user_attributes[attr_name]
        declare_custom_user_attrs()

    global loaded_with_language
    if loaded_with_language == current_language:
        return

    # declare & initialize global vars
    user_attributes = {}
    multisite_user_connectors = []

    load_web_plugins("userdb", globals())

    global builtin_user_attribute_names
    builtin_user_attribute_names = user_attributes.keys()
    declare_custom_user_attrs()

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
    users = load_users(lock = True)
    if username in users:
        return # User exists. Nothing to do...

    users[username] = new_user_template(connector_id)
    save_users(users)

    # Call the sync function for this new user
    hook_sync(connector_id = connector_id, only_username = username)

# FIXME: Can we improve this easily? Would be nice not to have to call "load_users".
# Maybe a directory listing of profiles or a list of a small file would perform better
# than having to load the users, contacts etc. during each http request to multisite
def user_exists(username):
    return username in load_users().keys()

def user_locked(username):
    users = load_users()
    return users[username].get('locked', False)

def update_user_access_time(username):
    if not config.save_user_access_times:
        return
    save_custom_attr(username, 'last_seen', repr(time.time()))

def on_succeeded_login(username):
    num_failed = load_custom_attr(username, 'num_failed', saveint)
    if num_failed != None and num_failed != 0:
        save_custom_attr(username, 'num_failed', '0')

    update_user_access_time(username)

def on_failed_login(username):
    users = load_users(lock = True)
    if username in users:
        if "num_failed" in users[username]:
            users[username]["num_failed"] += 1
        else:
            users[username]["num_failed"] = 1

        if config.lock_on_logon_failures:
            if users[username]["num_failed"] >= config.lock_on_logon_failures:
                users[username]["locked"] = True

        save_users(users)

root_dir      = defaults.check_mk_configdir + "/wato/"
multisite_dir = defaults.default_config_dir + "/multisite.d/wato/"

#.
#   .--Users---------------------------------------------------------------.
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
        # Make sure that the file exists without modifying it, *if* it exists
        # to be able to lock and realease the file properly.
        # Note: the lock will be released on next save_users() call or at
        #       end of page request automatically.
        file(filename, "a")
        aquire_lock(filename)

    if html.is_cached('users'):
        return html.get_cached('users')

    # First load monitoring contacts from Check_MK's world. If this is
    # the first time, then the file will be empty, which is no problem.
    # Execfile will the simply leave contacts = {} unchanged.
    try:
        vars = { "contacts" : {} }
        execfile(filename, vars, vars)
        contacts = vars["contacts"]
    except IOError:
        contacts = {} # a not existing file is ok, start with empty data
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
    try:
        vars = { "multisite_users" : {} }
        execfile(filename, vars, vars)
        users = vars["multisite_users"]
    except IOError:
        users = {} # not existing is ok -> empty structure
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_users: Problem while loading users (%s - %s). '
                     'Initializing structure...' % (filename, e))
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

    def readlines(f):
        try:
            return file(f)
        except IOError:
            return []

    filename = defaults.htpasswd_file
    for line in readlines(filename):
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
    for line in readlines(serials_file):
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

            # read special values from own files
            if id in result:
                num_failed = load_custom_attr(d, 'num_failed', saveint)
                if num_failed != None:
                    result[id]['num_failed'] = num_failed

                last_seen = load_custom_attr(d, 'last_seen',  savefloat)
                if last_seen != None:
                    result[id]['last_seen'] = last_seen

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

def load_custom_attr(userid, key, conv_func, default = None):
    basedir = defaults.var_dir + "/web/" + userid
    try:
        return conv_func(file(basedir + '/' + key + '.mk').read().strip())
    except IOError:
        return default

def save_custom_attr(userid, key, val):
    basedir = defaults.var_dir + "/web/" + userid
    make_nagios_directory(basedir)
    create_user_file('%s/%s.mk' % (basedir, key), 'w').write('%s\n' % val)

def get_online_user_ids():
    online_threshold = time.time() - config.user_online_maxage
    users = []
    for user_id, user in load_users(lock = False).items():
        if user.get('last_seen', 0) >= online_threshold:
            users.append(user_id)
    return users

def split_dict(d, keylist, positive):
    return dict([(k,v) for (k,v) in d.items() if (k in keylist) == positive])

def save_users(profiles):

    # Add custom macros
    core_custom_macros =  [ k for k,o in user_attributes.items() if o.get('add_custom_macro') ]
    for user in profiles.keys():
        for macro in core_custom_macros:
            if profiles[user].get(macro):
                profiles[user]['_'+macro] = profiles[user][macro]

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
        "num_failed",
        "last_seen",
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


    # Check_MK's monitoring contacts
    filename = root_dir + "contacts.mk.new"
    out = create_user_file(filename, "w")
    out.write("# Written by Multisite UserDB\n# encoding: utf-8\n\n")
    out.write("contacts.update(\n%s\n)\n" % pprint.pformat(contacts))
    out.close()
    os.rename(filename, filename[:-4])

    # Users with passwords for Multisite
    filename = multisite_dir + "users.mk.new"
    make_nagios_directory(multisite_dir)
    out = create_user_file(filename, "w")
    out.write("# Written by Multisite UserDB\n# encoding: utf-8\n\n")
    out.write("multisite_users = \\\n%s\n" % pprint.pformat(users))
    out.close()
    os.rename(filename, filename[:-4])

    # Execute user connector save hooks
    hook_save(profiles)

    # Write out the users serials
    serials_file = '%s/auth.serials.new' % os.path.dirname(defaults.htpasswd_file)
    rename_file = True
    try:
        out = create_user_file(serials_file, "w")
    except:
        rename_file = False
        out = create_user_file(serials_file[:-4], "w")

    def encode_utf8(value):
        if type(value) == unicode:
            value = value.encode("utf-8")
        return value

    for user_id, user in profiles.items():
        out.write('%s:%d\n' % (encode_utf8(user_id), user.get('serial', 0)))
    out.close()
    if rename_file:
        os.rename(serials_file, serials_file[:-4])

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
        save_custom_attr(id, 'serial', str(user.get('serial', 0)))

        # Write out the users number of failed login
        save_custom_attr(id, 'num_failed', str(user.get('num_failed', 0)))

        # Write out the last seent time
        if 'last_seen' in user:
            save_custom_attr(id, 'last_seen', repr(user['last_seen']))

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

    # Release the lock to make other threads access possible again asap
    # This lock is set by load_users() only in the case something is expected
    # to be written (like during user syncs, wato, ...)
    release_lock(root_dir + "contacts.mk")

    # populate the users cache
    html.set_cache('users', profiles)

    # Call the users_saved hook
    hooks.call("users-saved", profiles)

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
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_roles: Problem while loading roles (%s - %s). '
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
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_group_information: Problem while loading groups (%s - %s). '
                     'Initializing structure...' % (filename, e))
        return {}

#.
#   .--Custom-Attrs.-------------------------------------------------------.
#   |   ____          _                          _   _   _                 |
#   |  / ___|   _ ___| |_ ___  _ __ ___         / \ | |_| |_ _ __ ___      |
#   | | |  | | | / __| __/ _ \| '_ ` _ \ _____ / _ \| __| __| '__/ __|     |
#   | | |__| |_| \__ \ || (_) | | | | | |_____/ ___ \ |_| |_| |  \__ \_    |
#   |  \____\__,_|___/\__\___/|_| |_| |_|    /_/   \_\__|\__|_|  |___(_)   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mange custom attributes of users (in future hosts etc.)              |
#   '----------------------------------------------------------------------'

def load_custom_attrs():
    try:
        filename = multisite_dir + "custom_attrs.mk"
        if not os.path.exists(filename):
            return {}

        vars = {
            'wato_user_attrs': [],
        }
        execfile(filename, vars, vars)

        attrs = {}
        for what in [ "user" ]:
            attrs[what] = vars.get("wato_%s_attrs" % what, [])
        return attrs

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        else:
            html.log('load_custom_attrs: Problem while loading custom attributes (%s - %s). '
                     'Initializing structure...' % (filename, e))
        return {}

def declare_custom_user_attrs():
    all_attrs = load_custom_attrs()
    attrs = all_attrs.setdefault('user', [])
    for attr in attrs:
        vs = globals()[attr['type']](title = attr['title'], help = attr['help'])
        declare_user_attribute(attr['name'], vs,
            user_editable = attr['user_editable'],
            show_in_table = attr.get('show_in_table', False),
            topic = attr.get('topic', 'personal'),
            add_custom_macro = attr.get('add_custom_macro', False )
        )

#.
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
#   c) Before activating the changes in WATO
def hook_sync(connector_id = None, add_to_changelog = False, only_username = None, raise_exc = False):
    if connector_id:
        connectors = [ get_connector(connector_id) ]
    else:
        connectors = enabled_connectors()

    no_errors = True
    for connector in connectors:
        handler = connector.get('sync', None)
        if handler:
            try:
                handler(add_to_changelog, only_username)
            except MKLDAPException, e:
                if raise_exc:
                    raise
                if config.debug:
                    import traceback
                    html.show_error(
                        "<h3>" + _("Error during sync") + "</h3>"
                        "<pre>%s</pre>" % (traceback.format_exc())
                    )
                else:
                    html.show_error(
                        "<h3>" + _("Error during sync") + "</h3>"
                        "<pre>%s</pre>" % (e)
                    )
                no_errors = False
            except:
                if raise_exc:
                    raise
                import traceback
                html.show_error(
                    "<h3>" + _("Error during sync") + "</h3>"
                    "<pre>%s</pre>" % (traceback.format_exc())
                )
                no_errors = False
    return no_errors

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
                    "<h3>" + _("Error during saving") + "</h3>"
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
        save_users(load_users(lock = True))

# Hook function can be registered here to execute actions on a "regular" base without
# user triggered action. This hook is called on each page load.
# Catch all exceptions and log them to apache error log. Let exceptions raise trough
# when debug mode is enabled.
def hook_page():
    if 'page' not in config.userdb_automatic_sync:
        return

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

def ajax_sync():
    try:
        hook_sync(add_to_changelog = False, raise_exc = True)
        html.write('OK\n')
    except Exception, e:
        if config.debug:
            raise
        else:
            html.write('ERROR %s\n' % e)
