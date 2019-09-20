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

import sys
import errno
import os
import copy
import json
from typing import Any, Callable, Dict, List, NewType, Optional, Tuple, Union  # pylint: disable=unused-import
import six
from pathlib2 import Path

import cmk
import cmk.gui.utils as utils
import cmk.utils.tags
import cmk.gui.i18n
from cmk.gui.i18n import _
import cmk.gui.log as log
import cmk.utils.paths
import cmk.utils.store as store
from cmk.gui.exceptions import MKConfigError, MKAuthException
import cmk.gui.permissions as permissions

import cmk.gui.plugins.config

# This import is added for static analysis tools like pylint to make them
# know about all shipped config options. The default config options are
# later handled with the default_config dict and _load_default_config()
from cmk.gui.plugins.config.base import *  # pylint: disable=wildcard-import,unused-wildcard-import

if not cmk.is_raw_edition():
    from cmk.gui.cee.plugins.config.cee import *  # pylint: disable=wildcard-import,unused-wildcard-import

if cmk.is_managed_edition():
    from cmk.gui.cme.plugins.config.cme import *  # pylint: disable=wildcard-import,unused-wildcard-import

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

SiteId = NewType('SiteId', str)
SiteConfiguration = NewType('SiteConfiguration', Dict[str, Any])
SiteConfigurations = NewType('SiteConfigurations', Dict[SiteId, SiteConfiguration])

multisite_users = {}
admin_users = []
tags = cmk.utils.tags.TagConfig()

# hard coded in various permissions
builtin_role_ids = ["user", "admin", "guest"]

# Base directory of dynamic configuration
config_dir = cmk.utils.paths.var_dir + "/web"

# Stores the initial configuration values
default_config = {}  # type: Dict[str, Any]

# TODO: Clean this up
permission_declaration_functions = []

# Constants for BI
ALL_HOSTS = '(.*)'
HOST_STATE = ('__HOST_STATE__',)
HIDDEN = ('__HIDDEN__',)


class FOREACH_HOST(object):
    pass


class FOREACH_CHILD(object):
    pass


class FOREACH_CHILD_WITH(object):
    pass


class FOREACH_PARENT(object):
    pass


class FOREACH_SERVICE(object):
    pass


class REMAINING(object):
    pass


class DISABLED(object):
    pass


class HARD_STATES(object):
    pass


class DT_AGGR_WARN(object):
    pass


# Has to be declared here once since the functions can be assigned in
# bi.py and also in multisite.mk. "Double" declarations are no problem
# here since this is a dict (List objects have problems with duplicate
# definitions).
aggregation_functions = {}  # type: Dict[str, Callable]

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
    cmk.gui.i18n.set_user_localizations(user_localizations)


def _load_config_file(path):
    # type: (str) -> None
    """Load the given GUI configuration file"""
    try:
        exec (open(path).read(), globals(), globals())
    except IOError as e:
        if e.errno != errno.ENOENT:  # No such file or directory
            raise
    except Exception as e:
        raise MKConfigError(_("Cannot read configuration file %s: %s:") % (path, e))


# Load multisite.mk and all files in multisite.d/. This will happen
# for *each* HTTP request.
# FIXME: Optimize this to cache the config etc. until either the config files or plugins
# have changed. We could make this being cached for multiple requests just like the
# plugins of other modules. This may save significant time in case of small requests like
# the graph ajax page or similar.
def load_config():
    # type: () -> None
    global sites

    # Set default values for all user-changable configuration settings
    _initialize_with_default_config()

    # Initialze sites with default site configuration. Need to do it here to
    # override possibly deleted sites
    sites = default_single_site_configuration()

    # First load main file
    _load_config_file(cmk.utils.paths.default_config_dir + "/multisite.mk")

    # Load also recursively all files below multisite.d
    conf_dir = cmk.utils.paths.default_config_dir + "/multisite.d"
    filelist = []
    if os.path.isdir(conf_dir):
        for root, _directories, files in os.walk(conf_dir):
            for filename in files:
                if filename.endswith(".mk"):
                    filelist.append(root + "/" + filename)

    filelist.sort()
    for p in filelist:
        _load_config_file(p)

    if sites:
        sites = migrate_old_site_config(sites)
    else:
        sites = default_single_site_configuration()

    _prepare_tag_config()
    execute_post_config_load_hooks()


