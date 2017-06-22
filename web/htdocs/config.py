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

import os, pprint, glob
import i18n
import log
from lib import *
import cmk.paths

#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Declarations of global variables and constants                      |
#   '----------------------------------------------------------------------'

multisite_users = {}
admin_users     = []

# hard coded in various permissions
builtin_role_ids = [ "user", "admin", "guest" ]

# Base directory of dynamic configuration
config_dir = cmk.paths.var_dir + "/web"

# Detect modification in configuration
modification_timestamps = []

# Global table of available permissions. Plugins may add their own
# permissions by calling declare_permission()
permissions_by_name              = {}
permissions_by_order             = []
permission_sections              = {}
permission_declaration_functions = []

# Constants for BI
ALL_HOSTS = '(.*)'
HOST_STATE = ('__HOST_STATE__',)
HIDDEN = ('__HIDDEN__',)
class FOREACH_HOST(object): pass
class FOREACH_CHILD(object): pass
class FOREACH_CHILD_WITH(object): pass
class FOREACH_PARENT(object): pass
class FOREACH_SERVICE(object): pass
class REMAINING(object): pass
class DISABLED(object): pass
class HARD_STATES(object): pass
class DT_AGGR_WARN(object): pass

# Has to be declared here once since the functions can be assigned in
# bi.py and also in multisite.mk. "Double" declarations are no problem
# here since this is a dict (List objects have problems with duplicate
# definitions).
aggregation_functions = {}


#.
#   .--Functions-----------------------------------------------------------.
#   |             _____                 _   _                              |
#   |            |  ___|   _ _ __   ___| |_(_) ___  _ __  ___              |
#   |            | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|             |
#   |            |  _|| |_| | | | | (__| |_| | (_) | | | \__ \             |
#   |            |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper functions for config parsing, login, etc.                    |
#   '----------------------------------------------------------------------'


def initialize():
    clear_user_login()
    load_config()
    log.set_log_levels(log_levels)


# Read in a multisite.d/*.mk file
def include(filename):
    if not filename.startswith("/"):
        filename = cmk.paths.default_config_dir + "/" + filename

    # Config file is obligatory. An empty example is installed
    # during setup.sh. Better signal an error then simply ignore
    # Absence.
    try:
        lm = os.stat(filename).st_mtime
        execfile(filename, globals(), globals())
        modification_timestamps.append((filename, lm))
    except Exception, e:
        raise MKConfigError(_("Cannot read configuration file %s: %s:") % (filename, e))

# Load multisite.mk and all files in multisite.d/. This will happen
# for *each* HTTP request.
# FIXME: Optimize this to cache the config etc. until either the config files or plugins
# have changed. We could make this being cached for multiple requests just like the
# plugins of other modules. This may save significant time in case of small requests like
# the graph ajax page or similar.
def load_config():
    global modification_timestamps, sites
    modification_timestamps = []

    # Set default values for all user-changable configuration settings
    load_plugins(True)

    # Initialze sites with default site configuration. Need to do it here to
    # override possibly deleted sites
    sites = default_single_site_configuration()

    # First load main file
    include("multisite.mk")

    # Load also recursively all files below multisite.d
    conf_dir = cmk.paths.default_config_dir + "/multisite.d"
    filelist = []
    if os.path.isdir(conf_dir):
        for root, dirs, files in os.walk(conf_dir):
            for filename in files:
                if filename.endswith(".mk"):
                    filelist.append(root + "/" + filename)

    filelist.sort()
    for p in filelist:
        include(p)

    # Prevent problem when user has deleted all sites from his configuration
    # and sites is {}. We assume a default single site configuration in
    # that case.
    if not sites:
        sites = default_single_site_configuration()


def reporting_available():
    try:
        # Check the existance of one arbitrary config variable from the
        # reporting module
        reporting_filename
        return True
    except:
        return False


def combined_graphs_available():
    try:
        have_combined_graphs
        return True
    except:
        return False


def hide_language(lang):
    return lang in hide_languages


def get_language(default=None):
    if default == None:
        return default_language
    else:
        return default


#.
#   .--Permissions---------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declarations of permissions and roles                                |
#   '----------------------------------------------------------------------'

def declare_permission(name, title, description, defaults):
    perm = {
        "name"        : name,
        "title"       : title,
        "description" : description,
        "defaults"    : defaults,
    }

    # Detect if this permission has already been declared before
    # The dict value is replaced automatically but the list value
    # to be replaced -> INPLACE!
    # FIXME: permissions_by_order is bad. Remove this and add a "sort"
    # attribute to the permissions_by_name dict. This would be much cleaner.
    replaced = False
    for index, test_perm in enumerate(permissions_by_order):
        if test_perm['name'] == perm['name']:
            permissions_by_order[index] = perm
            replaced = True

    if not replaced:
        permissions_by_order.append(perm)

    permissions_by_name[name] = perm