def _prepare_tag_config():
    # type: () -> None
    global tags

    # When the user config does not contain "tags" a pre 1.6 config is loaded. Convert
    # the wato_host_tags and wato_aux_tags to the new structure
    tag_config = wato_tags
    if not any(tag_config.values()) and (wato_host_tags or wato_aux_tags):
        tag_config = cmk.utils.tags.transform_pre_16_tags(wato_host_tags, wato_aux_tags)

    tags = cmk.utils.tags.get_effective_tag_config(tag_config)


def execute_post_config_load_hooks():
    # type: () -> None
    for func in _post_config_load_hooks:
        func()


_post_config_load_hooks = []  # type: List[Callable[[], None]]


def register_post_config_load_hook(func):
    # type: (Callable[[], None]) -> None
    _post_config_load_hooks.append(func)


def _initialize_with_default_config():
    # type: () -> None
    vars_before_plugins = all_nonfunction_vars(globals())
    load_plugins(True)
    vars_after_plugins = all_nonfunction_vars(globals())
    _load_default_config(vars_before_plugins, vars_after_plugins)

    _apply_default_config()


def _apply_default_config():
    # type: () -> None
    for k, v in default_config.items():
        if isinstance(v, (dict, list)):
            v = copy.deepcopy(v)
        globals()[k] = v


def _load_default_config(vars_before_plugins, vars_after_plugins):
    default_config.clear()
    _load_default_config_from_module_plugins()
    _load_default_config_from_legacy_plugins(vars_before_plugins, vars_after_plugins)


def _load_default_config_from_module_plugins():
    # TODO: Find a better solution for this. Probably refactor declaration of default
    # config option.
    config_plugin_vars = {}
    for module in _config_plugin_modules():
        config_plugin_vars.update(module.__dict__)

    for k, v in config_plugin_vars.items():
        if k[0] == "_":
            continue

        if isinstance(v, (dict, list)):
            v = copy.deepcopy(v)

        default_config[k] = v


def _load_default_config_from_legacy_plugins(vars_before_plugins, vars_after_plugins):
    new_vars = vars_after_plugins.difference(vars_before_plugins)
    default_config.update(dict([(k, copy.deepcopy(globals()[k])) for k in new_vars]))


def _config_plugin_modules():
    return [
        module for name, module in sys.modules.items()
        if (name.startswith("cmk.gui.plugins.config.") or name.startswith(
            "cmk.gui.cee.plugins.config.") or name.startswith("cmk.gui.cme.plugins.config.")) and
        module is not None
    ]


def reporting_available():
    try:
        # Check the existance of one arbitrary config variable from the
        # reporting module
        _dummy = reporting_filename
        return True
    except NameError:
        return False


def combined_graphs_available():
    try:
        _dummy = have_combined_graphs
        return True
    except NameError:
        return False


def hide_language(lang):
    return lang in hide_languages


def all_nonfunction_vars(var_dict):
    return {
        name for name, value in var_dict.items()
        if name[0] != '_' and not hasattr(value, '__call__')
    }


def get_language(default=None):
    if default is None:
        return default_language
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

# Kept for compatibility with pre 1.6 GUI plugins
declare_permission = permissions.declare_permission
declare_permission_section = permissions.declare_permission_section


# Some module have a non-fixed list of permissions. For example for
# each user defined view there is also a permission. This list is
# not known at the time of the loading of the module - though. For
# that purpose module can register functions. These functions should
# just call declare_permission(). They are being called in the correct
# situations.
# TODO: Clean this up
def declare_dynamic_permissions(func):
    permission_declaration_functions.append(func)


# This function needs to be called by all code that needs access
# to possible dynamic permissions
# TODO: Clean this up
def load_dynamic_permissions():
    for func in permission_declaration_functions:
        func()


def get_role_permissions():
    """Returns the set of permissions for all roles"""
    role_permissions = {}
    roleids = roles.keys()
    for perm_class in permissions.permission_registry.values():
        perm = perm_class()
        for role_id in roleids:
            if not role_id in role_permissions:
                role_permissions[role_id] = []

            if _may_with_roles([role_id], perm.name):
                role_permissions[role_id].append(perm.name)
    return role_permissions


def _may_with_roles(some_role_ids, pname):
    # If at least one of the given roles has this permission, it's fine
    for role_id in some_role_ids:
        role = roles[role_id]

        he_may = role.get("permissions", {}).get(pname)
        # Handle compatibility with permissions without "general." that
        # users might have saved in their own custom roles.
        if he_may is None and pname.startswith("general."):
            he_may = role.get("permissions", {}).get(pname[8:])

        if he_may is None:  # not explicitely listed -> take defaults
            if "basedon" in role:
                base_role_id = role["basedon"]
            else:
                base_role_id = role_id
            if pname not in permissions.permission_registry:
                return False  # Permission unknown. Assume False. Functionality might be missing
            perm = permissions.permission_registry[pname]()
            he_may = base_role_id in perm.defaults
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
        self._button_counts = None

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
        if self.attributes is None:
            if self.id in multisite_users:
                self.attributes = multisite_users[self.id]
            else:
                self.attributes = {
                    "roles": self.role_ids,
                }

        self.alias = self.attributes.get("alias", self.id)
        self.email = self.attributes.get("email", self.id)

    def _load_permissions(self):
        # Prepare cache of already computed permissions
        # Make sure, admin can restore permissions in any case!
        if self.id in admin_users:
            self.permissions = {
                "general.use": True,  # use Multisite
                "wato.use": True,  # enter WATO
                "wato.edit": True,  # make changes in WATO...
                "wato.users": True,  # ... with access to user management
            }
        else:
            self.permissions = {}

    def _load_confdir(self):
        self.confdir = config_dir + "/" + self.id.encode("utf-8")
        store.mkdir(self.confdir)

    def _load_site_config(self):
        self.siteconf = self.load_file("siteconfig", {})

    def get_button_counts(self):
        if not self._button_counts:
            self._button_counts = self.load_file("buttoncounts", {})
        return self._button_counts

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

    def is_site_disabled(self, site_id):
        # type: (SiteId) -> bool
        siteconf = self.siteconf.get(site_id, {})
        return siteconf.get("disabled", False)

    def authorized_sites(self, unfiltered_sites=None):
        # type: (Optional[SiteConfigurations]) -> SiteConfigurations
        if unfiltered_sites is None:
            unfiltered_sites = allsites()

        authorized_sites = self.get_attribute("authorized_sites")
        if authorized_sites is None:
            return SiteConfigurations(dict(unfiltered_sites))

        return SiteConfigurations({
            site_id: s  #
            for site_id, s in unfiltered_sites.iteritems()
            if site_id in authorized_sites
        })

    def authorized_login_sites(self):
        # type: () -> SiteConfigurations
        login_site_ids = get_login_slave_sites()
        return self.authorized_sites(
            SiteConfigurations({
                site_id: s  #
                for site_id, s in allsites().items()
                if site_id in login_site_ids
            }))

    def may(self, pname):
        # type: (str) -> bool
        if pname in self.permissions:
            return self.permissions[pname]
        he_may = _may_with_roles(user.role_ids, pname)
        self.permissions[pname] = he_may
        return he_may

    def need_permission(self, pname):
        if not self.may(pname):
            perm = permissions.permission_registry[pname]()
            raise MKAuthException(
                _("We are sorry, but you lack the permission "
                  "for this operation. If you do not like this "
                  "then please ask you administrator to provide you with "
                  "the following permission: '<b>%s</b>'.") % perm.title)

    def load_file(self, name, deflt, lock=False):
        # In some early error during login phase there are cases where it might
        # happen that a user file is requested but the user is not yet
        # set. We have all information to set it, then do it.
        if not user:
            return deflt  # No user known at this point of time

        path = self.confdir + "/" + name + ".mk"
        return store.load_data_from_file(path, deflt, lock)

    def save_file(self, name, content, unlock=False):
        save_user_file(name, content, self.id, unlock)

    def file_modified(self, name):
        if self.confdir is None:
            return 0

        try:
            return os.stat(self.confdir + "/" + name + ".mk").st_mtime
        except OSError as e:
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
        return ["admin"]

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
        return [role_id for role_id in role_ids if role_id in roles]

    if user_id in multisite_users:
        return existing_role_ids(multisite_users[user_id]["roles"])
    elif user_id in admin_users:
        return ["admin"]
    elif user_id in guest_users:
        return ["guest"]
    elif users is not None and user_id in users:
        return ["user"]
    elif os.path.exists(config_dir + "/" + user_id.encode("utf-8") + "/automation.secret"):
        return ["guest"]  # unknown user with automation account
    elif 'roles' in default_user_profile:
        return existing_role_ids(default_user_profile['roles'])
    elif default_user_role:
        return existing_role_ids([default_user_role])
    return []