def declare_permission_section(name, title, prio = 0, do_sort = False):
    # Prio can be a number which is used for sorting. Higher numbers will
    # be listed first, e.g. in the edit dialogs
    permission_sections[name] = (prio, title, do_sort)


# Some module have a non-fixed list of permissions. For example for
# each user defined view there is also a permission. This list is
# not known at the time of the loading of the module - though. For
# that purpose module can register functions. These functions should
# just call declare_permission(). They are being called in the correct
# situations.
def declare_dynamic_permissions(func):
    permission_declaration_functions.append(func)


# This function needs to be called by all code that needs access
# to possible dynamic permissions
def load_dynamic_permissions():
    for func in permission_declaration_functions:
        func()


def permission_exists(pname):
    return pname in permissions_by_name


def get_role_permissions():
    role_permissions = {}
    # Loop all permissions
    # and for each permission loop all roles
    # and check whether it has the permission or not

    roleids = roles.keys()
    for perm in permissions_by_order:
        for role_id in roleids:
            if not role_id in role_permissions:
                role_permissions[role_id] = []

            if _may_with_roles([role_id], perm['name']):
                role_permissions[role_id].append(perm['name'])
    return role_permissions


def _may_with_roles(some_role_ids, pname):
    # If at least one of the given roles has this permission, it's fine
    for role_id in some_role_ids:
        role = roles[role_id]

        he_may = role.get("permissions", {}).get(pname)
        # Handle compatibility with permissions without "general." that
        # users might have saved in their own custom roles.
        if he_may == None and pname.startswith("general."):
            he_may = role.get("permissions", {}).get(pname[8:])

        if he_may == None: # not explicitely listed -> take defaults
            if "basedon" in role:
                base_role_id = role["basedon"]
            else:
                base_role_id = role_id
            if pname not in permissions_by_name:
                return False # Permission unknown. Assume False. Functionality might be missing
            perm = permissions_by_name[pname]
            he_may = base_role_id in perm["defaults"]
        if he_may:
            return True
    return False



#.
#   .--User Login----------------------------------------------------------.
#   |           _   _                 _                _                   |
#   |          | | | |___  ___ _ __  | |    ___   __ _(_)_ __              |
#   |          | | | / __|/ _ \ '__| | |   / _ \ / _` | | '_ \             |
#   |          | |_| \__ \  __/ |    | |__| (_) | (_| | | | | |            |
#   |           \___/|___/\___|_|    |_____\___/ \__, |_|_| |_|            |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   | Managing the currently logged in user                                |
#   '----------------------------------------------------------------------'
# TODO: Shouldn't this be moved to e.g. login.py or userdb.py?