def alias_of_user(user_id):
    if user_id in multisite_users:
        return multisite_users[user_id].get("alias", user_id)
    return user_id


def user_may(user_id, pname):
    return _may_with_roles(roles_of_user(user_id), pname)


# TODO: Check all calls for arguments (changed optional user to 3rd positional)
def save_user_file(name, data, user_id, unlock=False):
    path = config_dir + "/" + user_id.encode("utf-8") + "/" + name + ".mk"
    store.mkdir(os.path.dirname(path))
    store.save_data_to_file(path, data)


def migrate_old_site_config(site_config):
    # type: (SiteConfigurations) -> SiteConfigurations
    if not site_config:
        # Prevent problem when user has deleted all sites from his
        # configuration and sites is {}. We assume a default single site
        # configuration in that case.
        return default_single_site_configuration()

    for site_id, site_cfg in site_config.iteritems():
        # Until 1.6 "replication" could be not present or
        # set to "" instead of None
        if site_cfg.get("replication", "") == "":
            site_cfg["replication"] = None

        # Until 1.6 "url_prefix" was an optional attribute
        if "url_prefix" not in site_cfg:
            site_cfg["url_prefix"] = "/%s/" % site_id

        site_cfg.setdefault("proxy", None)

        _migrate_pre_16_socket_config(site_cfg)

    return site_config