# This objects intention is currently only to handle the currently logged in user after authentication.
# But maybe this can be used for managing all user objects in future.
# TODO: Cleanup accesses to module global vars and functions
class LoggedInUser(object):
    def __init__(self, user_id):
        self.id = user_id

        self._load_confdir()
        self._load_roles()
        self._load_attributes()
        self._load_permissions()
        self._load_site_config()


    # TODO: Clean up that baserole_* stuff?
    def _load_roles(self):
        # Determine the roles of the user. If the user is listed in
        # users, admin_users or guest_users in multisite.mk then we
        # give him the according roles. If the user has an explicit
        # profile in multisite_users (e.g. due to WATO), we rather
        # use that profile. Remaining (unknown) users get the default_user_role.
        # That can be set to None -> User has no permissions at all.
        self.role_ids = self._gather_roles()

        # Get base roles (admin/user/guest)
        self._load_base_roles()

        # Get best base roles and use as "the" role of the user
        if "admin" in self.baserole_ids:
            self.baserole_id = "admin"
        elif "user" in self.baserole_ids:
            self.baserole_id = "user"
        else:
            self.baserole_id = "guest"


    def _gather_roles(self):
        return roles_of_user(self.id)


    def _load_base_roles(self):
        base_roles = set([])
        for r in self.role_ids:
            if r in builtin_role_ids:
                base_roles.add(r)
            else:
                base_roles.add(roles[r]["basedon"])

        self.baserole_ids = list(base_roles)


    def _load_attributes(self):
        self.attributes = self.load_file("cached_profile", None)
        if self.attributes == None:
            if self.id in multisite_users:
                self.attributes = multisite_users[self.id]
            else:
                self.attributes = {
                    "roles" : self.role_ids,
                }

        self.alias = self.attributes.get("alias", self.id)
        self.email = self.attributes.get("email", self.id)


    def _load_permissions(self):
        # Prepare cache of already computed permissions
        # Make sure, admin can restore permissions in any case!
        if self.id in admin_users:
            self.permissions = {
                "general.use" : True, # use Multisite
                "wato.use"    : True, # enter WATO
                "wato.edit"   : True, # make changes in WATO...
                "wato.users"  : True, # ... with access to user management
            }
        else:
            self.permissions = {}


    def _load_confdir(self):
        self.confdir = config_dir + "/" + self.id.encode("utf-8")
        make_nagios_directory(self.confdir)


    def _load_site_config(self):
        self.siteconf = self.load_file("siteconfig", {})


    def save_site_config(self):
        self.save_file("siteconfig", self.siteconf)


    def get_attribute(self, key, deflt=None):
        return self.attributes.get(key, deflt)


    def set_attribute(self, key, value):
        self.attributes[key] = value


    def unset_attribute(self, key):
        try:
            del self.attributes[key]
        except KeyError:
            pass


    def language(self, default=None):
        return self.get_attribute("language", get_language(default))


    def contact_groups(self):
        return self.get_attribute("contactgroups", [])


    def load_stars(self):
        return set(self.load_file("favorites", []))


    def save_stars(self, stars):
        self.save_file("favorites", list(stars))


    def may(self, pname):
        if pname in self.permissions:
            return self.permissions[pname]
        he_may = _may_with_roles(user.role_ids, pname)
        self.permissions[pname] = he_may
        return he_may


    def need_permission(self, pname):
        if not self.may(pname):
            perm = permissions_by_name[pname]
            raise MKAuthException(_("We are sorry, but you lack the permission "
                                  "for this operation. If you do not like this "
                                  "then please ask you administrator to provide you with "
                                  "the following permission: '<b>%s</b>'.") % perm["title"])


    def load_file(self, name, deflt, lock=False):
        # In some early error during login phase there are cases where it might
        # happen that a user file is requested but the user is not yet
        # set. We have all information to set it, then do it.
        if not user:
            return deflt # No user known at this point of time

        path = self.confdir + "/" + name + ".mk"
        return store.load_data_from_file(path, deflt, lock)


    def save_file(self, name, content, unlock=False):
        save_user_file(name, content, self.id, unlock)


    def file_modified(self, name):
        if self.confdir == None:
            return 0

        try:
            return os.stat(self.confdir + "/" + name + ".mk").st_mtime
        except OSError, e:
            if e.errno == errno.ENOENT:
                return 0
            else:
                raise



# Login a user that has all permissions. This is needed for making
# Livestatus queries from unauthentiated page handlers
# TODO: Can we somehow get rid of this?
class LoggedInSuperUser(LoggedInUser):
    def __init__(self):
        super(LoggedInSuperUser, self).__init__(None)
        self.alias = "Superuser for unauthenticated pages"
        self.email = "admin"


    def _gather_roles(self):
        return [ "admin" ]


    def _load_confdir(self):
        self.confdir = None


    def _load_site_config(self):
        self.siteconf = {}


    def load_file(self, name, deflt, lock=False):
        return deflt



class LoggedInNobody(LoggedInUser):
    def __init__(self):
        super(LoggedInNobody, self).__init__(None)
        self.alias = "Unauthenticated user"
        self.email = "nobody"


    def _gather_roles(self):
        return []


    def _load_confdir(self):
        self.confdir = None


    def _load_site_config(self):
        self.siteconf = {}


    def load_file(self, name, deflt, lock=False):
        return deflt



def clear_user_login():
    _set_user(LoggedInNobody())


def set_user_by_id(user_id):
    _set_user(LoggedInUser(user_id))


def set_super_user():
    _set_user(LoggedInSuperUser())


def _set_user(_user):
    global user
    user = _user


# This holds the currently logged in user object
user = LoggedInNobody()

#.
#   .--User Handling-------------------------------------------------------.
#   |    _   _                 _   _                 _ _ _                 |
#   |   | | | |___  ___ _ __  | | | | __ _ _ __   __| | (_)_ __   __ _     |
#   |   | | | / __|/ _ \ '__| | |_| |/ _` | '_ \ / _` | | | '_ \ / _` |    |
#   |   | |_| \__ \  __/ |    |  _  | (_| | | | | (_| | | | | | | (_| |    |
#   |    \___/|___/\___|_|    |_| |_|\__,_|_| |_|\__,_|_|_|_| |_|\__, |    |
#   |                                                            |___/     |
#   +----------------------------------------------------------------------+
#   | General user handling of all users, not only the currently logged    |
#   | in user. These functions are mostly working with the loaded multisite|
#   | configuration data (multisite_users, admin_users, ...), so they are  |
#   | more related to this module than to the userdb module.               |
#   '----------------------------------------------------------------------'

def roles_of_user(user_id):
    def existing_role_ids(role_ids):
        return [
            role_id for role_id in role_ids
            if role_id in roles
        ]

    if user_id in multisite_users:
        return existing_role_ids(multisite_users[user_id]["roles"])
    elif user_id in admin_users:
        return [ "admin" ]
    elif user_id in guest_users:
        return [ "guest" ]
    elif users != None and user_id in users:
        return [ "user" ]
    elif os.path.exists(config_dir + "/" + user_id.encode("utf-8") + "/automation.secret"):
        return [ "guest" ] # unknown user with automation account
    elif 'roles' in default_user_profile:
        return existing_role_ids(default_user_profile['roles'])
    elif default_user_role:
        return existing_role_ids([ default_user_role ])
    else:
        return []


def alias_of_user(user_id):
    if user_id in multisite_users:
        return multisite_users[user_id].get("alias", user_id)
    else:
        return user_id


def user_may(user_id, pname):
    return _may_with_roles(roles_of_user(user_id), pname)


# TODO: Check all calls for arguments (changed optional user to 3rd positional)
def save_user_file(name, data, user, unlock=False):
    path = config_dir + "/" + user.encode("utf-8") + "/" + name + ".mk"
    make_nagios_directory(os.path.dirname(path))
    store.save_data_to_file(path, data)


#.
#   .--Sites---------------------------------------------------------------.
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  The config module provides some helper functions for sites.         |
#   '----------------------------------------------------------------------'

def omd_site():
    return os.environ["OMD_SITE"]

def url_prefix():
    return "/%s/" % omd_site()

use_siteicons = False

def default_single_site_configuration():
    return {
        omd_site(): {
            'alias'        : _("Local site %s") % omd_site(),
            'disable_wato' : True,
            'disabled'     : False,
            'insecure'     : False,
            'multisiteurl' : '',
            'persist'      : False,
            'replicate_ec' : False,
            'replication'  : '',
            'timeout'      : 10,
            'user_login'   : True,
    }}

sites = {}

def sitenames():
    return sites.keys()

# TODO: Cleanup: Make clear that this function is used by the status GUI (and not WATO)
# and only returns the currently enabled sites. Or should we redeclare the "disabled" state
# to disable the sites at all?
# TODO: Rename this!
def allsites():
    return dict( [(name, site(name))
                  for name in sitenames()
                  if not site(name).get("disabled", False)
                     and site(name)['socket'] != 'disabled' ] )


def configured_sites():
    return [(site_id, site(site_id)) for site_id in sitenames() ]


def sorted_sites():
    sitenames = []
    for sitename, site in allsites().iteritems():
        sitenames.append((sitename, site['alias']))
    sitenames = sorted(sitenames, key=lambda k: k[1], cmp = lambda a,b: cmp(a.lower(), b.lower()))

    return sitenames


def site(site_id):
    s = dict(sites.get(site_id, {}))
    # Now make sure that all important keys are available.
    # Add missing entries by supplying default values.
    s.setdefault("alias", site_id)
    s.setdefault("socket", "unix:" + cmk.paths.livestatus_unix_socket)
    s.setdefault("url_prefix", "../") # relative URL from /check_mk/
    if type(s["socket"]) == tuple and s["socket"][0] == "proxy":
        s["cache"] = s["socket"][1].get("cache", True)
        s["socket"] = "unix:" + cmk.paths.livestatus_unix_socket + "proxy/" + site_id
    else:
        s["cache"] = False
    s["id"] = site_id
    return s


def site_is_local(site_name):
    s = sites.get(site_name, {})
    sock = s.get("socket")

    if not sock or sock == "unix:" + cmk.paths.livestatus_unix_socket:
        return True

    if type(s["socket"]) == tuple and s["socket"][0] == "proxy" \
       and s["socket"][1]["socket"] is None:
        return True

    return False


def default_site():
    for site_name, site in sites.items():
        if site_is_local(site_name):
            return site_name
    return None



def is_multisite():
    # TODO: Remove all calls of this function
    return True

def is_single_local_site():
    if len(sites) > 1:
        return False
    elif len(sites) == 0:
        return True
    else:
        # Also use Multisite mode if the one and only site is not local
        sitename = sites.keys()[0]
        return site_is_local(sitename)


def site_choices(filter_func=None):
    choices = []
    for site_id, site in sites.items():
        if filter_func and not filter_func(site_id, site):
            continue

        title = site_id
        if site.get("alias"):
            title += " - " + site["alias"]

        choices.append((site_id, title))

    return sorted(choices, key=lambda s: s[1])


def get_event_console_site_choices():
    return site_choices(filter_func=lambda site_id, site: site_is_local(site_id) or site.get("replicate_ec"))


#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |  Handling of our own plugins. In plugins other software pieces can   |
#   |  declare defaults for configuration variables.                       |
#   '----------------------------------------------------------------------'

def load_plugins(force):
    load_web_plugins("config", globals())

    # Make sure, builtin roles are present, even if not modified and saved with WATO.
    for br in builtin_role_ids:
        roles.setdefault(br, {})