# During development of the 1.6 version the site configuration has been cleaned up in several ways:
# 1. The "socket" attribute could be "disabled" to disable a site connection. This has already been
#    deprecated long time ago and was not configurable in WATO. This has now been superceeded by
#    the dedicated "disabled" attribute.
# 2. The "socket" attribute was optional. A not present socket meant "connect to local unix" socket.
#    This is now replaced with a value like this ("local", None) to reflect the generic
#    CascadingDropdown() data structure of "(type, attributes)".
# 3. The "socket" attribute was stored in the livestatus.py socketurl encoded format, at least when
#    livestatus proxy was not used. This is now stored in the CascadingDropdown() native format and
#    converted here to the correct format.
# 4. When the livestatus proxy was enabled for a site, the settings were stored in the "socket"
#    attribute. The proxy settings were an additional dict which also held a "socket" key containing
#    the final socket connection properties.
#    This has now been split up. The top level socket settings are now used independent of the proxy.
#    The proxy options are stored in the separate key "proxy" which is a mandatory key.
def _migrate_pre_16_socket_config(site_cfg):
    if site_cfg.get("socket") is None:
        site_cfg["socket"] = ("local", None)
        return

    socket = site_cfg["socket"]
    if isinstance(socket, tuple) and socket[0] == "proxy":
        site_cfg["proxy"] = socket[1]

        # "socket" of proxy could either be None or two element tuple for "tcp"
        proxy_socket = site_cfg["proxy"].pop("socket", None)
        if proxy_socket is None:
            site_cfg["socket"] = ("local", None)

        elif isinstance(socket, tuple):
            site_cfg["socket"] = ("tcp", {
                "address": proxy_socket,
                "tls": ("plain_text", {}),
            })

        else:
            raise NotImplementedError("Unhandled proxy socket: %r" % proxy_socket)

        return

    if socket == 'disabled':
        site_cfg['disabled'] = True
        site_cfg['socket'] = ("local", None)
        return

    if isinstance(socket, six.string_types):
        site_cfg["socket"] = _migrate_string_encoded_socket(socket)


def _migrate_string_encoded_socket(value):
    # type: (str) -> Tuple[str, Union[Dict]]
    family_txt, address = value.split(":", 1)  # pylint: disable=no-member

    if family_txt == "unix":
        return "unix", {
            "path": value.split(":", 1)[1],
        }

    if family_txt in ["tcp", "tcp6"]:
        host, port = address.rsplit(":", 1)
        return family_txt, {
            "address": (host, int(port)),
            "tls": ("plain_text", {}),
        }

    raise NotImplementedError()


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
    # type: () -> SiteId
    return cmk.omd_site()


def url_prefix():
    # type: () -> str
    return "/%s/" % cmk.omd_site()


use_siteicons = False


def default_single_site_configuration():
    # type: () -> SiteConfigurations
    return SiteConfigurations({
        omd_site(): SiteConfiguration({
            'alias': _("Local site %s") % omd_site(),
            'socket': ("local", None),
            'disable_wato': True,
            'disabled': False,
            'insecure': False,
            'url_prefix': "/%s/" % omd_site(),
            'multisiteurl': '',
            'persist': False,
            'replicate_ec': False,
            'replication': None,
            'timeout': 5,
            'user_login': True,
            'proxy': None,
        })
    })


sites = SiteConfigurations({})


def sitenames():
    # () -> List[SiteId]
    return sites.keys()


# TODO: Cleanup: Make clear that this function is used by the status GUI (and not WATO)
# and only returns the currently enabled sites. Or should we redeclare the "disabled" state
# to disable the sites at all?
# TODO: Rename this!
def allsites():
    # type: () -> SiteConfigurations
    return SiteConfigurations({
        name: site(name)  #
        for name in sitenames()
        if not site(name).get("disabled", False)
    })


def configured_sites():
    # type: () -> SiteConfigurations
    return SiteConfigurations({site_id: site(site_id) for site_id in sitenames()})


def has_wato_slave_sites():
    return bool(wato_slave_sites())


def is_wato_slave_site():
    return _has_distributed_wato_file() and not has_wato_slave_sites()


def _has_distributed_wato_file():
    return os.path.exists(cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk") \
        and os.stat(cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk").st_size != 0


def get_login_sites():
    # type: () -> List[SiteId]
    """Returns the WATO slave sites a user may login and the local site"""
    return get_login_slave_sites() + [omd_site()]


# TODO: All site listing functions should return the same data structure, e.g. a list of
#       pairs (site_id, site)
def get_login_slave_sites():
    # type: () -> List[SiteId]
    """Returns a list of site ids which are WATO slave sites and users can login"""
    login_sites = []
    for site_id, site_spec in wato_slave_sites().iteritems():
        if site_spec.get('user_login', True) and not site_is_local(site_id):
            login_sites.append(site_id)
    return login_sites


def wato_slave_sites():
    # type: () -> SiteConfigurations
    return SiteConfigurations({
        site_id: s  #
        for site_id, s in sites.items()
        if s.get("replication")
    })


def sorted_sites():
    # type: () -> List[Tuple[SiteId, str]]
    return sorted([(site_id, s['alias']) for site_id, s in user.authorized_sites().iteritems()],
                  key=lambda k: k[1].lower())


def site(site_id):
    # type: (SiteId) -> SiteConfiguration
    s = SiteConfiguration(dict(sites.get(site_id, {})))
    # Now make sure that all important keys are available.
    # Add missing entries by supplying default values.
    s.setdefault("alias", site_id)
    s.setdefault("socket", ("local", None))
    s.setdefault("url_prefix", "../")  # relative URL from /check_mk/
    s["id"] = site_id
    return s


def site_is_local(site_id):
    # type: (SiteId) -> bool
    family_spec, address_spec = site(site_id)["socket"]
    return _is_local_socket_spec(family_spec, address_spec)


def _is_local_socket_spec(family_spec, address_spec):
    # type: (str, Dict[str, Any]) -> bool
    if family_spec == "local":
        return True

    if family_spec == "unix" and address_spec["path"] == cmk.utils.paths.livestatus_unix_socket:
        return True

    return False


def default_site():
    # type: () -> Optional[SiteId]
    for site_name, _site in sites.items():
        if site_is_local(site_name):
            return site_name
    return None


def is_single_local_site():
    # type: () -> bool
    if len(sites) > 1:
        return False
    elif len(sites) == 0:
        return True

    # Also use Multisite mode if the one and only site is not local
    sitename = sites.keys()[0]
    return site_is_local(sitename)


def site_attribute_default_value():
    # type: () -> Optional[SiteId]
    def_site = default_site()
    authorized_site_ids = user.authorized_sites(unfiltered_sites=configured_sites()).keys()
    if def_site and def_site in authorized_site_ids:
        return def_site
    return None


def site_attribute_choices():
    # () -> List[Tuple[SiteId, str]]
    authorized_site_ids = user.authorized_sites(unfiltered_sites=configured_sites()).keys()
    return site_choices(filter_func=lambda site_id, site: site_id in authorized_site_ids)


def site_choices(filter_func=None):
    # (Optional[Callable[[SiteId, SiteConfiguration], bool]]) -> List[Tuple[SiteId, str]]
    choices = []
    for site_id, site_spec in sites.items():
        if filter_func and not filter_func(site_id, site_spec):
            continue

        title = site_id
        if site_spec.get("alias"):
            title += " - " + site_spec["alias"]

        choices.append((site_id, title))

    return sorted(choices, key=lambda s: s[1])


def get_event_console_site_choices():
    # () -> List[Tuple[SiteId, str]]
    return site_choices(
        filter_func=lambda site_id, site: site_is_local(site_id) or site.get("replicate_ec"))


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
    utils.load_web_plugins("config", globals())

    # Make sure, builtin roles are present, even if not modified and saved with WATO.
    for br in builtin_role_ids:
        roles.setdefault(br, {})


def theme_choices():
    themes = {}

    for base_dir in [Path(cmk.utils.paths.web_dir), cmk.utils.paths.local_web_dir]:
        if not base_dir.exists():
            continue

        for theme_dir in (base_dir / "htdocs" / "themes").iterdir():  # pylint: disable=no-member
            meta_file = theme_dir / "theme.json"
            if not meta_file.exists():
                continue

            try:
                theme_meta = json.loads(meta_file.open(encoding="utf-8").read())
            except ValueError:
                # Ignore broken meta files and show the directory name as title
                theme_meta = {
                    "title": theme_dir.name,
                }

            themes[theme_dir.name] = theme_meta["title"]

    return sorted(themes.items())


def get_page_heading():
    if "%s" in page_heading:
        return page_heading % (site(omd_site()).get('alias', _("GUI")))
    return page_heading
