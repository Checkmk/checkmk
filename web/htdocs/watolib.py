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

# WATO LIBRARY
#
# This file contains classes, functions and globals that are being
# used by WATO. It does not contain any acutal page handlers or
# WATO modes. Nor complex HTML creation. This is all contained
# in wato.py

#   .--Initialization------------------------------------------------------.
#   |                           ___       _ _                              |
#   |                          |_ _|_ __ (_) |_                            |
#   |                           | || '_ \| | __|                           |
#   |                           | || | | | | |_                            |
#   |                          |___|_| |_|_|\__|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Doing this that must be done when the module WATO is loaded.        |
#   '----------------------------------------------------------------------'

import os, shutil, subprocess, base64
import defaults, config, hooks, userdb, multitar, pickle
from lib import *
from valuespec import *

replication_paths = []
backup_paths = []
backup_domains = {}

def initialize_before_loading_plugins():
    # Directories and files to synchronize during replication
    global replication_paths
    replication_paths = [
        ( "dir",  "check_mk",   wato_root_dir ),
        ( "dir",  "multisite",  multisite_dir ),
        ( "file", "htpasswd",   defaults.htpasswd_file ),
        ( "file", "auth.secret",  '%s/auth.secret' % os.path.dirname(defaults.htpasswd_file) ),
        ( "file", "auth.serials", '%s/auth.serials' % os.path.dirname(defaults.htpasswd_file) ),
        # Also replicate the user-settings of Multisite? While the replication
        # as such works pretty well, the count of pending changes will not
        # know.
        ( "dir", "usersettings", defaults.var_dir + "/web" ),
    ]
    if defaults.omd_root:
        replication_paths += [
          ( "dir", "mkps",  defaults.var_dir + "/packages" ),
          ( "dir", "local", defaults.omd_root + "/local" ),
        ]

    # Directories and files for backup & restore
    global backup_paths
    backup_paths = replication_paths + [
        ( "file", "sites",      sites_mk)
        # autochecks are a site-local ressource. This does only make
        # sense for single-site installations. How should we handle
        # this?
        # ( "dir", "autochecks", defaults.autochecksdir ),
    ]

    # Include rule configuration into backup/restore/replication. Current
    # status is not backed up.
    if hasattr(config, "mkeventd_enabled") and config.mkeventd_enabled:
        mkeventd_config_dir = defaults.default_config_dir + "/mkeventd.d/wato/"
        replication_paths.append(("dir", "mkeventd", mkeventd_config_dir))
        backup_paths.append(("dir", "mkeventd", mkeventd_config_dir))

    global backup_domains
    backup_domains = {}

def init_watolib_datastructures():
    if config.wato_use_git:
        prepare_git_commit()

    declare_host_tag_attributes() # create attributes out of tag definitions
    declare_site_attribute()      # create attribute for distributed WATO

#.
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Constants used in configuration files
ALL_HOSTS    = [ '@all' ]
ALL_SERVICES = [ "" ]
NEGATE       = '@negate'
NO_ITEM      = {} # Just an arbitrary unique thing

# Actions for log_pending
RESTART      = 1
SYNC         = 2
SYNCRESTART  = 3
AFFECTED     = 4
LOCALRESTART = 5

# Some paths and directories
wato_root_dir  = defaults.check_mk_configdir + "/wato/"
multisite_dir  = defaults.default_config_dir + "/multisite.d/wato/"
sites_mk       = defaults.default_config_dir + "/multisite.d/sites.mk"
var_dir        = defaults.var_dir + "/wato/"
log_dir        = var_dir + "log/"
snapshot_dir   = var_dir + "snapshots/"
repstatus_file = var_dir + "replication_status.mk"
php_api_dir    = var_dir + "php-api/"


#.
#   .--Changes-------------------------------------------------------------.
#   |                ____ _                                                |
#   |               / ___| |__   __ _ _ __   __ _  ___  ___                |
#   |              | |   | '_ \ / _` | '_ \ / _` |/ _ \/ __|               |
#   |              | |___| | | | (_| | | | | (_| |  __/\__ \               |
#   |               \____|_| |_|\__,_|_| |_|\__, |\___||___/               |
#   |                                       |___/                          |
#   +----------------------------------------------------------------------+
#   | Functions for logging changes and keeping the "Activate Changes"     |
#   | state and finally activating changes.                                |
#   '----------------------------------------------------------------------'

# This is the single site activation mode
def activate_changes():
    try:
        start = time.time()
        check_mk_local_automation(config.wato_activation_method)
        duration = time.time() - start
        update_replication_status(None, {}, { 'act': duration })
    except Exception:
        if config.debug:
            import traceback
            raise MKUserError(None, "Error executing hooks: %s" %
                              traceback.format_exc().replace('\n', '<br />'))
        else:
            raise


# Determine if other users have made pending changes
def foreign_changes():
    changes = {}
    for t, linkinfo, user, action, text in parse_audit_log("pending"):
        if user != '-' and user != config.user_id:
            changes.setdefault(user, 0)
            changes[user] += 1
    return changes


# linkinfo identifies the object operated on. It can be a Host or a Folder
# or a text.
def log_entry(linkinfo, action, message, logfilename, user_id = None):
    # Using attrencode here is against our regular rule to do the escaping
    # at the last possible time: When rendering. But this here is the last
    # place where we can distinguish between HTML() encapsulated (already)
    # escaped / allowed HTML and strings to be escaped.
    message = make_utf8(html.attrencode(message)).strip()

    # linkinfo is either a Folder, or a Host or a hostname or None
    if isinstance(linkinfo, Folder):
        link = linkinfo.path() + ":"
    elif isinstance(linkinfo, Host):
        link = linkinfo.folder().path() + ":" + linkinfo.name()
    elif linkinfo == None:
        link = "-"
    else:
        link = linkinfo

    if user_id == None and config.user_id != None:
        user_id = config.user_id.encode("utf-8")
    elif user_id == '':
        user_id = '-'

    log_file = log_dir + logfilename
    make_nagios_directory(log_dir)
    f = create_user_file(log_file, "ab")
    f.write("%d %s %s %s %s\n" % (int(time.time()), link, user_id, action, message))


def log_audit(linkinfo, what, message, user_id = None):
    if config.wato_use_git:
        if isinstance(message, HTML):
            message = html.strip_tags(message.value)
        g_git_messages.append(message)
    log_entry(linkinfo, what, message, "audit.log", user_id)


# status is one of:
# SYNC        -> Only sync neccessary
# RESTART     -> Restart and sync neccessary (where is this used??)
# SYNCRESTART -> Do sync and restart
# AFFECTED    -> affected sites are already marked for sync+restart
#                by mark_affected_sites_dirty().
# LOCALRESTART-> Called after inventory. In distributed mode, affected
#                sites have already been marked for restart. Do nothing here.
#                In non-distributed mode mark for restart
def log_pending(status, linkinfo, what, message, user_id = None):
    log_audit(linkinfo, what, message, user_id)
    need_sidebar_reload()

    # On each change to the Check_MK configuration mark the agents to be rebuild
    if 'need_to_bake_agents' in globals():
        need_to_bake_agents()

    # Only add pending log entries when a restart is needed
    if has_wato_slave_sites() or status != SYNC:
        log_entry(linkinfo, what, message, "pending.log", user_id)

    # Currently we add the pending to each site, regardless if
    # the site is really affected. This needs to be optimized
    # in future.
    for siteid, site in config.sites.items():
        changes = {}

        # Local site can never have pending changes to be synced
        if config.site_is_local(siteid):
            if status in [ RESTART, SYNCRESTART ]:
                changes["need_restart"] = True
        else:
            if status in [ SYNC, SYNCRESTART ]:
                changes["need_sync"] = True

            if status in [ RESTART, SYNCRESTART ]:
                changes["need_restart"] = True
        update_replication_status(siteid, changes)

        # Make sure that a new snapshot for syncing will be created
        # when times comes to syncing
        remove_sync_snapshot(siteid)


def log_exists(what):
    path = log_dir + what + ".log"
    return os.path.exists(path)


def clear_audit_log():
    path = log_dir + "audit.log"
    if os.path.exists(path):
        newpath = path + time.strftime(".%Y-%m-%d")
        if os.path.exists(newpath):
            n = 1
            while True:
                n += 1
                with_num = newpath + "-%d" % n
                if not os.path.exists(with_num):
                    newpath = with_num
                    break
        os.rename(path, newpath)


def parse_audit_log(what):
    path = log_dir + what + ".log"
    if os.path.exists(path):
        entries = []
        for line in file(path):
            line = line.rstrip().decode("utf-8")
            splitted = line.split(None, 4)
            if len(splitted) == 5 and isint(splitted[0]):
                splitted[0] = int(splitted[0])
                entries.append(splitted)
        entries.reverse()
        return entries
    return []


def log_commit_pending():
    pending = log_dir + "pending.log"
    if os.path.exists(pending):
        os.remove(pending)
    need_sidebar_reload()

#.
#   .--Hosts & Folders-----------------------------------------------------.
#   | _   _           _          ___     _____     _     _                 |
#   || | | | ___  ___| |_ ___   ( _ )   |  ___|__ | | __| | ___ _ __ ___   |
#   || |_| |/ _ \/ __| __/ __|  / _ \/\ | |_ / _ \| |/ _` |/ _ \ '__/ __|  |
#   ||  _  | (_) \__ \ |_\__ \ | (_>  < |  _| (_) | | (_| |  __/ |  \__ \  |
#   ||_| |_|\___/|___/\__|___/  \___/\/ |_|  \___/|_|\__,_|\___|_|  |___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  New Implementation of handling of hosts and folders                 |
#   |  This new implementation is currently additional to the existing one |
#   |  but will replace step by step all direct handling with the folder   |
#   |  and host dictionaries.                                              |
#   '----------------------------------------------------------------------'

# Names:
# folder_path: Path of the folders directory relative to etc/check_mk/conf.d/wato
#              The root folder is "". No trailing / is allowed here.
# wato_info:   The dictionary that is saved in the folder's .wato file

# Terms:
# create, delete   mean actual filesystem operations
# add, remove      mean just modifications in the data structures

class WithPermissions(object):
    def __init__(self):
        object.__init__(self)

    def may(self, how): # how is "read" or "write"
        return self.user_may(config.user_id, how)


    def reason_why_may_not(self, how):
        return self.reason_why_user_may_not(config.user_id, how)


    def user_needs_permission(self, user_id, how):
        raise NotImplementedError("Subclasses has to implement this!")


    def need_permission(self, how):
        self.user_needs_permission(config.user_id, how)


    def user_may(self, user_id, how):
        try:
            self.user_needs_permission(user_id, how)
            return True
        except MKAuthException, e:
            return False


    def reason_why_user_may_not(self, user_id, how):
        try:
            self.user_needs_permission(user_id, how)
            return False
        except MKAuthException, e:
            return "%s" % e



# Base class containing a couple of generic permission checking functions, used
# for Host and Folder
class WithPermissionsAndAttributes(WithPermissions):
    def __init__(self):
        WithPermissions.__init__(self)
        self._attributes = {}

    # .--------------------------------------------------------------------.
    # | ATTRIBUTES                                                         |
    # '--------------------------------------------------------------------'

    def attributes(self):
        return self._attributes


    def attribute(self, attrname, default_value=None):
        return self.attributes().get(attrname, default_value)


    def set_attribute(self, attrname, value):
        self._attributes[attrname] = value


    def has_explicit_attribute(self, attrname):
        return attrname in self.attributes()


    def effective_attributes(self):
        raise NotImplementedError("Subclasses has to implement this!")


    def effective_attribute(self, attrname, default_value=None):
        return self.effective_attributes().get(attrname, default_value)


    def remove_attribute(self, attrname):
        del self.attributes()[attrname]


#.
#   .--BaseFolder----------------------------------------------------------.
#   |          ____                 _____     _     _                      |
#   |         | __ )  __ _ ___  ___|  ___|__ | | __| | ___ _ __            |
#   |         |  _ \ / _` / __|/ _ \ |_ / _ \| |/ _` |/ _ \ '__|           |
#   |         | |_) | (_| \__ \  __/  _| (_) | | (_| |  __/ |              |
#   |         |____/ \__,_|___/\___|_|  \___/|_|\__,_|\___|_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class of SearchFolder and Folder. Implements common methods.   |
#   '----------------------------------------------------------------------'
class BaseFolder(WithPermissionsAndAttributes):
    def __init__(self):
        WithPermissions.__init__(self)


    def hosts(self):
        raise NotImplementedError("Subclasses has to implement this!")


    def host_names(self):
        return self.hosts().keys()


    def host(self, host_name):
        return self.hosts().get(host_name)


    def has_host(self, host_name):
        return host_name in self.hosts()


    def has_hosts(self):
        return len(self.hosts()) != 0


    def host_validation_errors(self):
        return validate_all_hosts(self.host_names())


    def is_disk_folder(self):
        return False


    def is_search_folder(self):
        return False


    def has_parent(self):
        return self.parent() != None


    def is_same_as(self, folder):
        return self == folder or self.path() == folder.path()


    def is_current_folder(self):
        return self.is_same_as(Folder.current())


    def is_parent_of(self, maybe_child):
        return maybe_child.parent() == self


    def is_transitive_parent_of(self, maybe_child):
        if self.is_same_as(maybe_child):
            return True
        elif maybe_child.has_parent():
            return self.is_transitive_parent_of(maybe_child.parent())
        else:
            return False


    def is_root(self):
        return not self.has_parent()


    def parent_folder_chain(self):
        folders = []
        folder = self.parent()
        while folder:
            folders.append(folder)
            folder = folder.parent()
        return folders[::-1]


    def show_breadcrump(self, link_to_folder=False, keepvarnames=["mode"]):
        keepvars = [ (name, html.var(name)) for name in keepvarnames ]
        if link_to_folder:
            keepvars.append(("mode", "folder"))

        def render_component(folder):
            return '<a href="%s">%s</a>' % (html.makeuri_contextless([("folder", folder.path())] + keepvars),
                                            html.attrencode(folder.title()))

        def breadcrump_element_start(end = '', z_index = 0):
            html.write('<li style="z-index:%d;"><div class="left %s"></div>' % (z_index, end))

        def breadcrump_element_end(end = ''):
            html.write('<div class="right %s"></div></li>' % end)


        parts = []
        for folder in self.parent_folder_chain():
            parts.append(render_component(folder))

        # The current folder (with link or without link)
        if link_to_folder:
            parts.append(render_component(self))
        else:
            parts.append(html.attrencode(self.title()))


        # Render the folder path
        html.write("<div class=folderpath><ul>\n")
        num = 0
        for part in parts:
            if num == 0:
                breadcrump_element_start('end', z_index = 100 + num)
            else:
                breadcrump_element_start(z_index = 100 + num)
            html.write('<div class=content>%s</div>\n' % part)

            breadcrump_element_end(num == len(parts)-1
                      and not (self.has_subfolders() and not link_to_folder)
                      and "end" or "")
            num += 1

        # Render the current folder when having subfolders
        if self.has_subfolders() and not link_to_folder:
            breadcrump_element_start(z_index = 100 + num)
            html.write("<div class=content><form method=GET name=folderpath>")
            html.sorted_select(
                "folder", [ ("", "") ] + self.subfolder_choices(),
                onchange = "folderpath.submit();",
                attrs = { "class": "folderpath", }
            )
            for var in keepvarnames:
                html.hidden_field(var, html.var(var))
            html.write("</form></div>")
            breadcrump_element_end('end')

        html.write("</ul></div>\n")


#.
#   .--Folder--------------------------------------------------------------.
#   |                     _____     _     _                                |
#   |                    |  ___|__ | | __| | ___ _ __                      |
#   |                    | |_ / _ \| |/ _` |/ _ \ '__|                     |
#   |                    |  _| (_) | | (_| |  __/ |                        |
#   |                    |_|  \___/|_|\__,_|\___|_|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  This class represents a WATO folder that contains other folders and |
#   |  hosts.                                                              |
#   '----------------------------------------------------------------------'


class Folder(BaseFolder):
    # .--------------------------------------------------------------------.
    # | STATIC METHODS                                                     |
    # '--------------------------------------------------------------------'

    @staticmethod
    def all_folders():
        if not html.is_cached("wato_folders"):
            wato_folders = html.set_cache("wato_folders", {})
            Folder("", "").add_to_dictionary(wato_folders)
        return html.get_cached("wato_folders")


    @staticmethod
    def folder_choices():
        return Folder.root_folder().recursive_subfolder_choices()


    @staticmethod
    def folder(folder_path):
        if folder_path in Folder.all_folders():
            return Folder.all_folders()[folder_path]
        else:
            raise MKGeneralException("No WATO folder %s." % folder_path)


    @staticmethod
    def create_missing_folders(folder_path):
        folder = Folder.folder("")
        for subfolder_name in Folder._split_folder_path(folder_path):
            if folder.has_subfolder(subfolder_name):
                folder = folder.subfolder(subfolder_name)
            else:
                folder = folder.create_subfolder(subfolder_name, subfolder_name, {})


    @staticmethod
    def _split_folder_path(folder_path):
        if not folder_path:
            return []
        else:
            return folder_path.split("/")


    @staticmethod
    def folder_exists(folder_path):
        return os.path.exists(wato_root_dir + folder_path)


    @staticmethod
    def root_folder():
        return Folder.folder("")


    @staticmethod
    def invalidate_caches():
        html.del_cache("wato_folders")
        Folder.root_folder().drop_caches()


    # Find folder that is specified by the current URL. This is either by a folder
    # path in the variable "folder" or by a host name in the variable "host". In the
    # latter case we need to load all hosts in all folders and actively search the host.
    @staticmethod
    def current():
        if not html.is_cached("wato_current_folder"):
            if html.has_var("host_search"):
                base_folder = Folder.folder(html.var("folder", ""))
                search_criteria = SearchFolder.criteria_from_html_vars()
                folder = SearchFolder(base_folder, search_criteria)
            elif html.has_var("folder"):
                folder = Folder.folder(html.var("folder"))
            else:
                host_name = html.var("host")
                folder = Folder.root_folder()
                if host_name: # find host with full scan. Expensive operation
                    host = Host.host(host_name)
                    if host:
                        folder = host.folder()

            html.set_cache("wato_current_folder", folder)
            return folder
        else:
            return html.get_cached("wato_current_folder")


    @staticmethod
    def current_disk_folder():
        folder = Folder.current()
        while not folder.is_disk_folder():
            folder = folder.parent()
        return folder


    @staticmethod
    def set_current(folder):
        html.set_cache("wato_current_folder", folder)



    # .-----------------------------------------------------------------------.
    # | CONSTRUCTION, LOADING & SAVING                                        |
    # '-----------------------------------------------------------------------'


    def __init__(self, name, folder_path=None, parent_folder=None, title=None, attributes=None):
        WithPermissionsAndAttributes.__init__(self)
        self._name = name
        self._parent = parent_folder
        self._subfolders = {}
        self._choices_for_moving_host = None
        if folder_path != None:
            self._init_by_loading_existing_directory(folder_path)
        else:
            self._init_by_creating_new(title, attributes)


    def _init_by_loading_existing_directory(self, folder_path):
        self._hosts = None
        self._load()
        self.load_subfolders()


    def _init_by_creating_new(self, title, attributes):
        self._hosts = {}
        self._num_hosts = 0
        self._title = title
        self._attributes = attributes
        self._locked = False
        self._locked_hosts = False
        self._locked_subfolders = False


    def __repr__(self):
        return "Folder(%r, %r)" % (self.path(), self._title)


    def parent(self):
        return self._parent


    def is_disk_folder(self):
        return True


    def _load_hosts_on_demand(self):
        if self._hosts == None:
            self._load_hosts()


    def _load_hosts(self):
        self._locked_hosts = False

        self._hosts = {}
        if not os.path.exists(self.hosts_file_path()):
            return

        variables = self._load_hosts_file()
        self._locked_hosts = variables["_lock"]

        # Add entries in clusters{} to all_hosts, prepare cluster to node mapping
        nodes_of = {}
        for cluster_with_tags, nodes in variables["clusters"].items():
            variables["all_hosts"].append(cluster_with_tags)
            nodes_of[cluster_with_tags.split('|')[0]] = nodes

        # Build list of individual hosts
        for host_name_with_tags in variables["all_hosts"]:
            parts = host_name_with_tags.split('|')
            host_name = parts[0]
            host_tags = self._cleanup_host_tags(parts[1:])
            host = self._create_host_from_variables(host_name, host_tags, nodes_of, variables)
            self._hosts[host_name] = host


    def _create_host_from_variables(self, host_name, host_tags, nodes_of, variables):
        cluster_nodes = nodes_of.get(host_name)

        # If we have a valid entry in host_attributes then the hosts.mk file contained
        # valid WATO information from a last save and we use that
        if host_name in variables["host_attributes"]:
            attributes = variables["host_attributes"][host_name]

            # Old WATO was saving "site" attribute with value of None. Skip this key.
            if "site" in attributes and attributes["site"] == None:
                del attributes["site"]

        else:
            # Otherwise it is an import from some manual old version of from some
            # CMDB and we reconstruct the attributes. That way the folder inheritance
            # information is not available and all tags are set explicitely
            attributes = {}
            alias = self._get_alias_from_extra_conf(host_name, variables)
            if alias != None:
                attributes["alias"] = alias
            attributes.update(self._get_attributes_from_tags(host_tags))
            for attribute_key, config_dict in [
                ( "ipaddress",      "ipaddresses" ),
                ( "ipv6address",    "ipv6addresses" ),
                ( "snmp_community", "explicit_snmp_communities" ),
            ]:
                if host_name in variables[config_dict]:
                    attributes[attribute_key] = variables[config_dict][host_name]

        return Host(self, host_name, attributes, cluster_nodes)


    def _load_hosts_file(self):
        variables = {
            "FOLDER_PATH"               : "",
            "ALL_HOSTS"                 : ALL_HOSTS,
            "ALL_SERVICES"              : ALL_SERVICES,
            "all_hosts"                 : [],
            "clusters"                  : {},
            "ipaddresses"               : {},
            "ipv6addresses"             : {},
            "explicit_snmp_communities" : {},
            "extra_host_conf"           : { "alias" : [] },
            "extra_service_conf"        : { "_WATO" : [] },
            "host_attributes"           : {},
            "host_contactgroups"        : [],
            "service_contactgroups"     : [],
            "_lock"                     : False,
        }
        execfile(self.hosts_file_path(), variables, variables)
        return variables


    def save_hosts(self):
        self.need_unlocked_hosts()
        self.need_permission("write")
        if self._hosts != None:
            self._save_hosts_file()
        call_hook_hosts_changed(self)


    def _save_hosts_file(self):
        self._ensure_folder_directory()
        if not self.has_hosts():
            if os.path.exists(self.hosts_file_path()):
                os.remove(self.hosts_file_path())
            return

        out = create_user_file(self.hosts_file_path(), 'w')
        out.write(wato_fileheader())

        all_hosts = [] # list of [Python string for all_hosts]
        clusters = [] # tuple list of (Python string, nodes)
        ipv4_addresses = {}
        ipv6_addresses = {}
        explicit_snmp_communities = {}
        hostnames = self.hosts().keys()
        hostnames.sort()
        custom_macros = {} # collect value for attributes that are to be present in Nagios
        cleaned_hosts = {}

        for hostname in hostnames:
            host = self.hosts()[hostname]
            effective = host.effective_attributes()
            cleaned_hosts[hostname] = host.attributes()

            tags = host.tags()
            tagstext = "|".join(list(tags))
            if tagstext:
                tagstext += "|"
            hostentry = '"%s|%swato|/" + FOLDER_PATH + "/"' % (hostname, tagstext)

            if host.is_cluster():
                clusters.append((hostentry, host.cluster_nodes()))
            else:
                all_hosts.append(hostentry)

            for attribute_name, dictionary in [
                ( "ipaddress", ipv4_addresses ),
                ( "ipv6address", ipv6_addresses ),
                ( "snmp_community", explicit_snmp_communities )
            ]:
                value = effective.get(attribute_name)
                if value:
                    dictionary[hostname] = value

            # Create contact group rule entries for hosts with explicitely set values
            # Note: since the type if this entry is a list, not a single contact group, all other list
            # entries coming after this one will be ignored. That way the host-entries have
            # precedence over the folder entries.

            if host.has_explicit_attribute("contactgroups"):
                 cgconfig = convert_cgroups_from_tuple(host.attribute("contactgroups"))
                 cgs = cgconfig["groups"]
                 if cgs and cgconfig["use"]:
                     out.write("\nhost_contactgroups += [\n")
                     for cg in cgs:
                         out.write('    ( %r, [%r] ),\n' % (cg, hostname))
                     out.write(']\n\n')

                     if cgconfig.get("use_for_services"):
                         out.write("\nservice_contactgroups += [\n")
                         for cg in cgs:
                             out.write('    ( %r, [%r], ALL_SERVICES ),\n' % (cg, hostname))
                         out.write(']\n\n')


            for attr, topic in all_host_attributes():
                attrname = attr.name()
                if attrname in effective:
                    custom_varname = attr.nagios_name()
                    if custom_varname:
                        value = effective.get(attrname)
                        nagstring = attr.to_nagios(value)
                        if nagstring != None:
                            if custom_varname not in custom_macros:
                                custom_macros[custom_varname] = {}
                            custom_macros[custom_varname][hostname] = nagstring

        if len(all_hosts) > 0:
            out.write("all_hosts += [\n")
            for entry in all_hosts:
                out.write('  %s,\n' % entry)
            out.write("]\n")

        if len(clusters) > 0:
            out.write("\nclusters.update({")
            for entry, nodes in clusters:
                out.write('\n  %s : %s,\n' % (entry, repr(nodes)))
            out.write("})\n")

        if len(ipv4_addresses) > 0:
            out.write("\n# Explicit IPv4 addresses\n")
            out.write("ipaddresses.update(")
            out.write(pprint.pformat(ipv4_addresses))
            out.write(")\n")

        if len(ipv6_addresses) > 0:
            out.write("\n# Explicit IPv6 addresses\n")
            out.write("ipv6addresses.update(")
            out.write(pprint.pformat(ipv6_addresses))
            out.write(")\n")

        if len(explicit_snmp_communities) > 0:
            out.write("\n# Explicit SNMP communities\n")
            out.write("explicit_snmp_communities.update(")
            out.write(pprint.pformat(explicit_snmp_communities))
            out.write(")")
        out.write("\n")

        for custom_varname, entries in custom_macros.items():
            macrolist = []
            for hostname, nagstring in entries.items():
                macrolist.append((nagstring, [hostname]))
            if len(macrolist) > 0:
                out.write("\n# Settings for %s\n" % custom_varname)
                out.write("extra_host_conf.setdefault(%r, []).extend(\n" % custom_varname)
                out.write("  %s)\n" % pprint.pformat(macrolist))

        # If the contact groups of the host are set to be used for the monitoring,
        # we create an according rule for the folder and an according rule for
        # each host that has an explicit setting for that attribute.
        permitted_groups, contact_groups, use_for_services = self.groups()
        if contact_groups:
            out.write("\nhost_contactgroups.append(\n"
                      "  ( %r, [ '/' + FOLDER_PATH + '/' ], ALL_HOSTS ))\n" % list(contact_groups))
            if use_for_services:
                # Currently service_contactgroups requires single values. Lists are not supported
                for cg in contact_groups:
                    out.write("\nservice_contactgroups.append(\n"
                              "  ( %r, [ '/' + FOLDER_PATH + '/' ], ALL_HOSTS, ALL_SERVICES ))\n" % cg)


        # Write information about all host attributes into special variable - even
        # values stored for check_mk as well.
        out.write("\n# Host attributes (needed for WATO)\n")
        out.write("host_attributes.update(\n%s)\n" % pprint.pformat(cleaned_hosts))


    # Remove dynamic tags like "wato" and the folder path.
    def _cleanup_host_tags(self, tags):
        return [ tag for tag in tags if
                 tag not in [ "wato", "//" ]
                     and not tag.startswith("/wato/") ]


    def _get_attributes_from_tags(self, host_tags):
        # Retrieve setting for each individual host tag. This is needed for
        # reading in hosts.mk files where host_attributes is missing. Can
        # we drop this one day?
        attributes = {}
        for attr, topic in all_host_attributes():
            if isinstance(attr, HostTagAttribute):
                tagvalue = attr.get_tag_value(host_tags)
                attributes[attr.name()] = tagvalue
        return attributes


    def _get_alias_from_extra_conf(self, host_name, variables):
        aliases = self._host_extra_conf(host_name, variables["extra_host_conf"]["alias"])
        if len(aliases) > 0:
            return aliases[0]
        else:
            return


    # This is a dummy implementation which works without tags
    # and implements only a special case of Check_MK's real logic.
    def _host_extra_conf(self, host_name, conflist):
        for value, hostlist in conflist:
            if host_name in hostlist:
                return [value]
        return []


    def _load(self):
        wato_info               = self._load_wato_info()
        self._title             = wato_info.get("title", self._fallback_title())
        self._attributes        = wato_info.get("attributes", {})
        self._locked            = wato_info.get("lock", False)
        self._locked_subfolders = wato_info.get("lock_subfolders", False)

        if "num_hosts" in wato_info:
            self._num_hosts         = wato_info.get("num_hosts", None)
        else:
            self._num_hosts = len(self.hosts())
            self._save_wato_info()


    def _load_wato_info(self):
        if os.path.exists(self.wato_info_path()):
            return eval(file(self.wato_info_path()).read())
        else:
            return {}


    def save(self):
        self._save_wato_info()
        Folder.invalidate_caches()


    def _save_wato_info(self):
        self._ensure_folder_directory()
        wato_info = {
            "title"           : self._title,
            "attributes"      : self._attributes,
            "num_hosts"       : self._num_hosts,
            "lock"            : self._locked,
            "lock_subfolders" : self._locked_subfolders,
        }
        try:
            file(self.wato_info_path(), "w").write("%r\n" % wato_info)
        except IOError, e:
            if e.errno == 13: # Permission denied
                raise MKGeneralException(_("Failed to write to the WATO folder '%s': %s. "
                                           "Please check the filesystems permissions of this "
                                           "folder.") % (self.title(), e))
            else:
                raise


    def _ensure_folder_directory(self):
        if not os.path.exists(self.filesystem_path()):
            make_nagios_directories(self.filesystem_path())


    def _fallback_title(self):
        if self.is_root():
            return _("Main directory")
        else:
            return self.name()


    def load_subfolders(self):
        dir_path = wato_root_dir + self.path()
        for entry in os.listdir(dir_path):
            subfolder_dir = dir_path + "/" + entry
            if os.path.isdir(subfolder_dir):
                if self.path():
                    subfolder_path = self.path() + "/" + entry
                else:
                    subfolder_path = entry
                self._subfolders[entry] = Folder(entry, subfolder_path, self)


    def wato_info_path(self):
        return self.filesystem_path() + "/.wato"


    def hosts_file_path(self):
        return self.filesystem_path() + "/hosts.mk"


    def rules_file_path(self):
        return self.filesystem_path() + "/rules.mk"


    def add_to_dictionary(self, dictionary):
        dictionary[self.path()] = self
        for subfolder in self._subfolders.values():
            subfolder.add_to_dictionary(dictionary)


    def drop_caches(self):
        self._choices_for_moving_host = None
        for subfolder in self._subfolders.values():
            subfolder.drop_caches()


    # .-----------------------------------------------------------------------.
    # | ELEMENT ACCESS                                                        |
    # '-----------------------------------------------------------------------'

    def name(self):
        return self._name


    def title(self):
        return self._title


    def filesystem_path(self):
        return (wato_root_dir + self.path()).rstrip("/")


    def path(self):
        if self.is_root():
            return ""
        elif self.parent().is_root():
            return self.name()
        else:
            return self.parent().path() + "/" + self.name()


    def hosts(self):
        self._load_hosts_on_demand()
        return self._hosts


    def num_hosts(self):
        # Do *not* load hosts here! This method must kept cheap
        return self._num_hosts


    def num_hosts_recursively(self):
        num = self.num_hosts()
        for subfolder in self.subfolders().values():
            num += subfolder.num_hosts_recursively()
        return num


    def all_hosts_recursively(self):
        hosts = {}
        hosts.update(self.hosts())
        for subfolder in self.subfolders().values():
            hosts.update(subfolder.all_hosts_recursively())
        return hosts


    def subfolders(self):
        return self._subfolders


    def subfolder(self, name):
        return self._subfolders[name]


    def subfolder_by_title(self, title):
        for subfolder in self.subfolders().values():
            if subfolder.title() == title:
                return subfolder


    def has_subfolder(self, name):
        return name in self._subfolders


    def has_subfolders(self):
        return len(self._subfolders) > 0


    def subfolder_choices(self):
        return [ (subfolder.path(), subfolder.title())
                 for subfolder in self.subfolders().values() ]


    def recursive_subfolder_choices(self, current_depth=0):
        if current_depth:
            title_prefix = (u"\u00a0" * 6 * current_depth) + u"\u2514\u2500 "
        else:
            title_prefix = ""
        sel = [ (self.path(), HTML(title_prefix + html.attrencode(self.title()))) ]

        for subfolder in self.subfolders_sorted_by_title():
            sel += subfolder.recursive_subfolder_choices(current_depth + 1)
        return sel


    def choices_for_moving_folder(self):
        return self._choices_for_moving("folder")


    def choices_for_moving_host(self):
        if self._choices_for_moving_host != None:
            return self._choices_for_moving_host # Cached
        else:
            self._choices_for_moving_host = self._choices_for_moving("host")
            return self._choices_for_moving_host


    def _choices_for_moving(self, what):
        choices = []
        for folder_path, folder in Folder.all_folders().items():
            if not folder.may("write"):
                continue
            if folder.is_same_as(self):
                continue # do not move into itself

            if what == "folder":
                if folder.is_same_as(self.parent()):
                    continue # We are already in that folder
                if folder.name() in folder.subfolders():
                    continue # naming conflict
                if self.is_transitive_parent_of(folder):
                    continue # we cannot be moved in our child folder

            msg = "/".join(folder.title_path_without_root())
            choices.append((folder_path, msg))

        choices.sort(cmp=lambda a,b: cmp(a[1].lower(), b[1].lower()))
        return choices


    def subfolders_sorted_by_title(self):
        return sorted(self.subfolders().values(), cmp=lambda a,b: cmp(a.title(), b.title()))


    def site_id(self):
        if "site" in self._attributes:
            return self._attributes["site"]
        elif self.has_parent():
            return self.parent().site_id()
        else:
            return default_site()


    def all_site_ids(self):
        site_ids = set()
        self._add_all_sites_to_set(site_ids)
        return site_ids


    def title_path(self, withlinks = False):
        titles = []
        for folder in self.parent_folder_chain() + [ self ]:
            title = folder.title()
            if withlinks:
                title = "<a href='wato.py?mode=folder&folder=%s'>%s</a>" % (folder.path(), title)
            titles.append(title)
        return titles


    def title_path_without_root(self):
        if self.is_root():
            return [ self.title() ]
        else:
            return self.title_path()[1:]


    def alias_path(self, show_main=True):
        if show_main:
            return " / ".join(self.title_path())
        else:
            return " / ".join(self.title_path_without_root())


    def effective_attributes(self):
        effective = {}
        for folder in self.parent_folder_chain():
            effective.update(folder.attributes())
        effective.update(self.attributes())

        # now add default values of attributes for all missing values
        for host_attribute, topic in all_host_attributes():
            attrname = host_attribute.name()
            if attrname not in effective:
                effective.setdefault(attrname, host_attribute.default_value())

        return effective


    def groups(self, host=None):
        # CLEANUP: this method is also used for determining host permission
        # in behalv of Host::groups(). Not nice but was done for avoiding
        # code duplication
        permitted_groups = set([])
        host_contact_groups = set([])
        if host:
            effective_folder_attributes = host.effective_attributes()
        else:
            effective_folder_attributes = self.effective_attributes()
        cgconf = get_folder_cgconf_from_attributes(effective_folder_attributes)

        # First set explicit groups
        permitted_groups.update(cgconf["groups"])
        if cgconf["use"]:
            host_contact_groups.update(cgconf["groups"])

        if host:
            parent = self
        else:
            parent = self.parent()

        while parent:
            effective_folder_attributes = parent.effective_attributes()
            parconf = get_folder_cgconf_from_attributes(effective_folder_attributes)
            parent_permitted_groups, parent_host_contact_groups, parent_use_for_services = parent.groups()

            if parconf["recurse_perms"]: # Parent gives us its permissions
                permitted_groups.update(parent_permitted_groups)

            if parconf["recurse_use"]:   # Parent give us its contact groups
                host_contact_groups.update(parent_host_contact_groups)

            parent = parent.parent()

        return permitted_groups, host_contact_groups, cgconf.get("use_for_services", False)


    def find_host_recursively(self, host_name):
        host = self.host(host_name)
        if host:
            return host

        for subfolder in self.subfolders().values():
            host = subfolder.find_host_recursively(host_name)
            if host:
                return host


    def user_needs_permission(self, user_id, how):
        if config.user_may(user_id, "wato.all_folders"):
            return
        if how == "read" and config.user_may(user_id, "wato.see_all_folders"):
            return

        permitted_groups, folder_contactgroups, use_for_services = self.groups()
        user_contactgroups = userdb.contactgroups_of_user(user_id)

        for c in user_contactgroups:
            if c in permitted_groups:
                return

        reason = _("Sorry, you have no permissions to the folder <b>%s</b>.") % self.alias_path()
        if not permitted_groups:
            reason += " " + _("The folder is not permitted for any contact group.")
        else:
            reason += " " + _("The folder's permitted contact groups are <b>%s</b>.") % ", ".join(permitted_groups)
            if user_contactgroups:
                reason += " " + _("Your contact groups are <b>%s</b>.") %  ", ".join(user_contactgroups)
            else:
                reason += " " + _("But you are not a member of any contact group.")
        reason += " " + _("You may enter the folder as you might have permission on a subfolders, though.")
        raise MKAuthException(reason)


    def need_recursive_permission(self, how):
        self.need_permission(how)
        if how == "write":
            self.need_unlocked()
            self.need_unlocked_subfolders()
            self.need_unlocked_hosts()

        for subfolder in self.subfolders().values():
            subfolder.need_recursive_permission(how)


    def need_unlocked(self):
        if self.locked():
            raise MKAuthException(_("Sorry, you cannot edit the folder %s. It is locked.") % self.title())


    def need_unlocked_hosts(self):
        if self.locked_hosts():
            raise MKAuthException(_("Sorry, the hosts in the folder %s are locked.") % self.title())


    def need_unlocked_subfolders(self):
        if self.locked_subfolders():
            raise MKAuthException(_("Sorry, the sub folders in the folder %s are locked.") % self.title())


    def url(self, add_vars = []):
        url_vars = [ ("folder", self.path()) ]
        have_mode = False
        for varname, value in add_vars:
            if varname == "mode":
                have_mode = True
                break
        if not have_mode:
            url_vars.append(("mode", "folder"))
        if html.var("debug") == "1":
            add_vars.append(("debug", "1"))
        url_vars += add_vars
        return html.makeuri_contextless(url_vars)


    def edit_url(self, backfolder=None):
        if backfolder == None:
            if self.has_parent():
                backfolder = self.parent()
            else:
                backfolder = self
        return html.makeuri_contextless([
            ("mode", "editfolder"),
            ("folder", self.path()),
            ("backfolder", backfolder.path()),
        ])


    def locked(self):
        return self._locked


    def locked_subfolders(self):
        return self._locked_subfolders


    def locked_hosts(self):
        self._load_hosts_on_demand()
        return self._locked_hosts


    # Returns:
    #  None:      No network scan is enabled.
    #  timestamp: Next planned run according to config.
    def next_network_scan_at(self):
        if "network_scan" in self._attributes:
            interval = self._attributes["network_scan"]["scan_interval"]
            last_end = self._attributes.get("network_scan_result", {}).get("end", None)
            if last_end == None:
                return time.time()
            else:
                return last_end + interval


    # .-----------------------------------------------------------------------.
    # | MODIFICATIONS                                                         |
    # |                                                                       |
    # | These methods are for being called by actual WATO modules when they   |
    # | want to modify folders and hosts. They all check permissions and      |
    # | locking. They may raise MKAuthException or MKUserError.               |
    # |                                                                       |
    # | Folder permissions: Creation and deletion of subfolders needs write   |
    # | permissions in the parent folder (like in Linux).                     |
    # |                                                                       |
    # | Locking: these methods also check locking. Locking is for preventing  |
    # | changes in files that are created by third party applications.        |
    # | A folder has three lock attributes:                                   |
    # |                                                                       |
    # | - locked_hosts() -> hosts.mk file in the folder must not be modified  |
    # | - locked()       -> .wato file in the folder must not be modified     |
    # | - locked_subfolders() -> No subfolders may be created/deleted         |
    # |                                                                       |
    # | Sidebar: some sidebar snapins show the WATO folder tree. Everytime    |
    # | the tree changes the sidebar needs to be reloaded. This is done here. |
    # |                                                                       |
    # | Validation: these methods do *not* validate the parameters for syntax.|
    # | This is the task of the actual WATO modes or the API.                 |
    # '-----------------------------------------------------------------------'

    def create_subfolder(self, name, title, attributes):
        # 1. Check preconditions
        config.need_permission("wato.manage_folders")
        self.need_permission("write")
        self.need_unlocked_subfolders()
        must_be_in_contactgroups(attributes.get("contactgroups"))

        # 2. Actual modification
        new_subfolder = Folder(name, parent_folder=self, title=title, attributes=attributes)
        self._subfolders[name] = new_subfolder
        new_subfolder.save()
        log_pending(AFFECTED, new_subfolder, "new-folder", _("Created new folder %s") % new_subfolder.alias_path())
        call_hook_folder_created(new_subfolder)
        need_sidebar_reload()
        return new_subfolder


    def delete_subfolder(self, name):
        # 1. Check preconditions
        config.need_permission("wato.manage_folders")
        self.need_permission("write")
        self.need_unlocked_subfolders()

        # 2. Actual modification
        subfolder = self.subfolder(name)
        subfolder.mark_hosts_dirty()
        call_hook_folder_deleted(subfolder)
        log_pending(AFFECTED, self, "delete-folder", _("Deleted folder %s") % subfolder.alias_path())
        self._remove_subfolder(name)
        shutil.rmtree(subfolder.filesystem_path())
        Folder.invalidate_caches()
        need_sidebar_reload()


    def move_subfolder_to(self, subfolder, target_folder):
        # 1. Check preconditions
        config.need_permission("wato.manage_folders")
        self.need_permission("write")
        self.need_unlocked_subfolders()
        target_folder.need_permission("write")
        target_folder.need_unlocked_subfolders()
        subfolder.need_recursive_permission("write") # Inheritance is changed
        if os.path.exists(target_folder.filesystem_path() + "/" + subfolder.name()):
            raise MKUserError(None, _("Cannot move folder: A folder with this name already exists in the target folder."))

        # 2. Actual modification
        subfolder.mark_hosts_dirty()
        old_filesystem_path = subfolder.filesystem_path()
        del self._subfolders[subfolder.name()]
        subfolder._parent = target_folder
        target_folder._subfolders[subfolder.name()] = subfolder
        shutil.move(old_filesystem_path, subfolder.filesystem_path())
        subfolder.rewrite_hosts_files() # fixes changed inheritance
        subfolder.mark_hosts_dirty()
        Folder.invalidate_caches()
        log_pending(AFFECTED, subfolder, "move-folder",
            _("Moved folder %s to %s") % (subfolder.alias_path(), target_folder.alias_path()))
        need_sidebar_reload()


    def edit(self, new_title, new_attributes):
        # 1. Check preconditions
        self.need_permission("write")
        self.need_unlocked()

        # For changing contact groups user needs write permission on parent folder
        if get_folder_cgconf_from_attributes(new_attributes) != \
           get_folder_cgconf_from_attributes(self.attributes()):
            must_be_in_contactgroups(self.attributes().get("contactgroups"))
            if self.has_parent():
                if not self.parent().may("write"):
                    raise MKAuthException(_("Sorry. In order to change the permissions of a folder you need write "
                                            "access to the parent folder."))

        # 2. Actual modification

        # Due to a change in the attribute "site" a host can move from
        # one site to another. In that case both sites need to be marked
        # dirty. Therefore we first mark dirty according to the current
        # host->site mapping and after the change we mark again according
        # to the new mapping.
        self.mark_hosts_dirty()

        self._title      = new_title
        self._attributes = new_attributes

        # Due to changes in folder/file attributes, host files
        # might need to be rewritten in order to reflect Changes
        # in Nagios-relevant attributes.
        self.save()
        self.rewrite_hosts_files()

        self.mark_hosts_dirty()
        log_pending(AFFECTED, self, "edit-folder", _("Edited properties of folder %s") % self.title())


    def create_hosts(self, entries):
        # 1. Check preconditions
        config.need_permission("wato.manage_hosts")
        self.need_unlocked_hosts()
        self.need_permission("write")

        for host_name, attributes, cluster_nodes in entries:
            must_be_in_contactgroups(attributes.get("contactgroups"))
            existing_host = Host.host(host_name)
            if existing_host:
                raise MKUserError("host", _('A host with the name <b><tt>%s</tt></b> already '
                       'exists in the folder <a href="%s">%s</a>.') %
                         (host_name, existing_host.folder().url(), existing_host.folder().alias_path()))

        # 2. Actual modification
        self._load_hosts_on_demand()
        for host_name, attributes, cluster_nodes in entries:
            host = Host(self, host_name, attributes, cluster_nodes)
            self._hosts[host_name] = host
            self._num_hosts = len(self._hosts)
            host.mark_dirty()
            log_pending(AFFECTED, host, "create-host", _("Created new host %s.") % host_name)
        self._save_wato_info() # num_hosts has changed
        self.save_hosts()


    def delete_hosts(self, host_names):
        # 1. Check preconditions
        config.need_permission("wato.manage_hosts")
        self.need_unlocked_hosts()
        self.need_permission("write")

        # 2. Actual modification
        for host_name in host_names:
            host = self.hosts()[host_name]
            host.mark_dirty()
            del self._hosts[host_name]
            self._num_hosts = len(self._hosts)
            log_pending(AFFECTED, host, "delete-host", _("Deleted host %s") % host_name)
        self._save_wato_info() # num_hosts has changed
        self.save_hosts()


    def move_hosts(self, host_names, target_folder):
        # 1. Check preconditions
        config.need_permission("wato.manage_hosts")
        config.need_permission("wato.edit_hosts")
        config.need_permission("wato.move_hosts")
        self.need_permission("write")
        self.need_unlocked_hosts()
        target_folder.need_permission("write")
        target_folder.need_unlocked_hosts()

        # 2. Actual modification
        for host_name in host_names:
            host = self.host(host_name)
            host.mark_dirty()
            self._remove_host(host)
            target_folder._add_host(host)
            host.mark_dirty()
            log_pending(AFFECTED, host, "move-host", _("Moved host from %s to %s") %
                (self.path(), target_folder.path()))

        self._save_wato_info() # num_hosts has changed
        self.save_hosts()
        target_folder._save_wato_info()
        target_folder.save_hosts()


    def rename_host(self, oldname, newname):
        # 1. Check preconditions
        config.need_permission("wato.manage_hosts")
        config.need_permission("wato.edit_hosts")
        self.need_unlocked_hosts()
        host = self.hosts()[oldname]
        host.need_permission("write")

        # 2. Actual modification
        host.rename(newname)
        del self._hosts[oldname]
        self._hosts[newname] = host
        host.mark_dirty()
        self.save_hosts()


    def rename_parent(self, oldname, newname):
        # Must not fail because of auth problems. Auth is check at the
        # actually renamed host.
        changed = rename_host_in_list(self._attributes["parents"], oldname, newname)
        self.mark_hosts_dirty()
        self.save_hosts()
        self.save()
        return changed


    def mark_hosts_dirty(self, need_sync=True, need_restart=True):
        for site_id in self.all_site_ids():
            changes = {}
            if need_sync and not config.site_is_local(site_id):
                changes["need_sync"] = True
            if need_restart: # Is this parameter used at all?
                changes["need_restart"] = True
            update_replication_status(site_id, changes)


    def rewrite_hosts_files(self):
        self._rewrite_hosts_file()
        for subfolder in self.subfolders().values():
            subfolder.rewrite_hosts_files()


    def _add_host(self, host):
        self._load_hosts_on_demand()
        self._hosts[host.name()] = host
        host._folder = self
        self._num_hosts = len(self._hosts)


    def _remove_host(self, host):
        self._load_hosts_on_demand()
        del self._hosts[host.name()]
        host._folder = None
        self._num_hosts = len(self._hosts)


    def _remove_subfolder(self, name):
        del self._subfolders[name]


    def _add_all_sites_to_set(self, site_ids):
        site_ids.add(self.site_id())
        for host in self.hosts().values():
            site_ids.add(host.site_id())
        for subfolder in self.subfolders().values():
            subfolder._add_all_sites_to_set(site_ids)


    def _rewrite_hosts_file(self):
        self._load_hosts_on_demand()
        self.save_hosts()



    # .-----------------------------------------------------------------------.
    # | HTML Generation                                                       |
    # '-----------------------------------------------------------------------'

    def show_locking_information(self):
        self._load_hosts_on_demand()
        lock_messages = []

        # Locked hosts
        if self._locked_hosts == True:
            lock_messages.append(_("Hosts attributes are locked "
                                    "(You cannot create, edit or delete hosts in this folder)"))
        elif self._locked_hosts:
            lock_messages.append(self._locked_hosts)

        # Locked folder attributes
        if self._locked == True:
            lock_messages.append(_("Folder attributes are locked "
                                   "(You cannot edit the attributes of this folder)"))
        elif self._locked:
            lock_messages.append(self._locked)

        # Also subfolders are locked
        if self._locked_subfolders:
            lock_messages.append(_("Subfolders are locked "
                                   "(You cannot create or remove folders in this folder)"))
        elif self._locked_subfolders:
            lock_messages.append(self._locked_subfolders)

        if lock_messages:
            if len(lock_messages) == 1:
                lock_message = lock_messages[0]
            else:
                li_elements = "".join([  "<li>%s</li>" % m for m in lock_messages ])
                lock_message = "<ul>" + li_elements + "</ul>"
            html.show_info(lock_message)



#.
#   .--Search Folder-------------------------------------------------------.
#   |    ____                      _       _____     _     _               |
#   |   / ___|  ___  __ _ _ __ ___| |__   |  ___|__ | | __| | ___ _ __     |
#   |   \___ \ / _ \/ _` | '__/ __| '_ \  | |_ / _ \| |/ _` |/ _ \ '__|    |
#   |    ___) |  __/ (_| | | | (__| | | | |  _| (_) | | (_| |  __/ |       |
#   |   |____/ \___|\__,_|_|  \___|_| |_| |_|  \___/|_|\__,_|\___|_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  A virtual folder representing the result of a search.               |
#   '----------------------------------------------------------------------'
class SearchFolder(BaseFolder):
    @staticmethod
    def criteria_from_html_vars():
        crit = { ".name" : html.var("host_search_host") }
        crit.update(collect_attributes("host_search", do_validate = False, varprefix="host_search_"))
        return crit


    # .--------------------------------------------------------------------.
    # | CONSTRUCTION                                                       |
    # '--------------------------------------------------------------------'

    def __init__(self, base_folder, criteria):
        self._criteria = criteria
        self._base_folder = base_folder
        self._found_hosts = None
        self._name = None


    def __repr__(self):
        return "SearchFolder(%r, %s)" % (self._base_folder.path(), self._name)


    # .--------------------------------------------------------------------.
    # | ACCESS                                                             |
    # '--------------------------------------------------------------------'

    def attributes(self):
        return {}


    def parent(self):
        return self._base_folder


    def is_search_folder(self):
        return True


    def user_needs_permission(self, user_id, how):
        pass


    def title(self):
        return _("Search results for folder %s") % self._base_folder.title()


    def hosts(self):
        if self._found_hosts == None:
            self._found_hosts = self._search_hosts_recursively(self._base_folder)
        return self._found_hosts


    def locked_hosts(self):
        return False


    def locked_subfolders(self):
        return False


    def show_locking_information(self):
        pass


    def has_subfolders(self):
        return False


    def choices_for_moving_host(self):
        return Folder.folder_choices()


    def path(self):
        if self._name:
            return self._base_folder.path() + "//search:" + self._name
        else:
            return self._base_folder.path() + "//search"


    def url(self, add_vars = []):
        url_vars = [("host_search", "1")] + add_vars

        for varname, value in html.all_vars().items():
            if varname.startswith("host_search_") \
                or varname.startswith("_change"):
                url_vars.append((varname, value))
        return self.parent().url(url_vars)



    # .--------------------------------------------------------------------.
    # | ACTIONS                                                            |
    # '--------------------------------------------------------------------'

    def delete_hosts(self, host_names):
        auth_errors = []
        for folder, host_names in self._group_hostnames_by_folder(host_names):
            try:
                folder.delete_hosts(host_names)
            except MKAuthException, e:
                auth_errors.append(_("<li>Cannot delete hosts in folder %s: %s</li>") % (folder.alias_path(), e))
        self._invalidate_search()
        if auth_errors:
            raise MKAuthException(HTML(_("Some hosts could not be deleted:<ul>%s</ul>") % "".join(auth_errors)))


    def move_hosts(self, host_names, target_folder):
        auth_errors = []
        for folder, host_names in self._group_hostnames_by_folder(host_names):
            try:
                folder.move_hosts(host_names, target_folder)
            except MKAuthException, e:
                auth_errors.append(_("<li>Cannot move hosts from folder %s: %s</li>") % (folder.alias_path(), e))
        self._invalidate_search()
        if auth_errors:
            raise MKAuthException(HTML(_("Some hosts could not be moved:<ul>%s</ul>") % "".join(auth_errors)))


    # .--------------------------------------------------------------------.
    # | PRIVATE METHODS                                                    |
    # '--------------------------------------------------------------------'

    def _group_hostnames_by_folder(self, host_names):
        by_folder = {}
        for host_name in host_names:
            host = self.host(host_name)
            by_folder.setdefault(host.folder().path(), []).append(host)

        return [ (hosts[0].folder(), [ host.name() for host in hosts ])
                 for hosts in by_folder.values() ]


    def _search_hosts_recursively(self, in_folder):
        hosts = self._search_hosts(in_folder)
        for subfolder in in_folder.subfolders().values():
            hosts.update(self._search_hosts_recursively(subfolder))
        return hosts


    def _search_hosts(self, in_folder):
        if not in_folder.may("read"):
            return {}

        found = {}
        for host_name, host in in_folder.hosts().items():
            if self._criteria[".name"] and self._criteria[".name"].lower() not in host_name.lower():
                continue

            # Compute inheritance
            effective = host.effective_attributes()

            # Check attributes
            dont_match = False
            for attr, topic in all_host_attributes():
                attrname = attr.name()
                if attrname in self._criteria and  \
                    not attr.filter_matches(self._criteria[attrname], effective.get(attrname), host_name):
                    dont_match = True
                    break

            if not dont_match:
                found[host_name] = host

        return found


    def _invalidate_search(self):
        self._found_hosts = None


#.
#   .--Host----------------------------------------------------------------.
#   |                         _   _           _                            |
#   |                        | | | | ___  ___| |_                          |
#   |                        | |_| |/ _ \/ __| __|                         |
#   |                        |  _  | (_) \__ \ |_                          |
#   |                        |_| |_|\___/|___/\__|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Class representing one host that is managed via WATO. Hosts are     |
#   |  contained in Folders.                                               |
#   '----------------------------------------------------------------------'

class Host(WithPermissionsAndAttributes):
    # .--------------------------------------------------------------------.
    # | STATIC METHODS                                                     |
    # '--------------------------------------------------------------------'

    @staticmethod
    def host(host_name):
        return Folder.root_folder().find_host_recursively(host_name)


    @staticmethod
    def all():
        return Folder.root_folder().all_hosts_recursively()


    @staticmethod
    def host_exists(host_name):
        return Host.host(host_name) != None



    # .--------------------------------------------------------------------.
    # | CONSTRUCTION, LOADING & SAVING                                     |
    # '--------------------------------------------------------------------'

    def __init__(self, folder, host_name, attributes, cluster_nodes):
        WithPermissionsAndAttributes.__init__(self)
        self._folder = folder
        self._name = host_name
        self._attributes = attributes
        self._cluster_nodes = cluster_nodes


    def __repr__(self):
        return "Host(%r)" % (self._name)


    # .--------------------------------------------------------------------.
    # | ELEMENT ACCESS                                                     |
    # '--------------------------------------------------------------------'

    def name(self):
        return self._name


    def alias(self):
        # Alias cannot be inherited, so no need to use effective_attributes()
        return self.attributes().get("alias")


    def folder(self):
        return self._folder


    def locked(self):
        return self.folder().locked_hosts()


    def need_unlocked(self):
        return self.folder().need_unlocked_hosts()


    def is_cluster(self):
        return self._cluster_nodes != None

    def cluster_nodes(self):
        return self._cluster_nodes


    def is_offline(self):
        return self.tag("criticality") == "offline"


    def site_id(self):
        return self._attributes.get("site") or self.folder().site_id()


    def parents(self):
        return self.effective_attribute("parents", [])


    def tags(self):
        # Compute tags from settings of each individual tag. We've got
        # the current value for each individual tag. Also other attributes
        # can set tags (e.g. the SiteAttribute)
        tags = set([])
        effective = self.effective_attributes()
        for attr, topic in all_host_attributes():
            value = effective.get(attr.name())
            tags.update(attr.get_tag_list(value))
        return tags


    def tag(self, taggroup_name):
        effective = self.effective_attributes()
        attribute_name = "tag_" + taggroup_name
        return effective.get(attribute_name)


    def discovery_failed(self):
        return self.attributes().get("inventory_failed", False)


    def validation_errors(self):
        if hooks.registered('validate-host'):
            errors = []
            for hook_function in hooks.get('validate-host'):
                try:
                    hook_function(self)
                except MKUserError, e:
                    errors.append("%s" % e)
            return errors
        else:
            return []


    def effective_attributes(self):
        effective = self.folder().effective_attributes()
        effective.update(self.attributes())
        return effective


    def groups(self):
        return self.folder().groups(self)


    def user_needs_permission(self, user_id, how):
        if config.may("wato.all_folders"):
            return True

        if how == "write":
            config.need_permission("wato.edit_hosts")

        permitted_groups, host_contact_groups, use_for_services = self.groups()
        user_contactgroups = userdb.contactgroups_of_user(user_id)

        for c in user_contactgroups:
            if c in permitted_groups:
                return

        reason = _("Sorry, you have no permission on the host '<b>%s</b>'. The host's contact "
                   "groups are <b>%s</b>, your contact groups are <b>%s</b>.") % \
                   (self.name(), ", ".join(permitted_groups), ", ".join(user_contactgroups))
        raise MKAuthException(reason)



    def edit_url(self):
        return html.makeuri_contextless([
            ("mode", "edit_host"),
            ("folder", self.folder().path()),
            ("host", self.name()),
        ])


    def params_url(self):
        return html.makeuri_contextless([
            ("mode", "object_parameters"),
            ("folder", self.folder().path()),
            ("host", self.name()),
        ])


    def services_url(self):
        return html.makeuri_contextless([
            ("mode", "inventory"),
            ("folder", self.folder().path()),
            ("host", self.name()),
        ])


    def clone_url(self):
        return html.makeuri_contextless([
            ("mode", self.is_cluster() and "newcluster" or "newhost"),
            ("folder", self.folder().path()),
            ("clone", self.name()),
        ])


    # .--------------------------------------------------------------------.
    # | MODIFICATIONS                                                      |
    # |                                                                    |
    # | These methods are for being called by actual WATO modules when they|
    # | want to modify hosts. See details at the comment header in Folder. |
    # '--------------------------------------------------------------------'

    def edit(self, attributes, cluster_nodes):
        # 1. Check preconditions
        if attributes.get("contactgroups") != self._attributes.get("contactgroups"):
            self._need_folder_write_permissions()
        self.need_permission("write")
        self.need_unlocked()
        must_be_in_contactgroups(attributes.get("contactgroups"))

        # 2. Actual modification
        self.mark_dirty()
        self._attributes = attributes
        self._cluster_nodes = cluster_nodes
        self.mark_dirty()
        self.folder().save_hosts()
        log_pending(AFFECTED, self, "edit-host", _("Modified host %s.") % self.name())


    def update_attributes(self, changed_attributes):
        new_attributes = self.attributes().copy()
        new_attributes.update(changed_attributes)
        self.edit(new_attributes, self._cluster_nodes)


    def clean_attributes(self, attrnames_to_clean):
        # 1. Check preconditions
        if "contactgroups" in attrnames_to_clean:
            self._need_folder_write_permissions()
        self.need_unlocked()

        # 2. Actual modification
        self.mark_dirty()
        for attrname in attrnames_to_clean:
            if attrname in self._attributes:
                del self._attributes[attrname]
        self.mark_dirty()
        self.folder().save_hosts()
        log_pending(AFFECTED, self, "edit-host", _("Removed explicit attributes of host %s.") % self.name())


    def _need_folder_write_permissions(self):
        if not self.folder().may("write"):
            raise MKAuthException(_("Sorry. In order to change the permissions of a host you need write "
                                    "access to the folder it is contained in."))


    def clear_discovery_failed(self):
        # 1. Check preconditions
        # We do not check permissions. They are checked during the discovery.
        self.need_unlocked()

        # 2. Actual modification
        self.set_discovery_failed(False)


    def set_discovery_failed(self, how=True):
        # 1. Check preconditions
        # We do not check permissions. They are checked during the discovery.
        self.need_unlocked()

        # 2. Actual modification
        if how:
            if not self._attributes.get("inventory_failed"):
                self._attributes["inventory_failed"] = True
                self.folder().save_hosts()
        else:
            if self._attributes.get("inventory_failed"):
                del self._attributes["inventory_failed"]
                self.folder().save_hosts()


    def mark_dirty(self, need_sync=True):
        site_id = self.site_id()
        changes = {}
        if not config.site_is_local(site_id):
            changes["need_sync"] = need_sync
        changes["need_restart"] = True
        update_replication_status(site_id, changes)


    def rename_cluster_node(self, oldname, newname):
        # We must not check permissions here. Permissions
        # on the renamed host must be sufficient. If we would
        # fail here we would leave an inconsistent state
        changed = rename_host_in_list(self._cluster_nodes, oldname, newname)
        self.mark_dirty()
        self.folder().save_hosts()
        return changed


    def rename_parent(self, oldname, newname):
        # Same is with rename_cluster_node()
        changed = rename_host_in_list(self._attributes["parents"], oldname, newname)
        self.mark_dirty()
        self.folder().save_hosts()
        return changed


    def rename(self, new_name):
        log_pending(AFFECTED, self, "rename-host", _("Renamed host from %s into %s.") % (self.name(), new_name))
        self._name = new_name
        self.mark_dirty()


#.
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A host attribute is something that is inherited from folders to      |
#   | hosts. Examples are the IP address and the host tags.                |
#   '----------------------------------------------------------------------'

class Attribute:
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self, name=None, title=None, help=None, default_value=None):
        self._name = name
        self._title = title
        self._help = help
        self._default_value = default_value

    # Return the name (= identifier) of the attribute
    def name(self):
        return self._name

    # Return the name of the Nagios configuration variable
    # if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")
    def nagios_name(self):
        return None

    # Return the title to be displayed to the user
    def title(self):
        return self._title

    # Return an optional help text
    def help(self):
        return self._help

    # Return the default value for new hosts
    def default_value(self):
        return self._default_value

    # Render HTML code displaying a value
    def paint(self, value, hostname):
        return "", value

    # Whether or not the user is able to edit this attribute. If
    # not, the value is shown read-only (when the user is permitted
    # to see the attribute).
    def may_edit(self):
        return True

    # Wether or not to show this attribute in tables.
    # This value is set by declare_host_attribute
    def show_in_table(self):
        return self._show_in_table

    # Wether or not to show this attribute in the edit form.
    # This value is set by declare_host_attribute
    def show_in_form(self):
        return self._show_in_form

    # Wether or not to make this attribute configurable in
    # files and folders (as defaule value for the hosts)
    def show_in_folder(self):
        return self._show_in_folder

    # Wether or not to make this attribute configurable in
    # the host search form
    def show_in_host_search(self):
        return self._show_in_host_search

    # Wether or not this attribute can be edited after creation
    # of the object
    def editable(self):
        return self._editable

    # Wether it is allowed that a host has no explicit
    # value here (inherited or direct value). An mandatory
    # has *no* default value.
    def is_mandatory(self):
        return False

    # Return information about the user roles we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_roles is set by declare_host_attribute().
    def depends_on_roles(self):
        try:
            return self._depends_on_roles
        except:
            return []

    # Return information about whether or not either the
    # inherited value or the default value should be shown
    # for an attribute.
    # _depends_on_roles is set by declare_host_attribute().
    def show_inherited_value(self):
        try:
            return self._show_inherited_value
        except:
            return True


    # Return information about the host tags we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_tags is set by declare_host_attribute().
    def depends_on_tags(self):
        try:
            return self._depends_on_tags
        except:
            return []

    # Render HTML input fields displaying the value and
    # make it editable. If filter == True, then the field
    # is to be displayed in filter mode (as part of the
    # search filter)
    def render_input(self, varprefix, value):
        pass

    # Create value from HTML variables.
    def from_html_vars(self, varprefix):
        return None


    # Check whether this attribute needs to be validated at all
    # Attributes might be permanently hidden (show_in_form = False)
    # or dynamically hidden by the depends_on_tags, editable features
    def needs_validation(self, for_what):
        if not self.is_visible(for_what):
            return False
        return html.var('attr_display_%s' % self._name, "1") == "1"


    # Gets the type of current view as argument and returns whether or not
    # this attribute is shown in this type of view
    def is_visible(self, for_what):
        if for_what in [ "host", "bulk" ] and not self.show_in_form():
            return False
        elif for_what == "folder" and not self.show_in_folder():
            return False
        elif for_what == "host_search" and not self.show_in_host_search():
            return False
        return True


    # Check if the value entered by the user is valid.
    # This method may raise MKUserError in case of invalid user input.
    def validate_input(self, varprefix):
        pass

    # If this attribute should be present in Nagios as
    # a host custom macro, then the value of that macro
    # should be returned here - otherwise None
    def to_nagios(self, value):
        return None

    # Checks if the give value matches the search attributes
    # that are represented by the current HTML variables.
    def filter_matches(self, crit, value, hostname):
        return crit == value

    # Host tags to set for this host
    def get_tag_list(self, value):
        return []


# A simple text attribute. It is stored in
# a Python unicode string
class TextAttribute(Attribute):
    def __init__(self, name, title, help = None, default_value="",
                 mandatory=False, allow_empty=True, size=25):
        Attribute.__init__(self, name, title, help, default_value)
        self._mandatory = mandatory
        self._allow_empty = allow_empty
        self._size = size

    def paint(self, value, hostname):
        if not value:
            return "", ""
        else:
            return "", value

    def is_mandatory(self):
        return self._mandatory

    def render_input(self, varprefix, value):
        if value == None:
            value = ""
        html.text_input(varprefix + "attr_" + self.name(), value, size = self._size)

    def from_html_vars(self, varprefix):
        value = html.get_unicode_input(varprefix + "attr_" + self.name())
        if value == None:
            value = ""
        return value.strip()

    def validate_input(self, varprefix):
        value = self.from_html_vars(varprefix)
        if self._mandatory and not value:
            raise MKUserError(varprefix + "attr_" + self.name(),
                  _("Please specify a value for %s") % self.title())
        if not self._allow_empty and value.strip() == "":
            raise MKUserError(varprefix + "attr_" + self.name(),
                  _("%s may be missing, if must not be empty if it is set.") % self.title())


    def filter_matches(self, crit, value, hostname):
        if value == None:  # Host does not have this attribute
            value = ""
        return crit.lower() in value.lower()

# A simple text attribute that is not editable by the user.
# It can be used to store context information from other
# systems (e.g. during an import of a host database from
# another system).
class FixedTextAttribute(TextAttribute):
    def __init__(self, name, title, help = None):
        TextAttribute.__init__(self, name, title, help, None)
        self._mandatory = False

    def render_input(self, varprefix, value):
        if value != None:
            html.hidden_field(varprefix + "attr_" + self.name(), value)
            html.write(value)

    def from_html_vars(self, varprefix):
        return html.var(varprefix + "attr_" + self.name())


# A text attribute that is stored in a Nagios custom macro
class NagiosTextAttribute(TextAttribute):
    def __init__(self, name, nag_name, title, help=None, default_value="",
                 mandatory=False, allow_empty=True, size=25):
        TextAttribute.__init__(self, name, title, help, default_value,
                               mandatory, allow_empty, size)
        self.nag_name = nag_name

    def nagios_name(self):
        return self.nag_name

    def to_nagios(self, value):
        if value:
            return value
        else:
            return None

# An attribute for selecting one item out of list using
# a drop down box (<select>). Enumlist is a list of
# pairs of keyword / title. The type of value is string.
# In all cases where no value is defined or the value is
# not in the enumlist, the default value is being used.
class EnumAttribute(Attribute):
    def __init__(self, name, title, help, default_value, enumlist):
        Attribute.__init__(self, name, title, help, default_value)
        self._enumlist = enumlist
        self._enumdict = dict(enumlist)

    def paint(self, value, hostname):
        return "", self._enumdict.get(value, self.default_value())

    def render_input(self, varprefix, value):
        html.select(varprefix + "attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self, varprefix):
        return html.var(varprefix + "attr_" + self.name(), self.default_value())


# A selection dropdown for a host tag
class HostTagAttribute(Attribute):
    def __init__(self, tag_definition):
        # Definition is either triple or 4-tuple (with
        # dependency definition)
        tag_id, title, self._taglist = tag_definition
        name = "tag_" + tag_id
        if len(self._taglist) == 1:
            def_value = None
        else:
            def_value = self._taglist[0][0]
        Attribute.__init__(self, name, title, "", def_value)

    def paint(self, value, hostname):
        # Localize the titles. To make the strings available in the scanned localization
        # files the _() function must also be placed in the configuration files
        # But don't localize empty strings - This empty string is connected to the header
        # of the .mo file
        if len(self._taglist) == 1:
            title = self._taglist[0][1]
            if title:
                title = _(title)
            if value:
                return "", title
            else:
                return "", "%s %s" % (_("not"), title)
        for entry in self._taglist:
            if value == entry[0]:
                return "", entry[1] and _(entry[1]) or ''
        return "", "" # Should never happen, at least one entry should match
                      # But case could occur if tags definitions have been changed.

    def render_input(self, varprefix, value):
        varname = varprefix + "attr_" + self.name()
        if value == None:
            value = html.var(varname,"") # "" is important for tag groups with an empty tag entry

        # Tag groups with just one entry are being displayed
        # as checkboxes
        choices = []
        for e in self._taglist:
            tagvalue = e[0]
            if not tagvalue: # convert "None" to ""
                tagvalue = ""
            if len(e) >= 3: # have secondary tags
                secondary_tags = e[2]
            else:
                secondary_tags = []
            choices.append(("|".join([ tagvalue ] + secondary_tags), e[1] and _u(_(e[1])) or ''))
            if value != "" and value == tagvalue and secondary_tags:
                value = value + "|" + "|".join(secondary_tags)

        if len(choices) == 1:
            html.checkbox(varname, value != "", cssclass = '', onclick='wato_fix_visibility();',
                          add_attr = ["tags=%s"%choices[0][0]], label = choices[0][1])
        else:
            html.select(varname, choices, value, onchange='wato_fix_visibility();')

    def from_html_vars(self, varprefix):
        varname = varprefix + "attr_" + self.name()
        if len(self._taglist) == 1:
            if html.get_checkbox(varname):
                return self._taglist[0][0]
            else:
                return None
        else:
            # strip of secondary tags
            value = html.var(varname).split("|")[0]
            if not value:
                value = None
            return value

    # Special function for computing the setting of a specific
    # tag group from the total list of tags of a host
    def get_tag_value(self, tags):
        for entry in self._taglist:
            if entry[0] in tags:
                return entry[0]
        return None

    # Return list of host tags to set (handles
    # secondary tags)
    def get_tag_list(self, value):
        for entry in self._taglist:
            if entry[0] == value:
                if len(entry) >= 3:
                    taglist = [ value ] + entry[2]
                else:
                    taglist =  [ value ]
                if taglist[0] == None:
                    taglist = taglist[1:]
                return taglist
        return [] # No matching tag


# An attribute using the generic ValueSpec mechanism
class ValueSpecAttribute(Attribute):
    def __init__(self, name, vs):
        Attribute.__init__(self, name)
        self._valuespec = vs

    def title(self):
        return self._valuespec.title()

    def help(self):
        return self._valuespec.help()

    def default_value(self):
        return self._valuespec.default_value()

    def paint(self, value, hostname):
        return "", \
            self._valuespec.value_to_text(value)

    def render_input(self, varprefix, value):
        self._valuespec.render_input(varprefix + self._name, value)

    def from_html_vars(self, varprefix):
        return self._valuespec.from_html_vars(varprefix + self._name)

    def validate_input(self, varprefix):
        value = self.from_html_vars(varprefix)
        self._valuespec.validate_value(value, varprefix + self._name)


# Convert old tuple representation to new dict representation of
# folder's group settings
def convert_cgroups_from_tuple(value):
    if type(value) == dict:
        if "use_for_services" in value:
            return value
        else:
            new_value = {
                "use_for_services" : False,
            }
            new_value.update(value)
            return value

    else:
        return {
            "groups"           : value[1],
            "recurse_perms"    : False,
            "use"              : value[0],
            "use_for_services" : False,
            "recurse_use"      : False,
        }

# Attribute needed for folder permissions
class ContactGroupsAttribute(Attribute):
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self):
        url = "wato.py?mode=rulesets&group=grouping"
        Attribute.__init__(self, "contactgroups", _("Permissions"),
          _("Only members of the contact groups listed here have WATO permission "
            "to the host / folder. If you want, you can make those contact groups "
            "automatically also <b>monitoring contacts</b>. This is completely "
            "optional. Assignment of host and services to contact groups "
            "can be done by <a href='%s'>rules</a> as well.") % url)
        self._default_value = ( True, [] )
        self._contactgroups = None
        self._users = None
        self._loaded_at = None

    def paint(self, value, hostname):
        value = convert_cgroups_from_tuple(value)

        texts = []
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp = lambda a,b: cmp(a[1]['alias'], b[1]['alias']))
        for name, cgroup in items:
            if name in value["groups"]:
                display_name = cgroup.get("alias", name)
                texts.append('<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' % (name, display_name))
        result = ", ".join(texts)
        if texts and value["use"]:
            result += "<span title='%s'><b>*</b></span>" % \
                  _("These contact groups are also used in the monitoring configuration.")
        return "", result

    def render_input(self, varprefix, value):
        value = convert_cgroups_from_tuple(value)

        # If we're just editing a host, then some of the checkboxes will be missing.
        # This condition is not very clean, but there is no other way to savely determine
        # the context.
        is_host = not not html.var("host") or html.var("mode") == "newhost"
        is_search = varprefix == "host_search"

        # Only show contact groups I'm currently in and contact
        # groups already listed here.
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp = lambda a,b: cmp(a[1], b[1]))
        for name, group in items:
            html.checkbox(varprefix + self._name + "_n_" + name, name in value["groups"])
            html.write(' <a href="%s">%s</a><br>' % (folder_preserving_link([("mode", "edit_contact_group"), ("edit", name)]), group['alias'] and group['alias'] or name))
        html.write("<hr>")

        if is_host:
            html.checkbox(varprefix + self._name + "_use", value["use"],
                label = _("Add these contact groups to the host"))

        elif not is_search:
            html.checkbox(varprefix + self._name + "_recurse_perms", value["recurse_perms"],
                label = _("Give these groups also <b>permission on all subfolders</b>"))
            html.write("<hr>")
            html.checkbox(varprefix + self._name + "_use", value["use"],
                label = _("Add these groups as <b>contacts</b> to all hosts in this folder"))
            html.write("<br>")
            html.checkbox(varprefix + self._name + "_recurse_use", value["recurse_use"],
                label = _("Add these groups as <b>contacts in all subfolders</b>"))

        html.write("<hr>")
        html.help(_("With this option contact groups that are added to hosts are always "
               "being added to services, as well. This only makes a difference if you have "
               "assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. "
               "As long as you do not have any such rule a service always inherits all contact groups "
               "from its host."))
        html.checkbox(varprefix + self._name + "_use_for_services", value.get("use_for_services", False),
            label = _("Always add host contact groups also to its services"))


    def load_data(self):
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)

        self._contactgroups = userdb.load_group_information().get("contact", {})

    def from_html_vars(self, varprefix):
        cgs = []
        self.load_data()
        for name in self._contactgroups:
            if html.get_checkbox(varprefix + self._name + "_n_" + name):
                cgs.append(name)
        return {
            "groups"           : cgs,
            "recurse_perms"    : html.get_checkbox(varprefix + self._name + "_recurse_perms"),
            "use"              : html.get_checkbox(varprefix + self._name + "_use"),
            "use_for_services" : html.get_checkbox(varprefix + self._name + "_use_for_services"),
            "recurse_use"      : html.get_checkbox(varprefix + self._name + "_recurse_use"),
        }

    def filter_matches(self, crit, value, hostname):
        value = convert_cgroups_from_tuple(value)
        # Just use the contact groups for searching
        for contact_group in crit["groups"]:
            if contact_group not in value["groups"]:
                return False
        return True


# Global datastructure holding all attributes (in a defined order)
# as pairs of (attr, topic). Topic is the title under which the
# attribute is being displayed. All builtin attributes use the
# topic None. As long as only one topic is used, no topics will
# be displayed. They are useful if you have a great number of
# custom attributes.
g_host_attributes = []

# Dictionary for quick access
g_host_attribute = {}

# Declare attributes with this method
def declare_host_attribute(a, show_in_table = True, show_in_folder = True, show_in_host_search = True,
       topic = None, show_in_form = True, depends_on_tags = [], depends_on_roles = [], editable = True,
       show_inherited_value = True, may_edit = None):

    g_host_attributes.append((a, topic))
    g_host_attribute[a.name()] = a
    a._show_in_table         = show_in_table
    a._show_in_folder        = show_in_folder
    a._show_in_host_search   = show_in_host_search
    a._show_in_form          = show_in_form
    a._show_inherited_value  = show_inherited_value
    a._depends_on_tags       = depends_on_tags
    a._depends_on_roles      = depends_on_roles
    a._editable              = editable

    if may_edit:
        a.may_edit = may_edit


def undeclare_host_attribute(attrname):
    if attrname in g_host_attribute:
        attr = g_host_attribute[attrname]
        del g_host_attribute[attrname]
        global g_host_attributes
        g_host_attributes = [ ha for ha in g_host_attributes if ha[0] != attr ]


def undeclare_all_host_attributes():
    del g_host_attributes[:]


def all_host_attributes():
    return g_host_attributes


def host_attribute(name):
    return g_host_attribute[name]


# Declare an attribute for each host tag configured in multisite.mk
# Also make sure that the tags are reconfigured as soon as the
# configuration of the tags has changed.
currently_configured_host_tags = None

def declare_host_tag_attributes(force=False):
    global currently_configured_host_tags
    global g_host_attributes

    if force or currently_configured_host_tags != configured_host_tags():
        # Remove host tag attributes from list, if existing
        g_host_attributes = [ (attr, topic)
               for (attr, topic)
               in g_host_attributes
               if not attr.name().startswith("tag_") ]

        # Also remove those attributes from the speed-up dictionary host_attribute
        for attr in g_host_attribute.values():
            if attr.name().startswith("tag_"):
                del g_host_attribute[attr.name()]

        for topic, grouped_tags in group_hosttags_by_topic(configured_host_tags()):
            for entry in grouped_tags:
                # if the entry has o fourth component, then its
                # the tag dependency defintion.
                depends_on_tags = []
                depends_on_roles = []
                attr_editable = True
                if len(entry) >= 6:
                    attr_editable = entry[5]
                if len(entry) >= 5:
                    depends_on_roles = entry[4]
                if len(entry) >= 4:
                    depends_on_tags = entry[3]

                if not topic:
                    topic = _('Host tags')

                declare_host_attribute(
                    HostTagAttribute(entry[:3]),
                        show_in_table = False,
                        show_in_folder = True,
                        editable = attr_editable,
                        depends_on_tags = depends_on_tags,
                        depends_on_roles = depends_on_roles,
                        topic = topic)

        currently_configured_host_tags = configured_host_tags()


def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    undeclare_host_attribute(attrname)


# Read attributes from HTML variables
def collect_attributes(for_what, do_validate = True, varprefix=""):
    host = {}
    for attr, topic in all_host_attributes():
        attrname = attr.name()
        if not html.var(for_what + "_change_%s" % attrname, False):
            continue

        if do_validate and attr.needs_validation(for_what):
            attr.validate_input(varprefix)

        host[attrname] = attr.from_html_vars(varprefix)
    return host

#.
#   .--Global configuration------------------------------------------------.
#   |       ____ _       _           _                    __ _             |
#   |      / ___| | ___ | |__   __ _| |   ___ ___  _ __  / _(_) __ _       |
#   |     | |  _| |/ _ \| '_ \ / _` | |  / __/ _ \| '_ \| |_| |/ _` |      |
#   |     | |_| | | (_) | |_) | (_| | | | (_| (_) | | | |  _| | (_| |      |
#   |      \____|_|\___/|_.__/ \__,_|_|  \___\___/|_| |_|_| |_|\__, |      |
#   |                                                          |___/       |
#   +----------------------------------------------------------------------+
#   |  Code for loading and saving global configuration variables. This is |
#   |  not only needed by the WATO for mode for editing these, but e.g.    |
#   |  also in the code for distributed WATO (handling of site specific    |
#   |  globals).
#   '----------------------------------------------------------------------'

def initialize_global_configvars():
    global g_configvars, g_configvar_groups, g_configvar_order
    g_configvars = {}
    g_configvar_groups = {}
    g_configvar_order = {}


g_configvar_domains = {
    "check_mk" : {
        "configdir" : wato_root_dir,
    },
    "multisite" : {
        "configdir" : multisite_dir,
    },
}


def configvars():
    return g_configvars


def configvar_groups():
    return g_configvar_groups


def configvar_order():
    return g_configvar_order

def configvar_domains():
    return g_configvar_domains



# domain is one of "check_mk", "multisite" or "nagios"
def register_configvar(group, varname, valuespec, domain="check_mk",
                       need_restart=False, allow_reset=True, in_global_settings=True):
    g_configvar_groups.setdefault(group, []).append((domain, varname, valuespec))
    g_configvars[varname] = domain, valuespec, need_restart, allow_reset, in_global_settings



# The following keys are available:
# configdir: Directory to store the global.mk in (applies to check_mk, multisite, mkeventd)
# pending:   Handler function to create the pending log entry
# load:      Optional handler to load/parse the file
# save:      Optional handler to save the filea
# in_global_settings: Set to False to hide whole section from global settings dialog
def register_configvar_domain(domain, configdir = None, pending = None, save = None, load = None, in_global_settings = True):
    g_configvar_domains[domain] = {
        'in_global_settings': in_global_settings,
    }
    for k in [ 'configdir', 'pending', 'save', 'load' ]:
        if locals()[k] is not None:
            g_configvar_domains[domain][k] = locals()[k]

# Persistenz: Speicherung der Werte
# - WATO speichert seine Variablen für main.mk in conf.d/wato/global.mk
# - Daten, die der User in main.mk einträgt, müssen WATO auch bekannt sein.
#   Sie werden als Defaultwerte verwendet.
# - Daten, die der User in final.mk oder local.mk einträgt, werden von WATO
#   völlig ignoriert. Der Admin kann hier Werte überschreiben, die man mit
#   WATO dann nicht ändern kann. Und man sieht auch nicht, dass der Wert
#   nicht änderbar ist.
# - WATO muss irgendwie von Check_MK herausbekommen, welche Defaultwerte
#   Variablen haben bzw. welche Einstellungen diese Variablen nach main.mk
#   haben.
# - WATO kann main.mk nicht selbst einlesen, weil dann der Kontext fehlt
#   (Default-Werte der Variablen aus Check_MK und aus den Checks)
# - --> Wir machen eine automation, die alle Konfigurationsvariablen
#   ausgibt.

def load_configuration_settings():
    settings = {}
    for domain, domain_info in g_configvar_domains.items():
        if 'load' in domain_info:
            domain_info['load'](settings)
        else:
            load_configuration_vars(domain_info["configdir"] + "global.mk", settings)
    return settings


def load_configuration_vars(filename, settings):
    if not os.path.exists(filename):
        return {}
    try:
        execfile(filename, settings, settings)
        for varname in settings.keys():
            if varname not in g_configvars:
                del settings[varname]
        return settings
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        return {}


def save_configuration_settings(vars):
    per_domain = {}
    for varname, (domain, valuespec, need_restart, allow_reset, in_global_settings) in g_configvars.items():
        if varname not in vars:
            continue
        per_domain.setdefault(domain, {})[varname] = vars[varname]

    # The global setting wato_enabled is not registered in the configuration domains
    # since the user must not change it directly. It is set by D-WATO on slave sites.
    if "wato_enabled" in vars:
        per_domain.setdefault("multisite", {})["wato_enabled"] = vars["wato_enabled"]

    for domain, domain_info in g_configvar_domains.items():
        if 'save' in domain_info:
            domain_info['save'](per_domain.get(domain, {}))
        else:
            dir = domain_info["configdir"]
            make_nagios_directory(dir)
            save_configuration_vars(per_domain.get(domain, {}), dir + "global.mk")

def save_configuration_vars(vars, filename):
    out = create_user_file(filename, 'w')
    out.write(wato_fileheader())
    for varname, value in vars.items():
        out.write("%s = %s\n" % (varname, pprint.pformat(value)))


#.
#   .--Distributed WATO----------------------------------------------------.
#   |                 ____     __        ___  _____ ___                    |
#   |                |  _ \    \ \      / / \|_   _/ _ \                   |
#   |                | | | |____\ \ /\ / / _ \ | || | | |                  |
#   |                | |_| |_____\ V  V / ___ \| || |_| |                  |
#   |                |____/       \_/\_/_/   \_\_| \___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Code for distributed WATO. Site configuration. Pushing snapshots.   |
#   '----------------------------------------------------------------------'

def get_login_secret(create_on_demand = False):
    path = var_dir + "automation_secret.mk"
    try:
        return eval(file(path).read())
    except:
        if not create_on_demand:
            return None
        secret = get_random_string(32)
        write_settings_file(path, secret)
        return secret


# Returns the ID of our site. This function only works in replication
# mode and looks for an entry connecting to the local socket.
def our_site_id():
    if not is_distributed():
        return None
    for site_id in config.allsites():
        if config.site_is_local(site_id):
            return site_id
    return None


def load_sites():
    try:
        if not os.path.exists(sites_mk):
            return config.default_single_site_configuration()

        vars = { "sites" : {} }
        execfile(sites_mk, vars, vars)

        # Be compatible to old "disabled" value in socket attribute.
        # Can be removed one day.
        for site in vars['sites'].values():
            if site.get('socket') == 'disabled':
                site['disabled'] = True
                del site['socket']

        if not vars["sites"]:
            # There seem to be installations out there which have a sites.mk
            # which has an empty sites dictionary. Apply the default configuration
            # for these sites too.
            return config.default_single_site_configuration()
        else:
            return vars["sites"]


    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (sites_mk, e)))
        return {}



def save_sites(sites, activate=True):
    make_nagios_directory(multisite_dir)

    # Important: even write out sites if it's empty. The global 'sites'
    # variable will otherwise survive in the Python interpreter of the
    # Apache processes.
    out = create_user_file(sites_mk, "w")
    out.write(wato_fileheader())
    out.write("sites = \\\n%s\n" % pprint.pformat(sites))

    # Do not activate when just the site's global settings have
    # been edited
    if activate:
        config.load_config() # make new site configuration active
        update_distributed_wato_file(sites)
        declare_site_attribute()
        Folder.invalidate_caches()
        need_sidebar_reload()

        if config.liveproxyd_enabled:
            save_liveproxyd_config(sites)

        create_nagvis_backends(sites)

        # Call the sites saved hook
        call_hook_sites_saved(sites)


def save_liveproxyd_config(sites):
    path = defaults.default_config_dir + "/liveproxyd.mk"
    out = create_user_file(path, "w")
    out.write(wato_fileheader())

    conf = {}
    for siteid, siteconf in sites.items():
        s = siteconf.get("socket")
        if type(s) == tuple and s[0] == "proxy":
            conf[siteid] = s[1]

    out.write("sites = \\\n%s\n" % pprint.pformat(conf))
    try:
        pidfile = defaults.livestatus_unix_socket + "proxyd.pid"
        pid = int(file(pidfile).read().strip())
        os.kill(pid, 10)
    except Exception, e:
        html.show_error(_("Warning: cannot reload Livestatus Proxy-Daemon: %s" % e))


def create_nagvis_backends(sites):
    if not defaults.omd_root:
        return # skip when not in OMD environment
    cfg = [
        '; MANAGED BY CHECK_MK WATO - Last Update: %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
    ]
    for site_id, site in sites.items():
        if site == defaults.omd_site:
            continue # skip local site, backend already added by omd
        if 'socket' not in site:
            continue # skip sites without configured sockets

        # Handle special data format of livestatus proxy config
        if type(site['socket']) == tuple:
            socket = 'tcp:%s:%d' % site['socket'][1]['socket']
        else:
            socket = site['socket']

        cfg += [
            '',
            '[backend_%s]' % site_id,
            'backendtype="mklivestatus"',
            'socket="%s"' % socket,
        ]

        if site.get("status_host"):
            cfg.append('statushost="%s"' % ':'.join(site['status_host']))

    file('%s/etc/nagvis/conf.d/cmk_backends.ini.php' % defaults.omd_root, 'w').write('\n'.join(cfg))


def create_site_globals_file(siteid, tmp_dir):
    if not os.path.exists(tmp_dir):
        make_nagios_directory(tmp_dir)
    sites = load_sites()
    site = sites[siteid]
    config = site.get("globals", {})

    # Add global setting for disabling WATO right here. It is not
    # available as a normal global option. That would be too dangerous.
    # You could disable WATO on the master very easily that way...
    # The default value is True - even for sites configured with an
    # older version of Check_MK.
    config["wato_enabled"] = not site.get("disable_wato", True)
    file(tmp_dir + "/sitespecific.mk", "w").write("%r\n" % config)


def create_distributed_wato_file(siteid, mode):
    out = create_user_file(defaults.check_mk_configdir + "/distributed_wato.mk", "w")
    out.write(wato_fileheader())
    out.write("# This file has been created by the master site\n"
              "# push the configuration to us. It makes sure that\n"
              "# we only monitor hosts that are assigned to our site.\n\n")
    out.write("distributed_wato_site = '%s'\n" % siteid)


def delete_distributed_wato_file():
    p = defaults.check_mk_configdir + "/distributed_wato.mk"
    # We do not delete the file but empty it. That way
    # we do not need write permissions to the conf.d
    # directory!
    if os.path.exists(p):
        create_user_file(p, "w").write("")


def has_distributed_wato_file():
    return os.path.exists(defaults.check_mk_configdir + "/distributed_wato.mk") \
        and os.stat(defaults.check_mk_configdir + "/distributed_wato.mk").st_size != 0


# Makes sure, that in distributed mode we monitor only
# the hosts that are directly assigned to our (the local)
# site.
def update_distributed_wato_file(sites):
    # Note: we cannot access config.sites here, since we
    # are currently in the process of saving the new
    # site configuration.
    distributed = False
    found_local = False
    for siteid, site in sites.items():
        if site.get("replication"):
            distributed = True
        if config.site_is_local(siteid):
            found_local = True
            create_distributed_wato_file(siteid, site.get("replication"))

    # Remove the distributed wato file
    # a) If there is no distributed WATO setup
    # b) If the local site could not be gathered
    if not distributed: # or not found_local:
        delete_distributed_wato_file()


def do_site_login(site_id, name, password):
    sites = load_sites()
    site = sites[site_id]
    if not name:
        raise MKUserError("_name",
            _("Please specify your administrator login on the remote site."))
    if not password:
        raise MKUserError("_passwd",
            _("Please specify your password."))

    # Trying basic auth AND form based auth to ensure the site login works.
    # Adding _ajaxid makes the web service fail silently with an HTTP code and
    # not output HTML code for an error screen.
    url = site["multisiteurl"] + 'login.py'
    post_data = html.urlencode_vars([
        ('_login', '1'),
        ('_username', name),
        ('_password', password),
        ('_origtarget', 'automation_login.py'),
        ('_plain_error', '1'),
    ])
    response = get_url(url, site.get('insecure', False), name, password, post_data=post_data).strip()
    if '<html>' in response.lower():
        message = _("Authentication to web service failed.<br>Message:<br>%s") % \
            html.strip_tags(html.strip_scripts(response))
        if config.debug:
            message += "<br>" + _("Automation URL:") + " <tt>%s</tt><br>" % url
        raise MKAutomationException(message)
    elif not response:
        raise MKAutomationException(_("Empty response from web service"))
    else:
        try:
            return eval(response)
        except:
            raise MKAutomationException(response)

def upload_file(url, file_path, insecure):
    return get_url(url, insecure, params = ' -F snapshot=@%s' % file_path)

def get_url(url, insecure, user=None, password=None, params = '', post_data = None):
    cred = ''
    if user:
        cred = ' -u %s' % quote_shell_string("%s:%s" % (user, password))

    insecure = insecure and ' --insecure' or ''

    # -s: silent
    # -S: show errors
    # -w '%{http_code}': add the http status code to the end of the output
    # -L: follow redirects
    # -b /dev/null: handle cookies, but do not persist them
    command = 'curl -b /dev/null -L -w "\n%%{http_code}" -s -S%s%s%s "%s" 2>&1' % (
              insecure, cred, params, url)
    tmp_file = None
    if post_data != None:
        # Put POST data on command line as long as it is not
        # longer than 50 KB (remember: Linux has an upper limit
        # of 132 KB for command line plus environment
        if len(post_data) < 50000:
            command += ' --data-binary "%s"' % post_data
        else:
            import tempfile
            tmp_file = tempfile.NamedTemporaryFile(dir = defaults.tmp_dir)
            tmp_file.write(post_data)
            tmp_file.flush()
            command += ' --data-binary "@%s"' % tmp_file.name

    response = os.popen(command).read().strip()
    try:
        status_code = int(response[-3:])
        response_body = response[:-3]
    except:
        status_code = None
        response_body = response

    if status_code == 401:
        raise MKUserError("_passwd", _("Authentication failed. Invalid login/password."))
    elif status_code != 200:
        raise MKUserError("_passwd", _("HTTP Error - %s: %s") % (status_code, response_body))

    return response_body

def check_mk_remote_automation(siteid, command, args, indata, stdin_data=None, timeout=None):
    site = config.site(siteid)
    if "secret" not in site:
        raise MKGeneralException(_("Cannot access site %s - you are not logged in.")
           % site.get("alias", siteid))

    # If the site is not up-to-date, synchronize it first.
    repstatus = load_replication_status()
    if repstatus.get(siteid, {}).get("need_sync"):
        synchronize_site(config.site(siteid), False)

    # Now do the actual remote command
    response = do_remote_automation(
        config.site(siteid), "checkmk-automation",
        [
            ("automation", command),             # The Check_MK automation command
            ("arguments",  mk_repr(args)),       # The arguments for the command
            ("indata",     mk_repr(indata)),     # The input data
            ("stdin_data", mk_repr(stdin_data)), # The input data for stdin
            ("timeout",    mk_repr(timeout)),     # The timeout
        ])
    return response

def do_remote_automation(site, command, vars):
    base_url = site["multisiteurl"]
    secret = site.get("secret")
    if not secret:
        raise MKAutomationException(_("You are not logged into the remote site."))

    url = base_url + "automation.py?" + \
        html.urlencode_vars([
               ("command", command),
               ("secret",  secret),
               ("debug",   config.debug and '1' or '')
        ])
    vars_encoded = html.urlencode_vars(vars)
    response = get_url(url, site.get('insecure', False),
                       post_data=vars_encoded)

    if not response:
        raise MKAutomationException("Empty output from remote site.")

    try:
        response = eval(response)
    except:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException("<pre>%s</pre>" % response)

    return response


# Determine, if we have any slaves to distribute
# configuration to.
def is_distributed(sites = None):
    # TODO: Remove all calls of this function
    return True

    if sites == None:
        sites = config.sites
    for site in sites.values():
        if site.get("replication"):
            return True
    return False


# Returns the ID of the default site. This is the site the main folder has
# configured by default. It inherits to all folders and hosts which don't have
# a site set on their own.
# In standalone and master sites this defaults to the local site. In distributed
# slave sites, we don't know the site ID of the master site. We set this explicit
# to false to configure that this host is monitored by another site (that we don't
# know about).
def default_site():
    if is_wato_slave_site():
        return False
    else:
        return config.default_site()


def is_wato_slave_site():
    return has_distributed_wato_file() and not has_wato_slave_sites()


def has_wato_slave_sites():
    return bool(wato_slave_sites())


def wato_slave_sites():
    return [ (site_id, site) for site_id, site in config.sites.items()
                                                  if site.get("replication") ]

def declare_site_attribute():
    undeclare_host_attribute("site")
    declare_host_attribute(SiteAttribute(), show_in_table = True, show_in_folder = True)


class SiteAttribute(ValueSpecAttribute):
    def __init__(self):
        # Default is is the local one, if one exists or
        # no one if there is no local site
        choices = []
        for id, site in config.sites.items():
            title = id
            if site.get("alias"):
                title += " - " + site["alias"]
            choices.append((id, title))

        choices.sort(cmp=lambda a,b: cmp(a[1], b[1]))

        ValueSpecAttribute.__init__(self, "site", DropdownChoice(
            title=_("Monitored on site"),
            help=_("Specify the site that should monitor this host."),
            default_value = default_site(),
            choices = choices,
            invalid_choice = "complain",
            invalid_choice_title = _("Unknown site (%s)"),
            invalid_choice_error = _("The configured site is not known to this site. In case you "
                                     "are configuring in a distributed slave, this may be a host "
                                     "monitored by another site. If you want to modify this "
                                     "host, you will have to change the site attribute to the "
                                     "local site. But this may make the host be monitored from "
                                     "multiple sites.")
        ))

    def get_tag_list(self, value):
        if value == False:
            return [ "site:" ]
        elif value != None:
            return [ "site:" + value ]
        else:
            return []

# The replication status contains information about each
# site. It is a dictionary from the site id to a dict with
# the following keys:
# "need_sync" : 17,  # number of non-synchronized changes
# "need_restart" : True, # True, if remote site needs a restart (cmk -R)
def load_replication_status():
    try:
        repstatus = eval(file(repstatus_file).read())

        for site_id, status in repstatus.items():
            if config.site_is_local(site_id): # nevery sync to local site
                status["need_sync"] = False

        return repstatus
    except:
        return {}

def save_replication_status(repstatus):
    config.write_settings_file(repstatus_file, repstatus)

# Updates one or more dict elements of a site in an
# atomic way. If vars is None, the sites status will
# be removed
def update_replication_status(site_id, vars, times = {}):
    make_nagios_directory(var_dir)
    fd = os.open(repstatus_file, os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    repstatus = load_replication_status()
    if vars == None:
        if site_id in repstatus:
            del repstatus[site_id]
    else:
        repstatus.setdefault(site_id, {})
        repstatus[site_id].update(vars)

        if config.site_is_local(site_id): # nevery sync to local site
            repstatus[site_id]["need_sync"] = False

        old_times = repstatus[site_id].setdefault("times", {})
        for what, duration in times.items():
            if what not in old_times:
                old_times[what] = duration
            else:
                old_times[what] = 0.8 * old_times[what] + 0.2 * duration
    save_replication_status(repstatus)
    os.close(fd)

def update_login_sites_replication_status():
    for siteid, site in config.sites.items():
        if site.get('user_login', True) and not config.site_is_local(siteid):
            update_replication_status(siteid, {'need_sync': True})

def global_replication_state():
    repstatus = load_replication_status()
    some_dirty = False

    for site_id in config.sitenames():
        site = config.site(site_id)
        if not config.site_is_local(site_id) and not site.get("replication"):
            continue

        srs = repstatus.get(site_id, {})
        if srs.get("need_sync") or srs.get("need_restart"):
            some_dirty = True

    if some_dirty:
        return "dirty"
    else:
        return "clean"


def remove_sync_snapshot(siteid):
    path = sync_snapshot_file(siteid)
    if os.path.exists(path):
        os.remove(path)


def sync_snapshot_file(siteid):
    return defaults.tmp_dir + "/sync-%s.tar.gz" % siteid


def create_sync_snapshot(site_id):
    path = sync_snapshot_file(site_id)
    if not os.path.exists(path):
        tmp_path = "%s-%s" % (path, id(html))

        # Add site-specific global settings.
        site_tmp_dir = defaults.tmp_dir + "/sync-%s-specific-%s" % (site_id, id(html))
        create_site_globals_file(site_id, site_tmp_dir)

        paths = replication_paths + [("dir", "sitespecific", site_tmp_dir)]

        # Remove Event Console settings, if this site does not want it (might
        # be removed in some future day)
        if not config.sites[site_id].get("replicate_ec"):
            paths = [ e for e in paths if e[1] != "mkeventd" ]

        # Remove extensions if site does not want them
        if not config.sites[site_id].get("replicate_mkps"):
            paths = [ e for e in paths if e[1] not in [ "local", "mkps" ] ]

        multitar.create(tmp_path, paths)
        shutil.rmtree(site_tmp_dir)
        os.rename(tmp_path, path)


def synchronize_site(site, restart):
    if config.site_is_local(site["id"]):
        if restart:
            start = time.time()
            configuration_warnings = restart_site(site)
            update_replication_status(site["id"],
                { "need_restart" : False },
                { "restart" : time.time() - start})
            return configuration_warnings
        else:
            return []

    create_sync_snapshot(site["id"])
    try:
        start = time.time()
        result = push_snapshot_to_site(site, restart)
        duration = time.time() - start
        update_replication_status(site["id"], {},
           { restart and "sync+restart" or "restart" : duration,
           })

        # Pre 1.2.7i3 sites return True on success and a string on error.
        # 1.2.7i3 and later return a ist of warning messages on success.
        # [] means OK and no warnings. The error handling is unchanged
        if result == True:
            result = []
        if type(result) == list:
            update_replication_status(site["id"], {
                "need_sync": False,
                "result" : _("Success"),
                "warnings" : result,
                })
            if restart:
                update_replication_status(site["id"], { "need_restart": False })
        else:
            update_replication_status(site["id"], { "result" : result })
        return result

    except Exception, e:
        update_replication_status(site["id"], { "result" : str(e) })
        raise


def automation_push_snapshot():
    try:
        site_id = html.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))
        mode = html.var("mode", "slave")

        our_id = our_site_id()

        if mode == "slave" and not config.is_single_local_site():
            raise MKGeneralException(_("Configuration error. You treat us as "
               "a <b>slave</b>, but we have an own distributed WATO configuration!"))

        if our_id != None and our_id != site_id:
            raise MKGeneralException(
              _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
                (our_id, site_id))

        # Make sure there are no local changes we would lose! But only if we are
        # distributed ourselves (meaning we are a peer).
        if is_distributed():
            pending = parse_audit_log("pending")
            if len(pending) > 0:
                message = _("There are %d pending changes that would get lost. "
                            "The most recent are: ") % len(pending)
                message += ", ".join([e[-1] for e in pending[:10]])
                raise MKGeneralException(message)

        tarcontent = html.uploaded_file("snapshot")
        if not tarcontent:
            raise MKGeneralException(_('Invalid call: The snapshot is missing.'))
        tarcontent = tarcontent[2]

        multitar.extract_from_buffer(tarcontent, replication_paths)

        # We expect one file containing sitespecific global settings.
        # That is contained in the sub-tarball "sitespecific.tar" and
        # just contains one file: "sitespecific.mk". The contains a repr()
        # of all global settings, that should override the ones in global.mk
        # in various directories.
        try:
            tmp_dir = defaults.tmp_dir + "/sitespecific-%s" % id(html)
            if not os.path.exists(tmp_dir):
                make_nagios_directory(tmp_dir)
            multitar.extract_from_buffer(tarcontent, [ ("dir", "sitespecific", tmp_dir) ])
            site_globals = eval(file(tmp_dir + "/sitespecific.mk").read())
            current_settings = load_configuration_settings()
            current_settings.update(site_globals)
            save_configuration_settings(current_settings)
            shutil.rmtree(tmp_dir)
        except Exception, e:
            logger(LOG_WARNING, "Warning: cannot extract site-specific global settings: %s" % e)

        log_commit_pending() # pending changes are lost

        call_hook_snapshot_pushed()

        # Create rule making this site only monitor our hosts
        create_distributed_wato_file(site_id, mode)
        log_audit(None, "replication", _("Synchronized with master (my site id is %s.)") % site_id)

        # Restart/reload monitoring core, if neccessary
        if html.var("restart", "no") == "yes":
            configuration_warnings = check_mk_local_automation(config.wato_activation_method)
        else:
            configuration_warnings = []

            # When core restart/reload is done above the EC is reloaded regularly. But
            # even when the core does not need to be restarted, EC rules might have
            # changed. So reload the EC in all cases.
            if hasattr(config, "mkeventd_enabled") and config.mkeventd_enabled:
                mkeventd_reload()

        return configuration_warnings
    except Exception, e:
        if config.debug:
            return _("Internal automation error: %s\n%s") % (str(e), format_exception())
        else:
            return _("Internal automation error: %s") % e


def mkeventd_reload():
    import mkeventd
    mkeventd.query("COMMAND RELOAD")
    try:
        os.remove(log_dir + "mkeventd.log")
    except OSError:
        pass # ignore not existing logfile
    log_audit(None, "mkeventd-activate", _("Activated changes of event console configuration"))


# Isolated restart without prior synchronization. Currently this
# is only being called for the local site.
def restart_site(site):
    start = time.time()
    configuration_warnings = check_mk_automation(site["id"], config.wato_activation_method)
    duration = time.time() - start
    update_replication_status(site["id"],
        { "need_restart" : False, "warnings" : configuration_warnings }, { "restart" : duration })
    return configuration_warnings


def push_snapshot_to_site(site, do_restart):
    mode = site.get("replication", "slave")
    url_base = site["multisiteurl"] + "automation.py?"
    var_string = html.urlencode_vars([
        ("command",    "push-snapshot"),
        ("secret",     site["secret"]),
        ("siteid",     site["id"]),         # This site must know it's ID
        ("mode",       mode),
        ("restart",    do_restart and "yes" or "on"),
        ("debug",      config.debug and "1" or ""),
    ])
    url = url_base + var_string
    response_text = upload_file(url, sync_snapshot_file(site["id"]), site.get('insecure', False))
    try:
        return eval(response_text)
    except:
        raise MKAutomationException(_("Garbled automation response from site %s: '%s'") %
            (site["id"], response_text))


def push_user_profile_to_site(site, user_id, profile):
    url = site["multisiteurl"] + "automation.py?" + html.urlencode_vars([
        ("command",    "push-profile"),
        ("secret",     site["secret"]),
        ("siteid",     site['id']),
        ("debug",      config.debug and "1" or ""),
    ])
    content = html.urlencode_vars([
        ('user_id', user_id),
        ('profile', mk_repr(profile)),
    ])

    response = get_url(url, site.get('insecure', False), post_data = content)
    if not response:
        raise MKAutomationException("Empty output from remote site.")

    try:
        response = mk_eval(response)
    except:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException('Invalid response: %s' % response)
    return response


def synchronize_profile(site, user_id):
    users = userdb.load_users(lock = False)
    if not user_id in users:
        raise MKUserError(None, _('The requested user does not exist'))

    start = time.time()
    result = push_user_profile_to_site(site, user_id, users[user_id])
    duration = time.time() - start
    update_replication_status(site["id"], {}, {"profile-sync": duration})
    return result


def cmc_reload():
    log_audit(None, "activate-config", "Reloading Check_MK Micro Core on the fly")
    html.live.command("[%d] RELOAD_CONFIG" % time.time())

# AJAX handler for asynchronous replication of user profiles (changed passwords)
def ajax_profile_repl():
    site_id = html.var("site")

    status = html.site_status.get(site_id, {}).get("state", "unknown")
    if status == "dead":
        result = _('The site is marked as dead. Not trying to replicate.')

    else:
        site = config.site(site_id)
        try:
            result = synchronize_profile(site, config.user_id)
        except Exception, e:
            result = str(e)

    if result == True:
        answer = "0 %s" % _("Replication completed successfully.");
    else:
        answer = "1 %s" % (_("Error: %s") % result)
        add_profile_replication_change(site_id, result)

    html.write(answer)


def add_profile_replication_change(site_id, result):
    # Add pending entry to make sync possible later for admins
    update_replication_status(site_id, {"need_sync": True})
    log_pending(AFFECTED, None, "edit-users", _('Profile changed (sync failed: %s)') % result)


#.
#   .--Host tags-----------------------------------------------------------.
#   |              _   _           _     _                                 |
#   |             | | | | ___  ___| |_  | |_ __ _  __ _ ___                |
#   |             | |_| |/ _ \/ __| __| | __/ _` |/ _` / __|               |
#   |             |  _  | (_) \__ \ |_  | || (_| | (_| \__ \               |
#   |             |_| |_|\___/|___/\__|  \__\__,_|\__, |___/               |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with host tags                         |
#   '----------------------------------------------------------------------'

def parse_hosttag_title(title):
    if '/' in title:
        return title.split('/', 1)
    else:
        return None, title


def hosttag_topics(hosttags, auxtags):
    names = set([])
    for entry in hosttags + auxtags:
        topic, title = parse_hosttag_title(entry[1])
        if topic:
            names.add((topic, topic))
    return list(names)


def group_hosttags_by_topic(hosttags):
    tags = {}
    for entry in hosttags:
        topic, title = parse_hosttag_title(entry[1])
        if not topic:
            topic = _('Host tags')
        tags.setdefault(topic, [])
        tags[topic].append((entry[0], title) + entry[2:])
    return sorted(tags.items(), key = lambda x: x[0])


def register_builtin_host_tags():
    global builtin_host_tags, builtin_aux_tags
    builtin_host_tags = [
        ('address_family', u'/IP Address Family',
            [
                ('ip-v4-only', u'IPv4 only', ['ip-v4']),
                ('ip-v6-only', u'IPv6 only', ['ip-v6']),
                ('ip-v4v6', u'IPv4/IPv6 dual-stack', ['ip-v4', 'ip-v6'])
            ]
        ),
    ]

    builtin_aux_tags = [
        ('ip-v4', u'IPv4'),
        ('ip-v6', u'IPv6')
    ]


def configured_host_tags():
    return config.wato_host_tags + builtin_host_tags


def configured_aux_tags():
    return config.wato_aux_tags + builtin_aux_tags


# Construct lists of builtin host tags. Users might already have the
# tag groups defined. Skip these builtin groups.
def load_builtin_hosttags():
    hosttags, auxtags = [], []
    # First add the regular tag groups
    for builtin_taggroup in builtin_host_tags:
        tag_id = builtin_taggroup[0]

        has_customized = bool([ g[0] for g in hosttags
                                if g[0] == tag_id ])
        if not has_customized:
            hosttags.append(builtin_taggroup)

    # then add the aux tags
    for builtin_auxtag in builtin_aux_tags:
        tag_id = builtin_auxtag[0]

        has_customized = bool([ g[0] for g in auxtags
                                if g[0] == tag_id ])
        if not has_customized:
            auxtags.append(builtin_auxtag)

    return hosttags, auxtags


def is_builtin_host_tag(taggroup_id):
    for builtin_taggroup in builtin_host_tags:
        if builtin_taggroup[0] == taggroup_id:
            return True
    return False


def is_builtin_aux_tag(taggroup_id):
    for builtin_taggroup in builtin_aux_tags:
        if builtin_taggroup[0] == taggroup_id:
            return True
    return False


def save_hosttags(hosttags, auxtags):
    make_nagios_directory(multisite_dir)
    out = create_user_file(multisite_dir + "hosttags.mk", "w")
    out.write(wato_fileheader())
    out.write("wato_host_tags += \\\n%s\n\n" % pprint.pformat(hosttags))
    out.write("wato_aux_tags += \\\n%s\n" % pprint.pformat(auxtags))
    export_hosttags_to_php(hosttags, auxtags)


# Creates a includable PHP file which provides some functions which
# can be used by the calling program, for example NagVis. It declares
# the following API:
#
# taggroup_title(group_id)
# Returns the title of a WATO tag group
#
# taggroup_choice(group_id, list_of_object_tags)
# Returns either
#   false: When taggroup does not exist in current config
#   null:  When no choice can be found for the given taggroup
#   array(tag, title): When a tag of the taggroup
#
# all_taggroup_choices(object_tags):
# Returns an array of elements which use the tag group id as key
# and have an assiciative array as value, where 'title' contains
# the tag group title and the value contains the value returned by
# taggroup_choice() for this tag group.
#
def export_hosttags_to_php(hosttags, auxtags):
    path = php_api_dir + '/hosttags.php'
    make_nagios_directory(php_api_dir)

    # need an extra lock file, since we move the auth.php.tmp file later
    # to auth.php. This move is needed for not having loaded incomplete
    # files into php.
    tempfile = path + '.tmp'
    lockfile = path + '.state'
    file(lockfile, 'a')
    aquire_lock(lockfile)

    # Transform WATO internal data structures into easier usable ones
    hosttags_dict =  {}
    for entry in hosttags:
        id, title, choices = entry[:3]
        tags = {}
        for tag_id, tag_title, tag_auxtags in choices:
            tags[tag_id] = tag_title, tag_auxtags
        topic, title = parse_hosttag_title(title)
        hosttags_dict[id] = topic, title, tags
    auxtags_dict = dict(auxtags)

    # First write a temp file and then do a move to prevent syntax errors
    # when reading half written files during creating that new file
    file(tempfile, 'w').write('''<?php
// Created by WATO
global $mk_hosttags, $mk_auxtags;
$mk_hosttags = %s;
$mk_auxtags = %s;

function taggroup_title($group_id) {
    global $mk_hosttags;
    if (isset($mk_hosttags[$group_id]))
        return $mk_hosttags[$group_id][0];
    else
        return $taggroup;
}

function taggroup_choice($group_id, $object_tags) {
    global $mk_hosttags;
    if (!isset($mk_hosttags[$group_id]))
        return false;
    foreach ($object_tags AS $tag) {
        if (isset($mk_hosttags[$group_id][2][$tag])) {
            // Found a match of the objects tags with the taggroup
            // now return an array of the matched tag and its alias
            return array($tag, $mk_hosttags[$group_id][2][$tag][0]);
        }
    }
    // no match found. Test whether or not a "None" choice is allowed
    if (isset($mk_hosttags[$group_id][2][null]))
        return array(null, $mk_hosttags[$group_id][2][null][0]);
    else
        return null; // no match found
}

function all_taggroup_choices($object_tags) {
    global $mk_hosttags;
    $choices = array();
    foreach ($mk_hosttags AS $group_id => $group) {
        $choices[$group_id] = array(
            'topic' => $group[0],
            'title' => $group[1],
            'value' => taggroup_choice($group_id, $object_tags),
        );
    }
    return $choices;
}

?>
''' % (format_php(hosttags_dict), format_php(auxtags_dict)))
    # Now really replace the destination file
    os.rename(tempfile, path)
    release_lock(lockfile)
    os.unlink(lockfile)


def format_php(data, lvl = 1):
    s = ''
    if isinstance(data, tuple) or isinstance(data, list):
        s += 'array(\n'
        for item in data:
            s += '    ' * lvl + format_php(item, lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, dict):
        s += 'array(\n'
        for key, val in data.iteritems():
            s += '    ' * lvl + format_php(key, lvl + 1) + ' => ' + format_php(val, lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, str):
        s += '\'%s\'' % data.replace('\'', '\\\'')
    elif isinstance(data, unicode):
        s += '\'%s\'' % data.encode('utf-8').replace('\'', '\\\'')
    elif isinstance(data, bool):
        s += data and 'true' or 'false'
    elif data is None:
        s += 'null'
    else:
        s += str(data)

    return s


# Current specification for hosttag entries: One tag definition is stored
# as tuple of at least three elements. The elements are used as follows:
# taggroup_id, group_title, list_of_choices, depends_on_tags, depends_on_roles, editable
def load_hosttags():
    filename = multisite_dir + "hosttags.mk"
    if not os.path.exists(filename):
        return [], []
    try:
        vars = {
            "wato_host_tags" : [],
            "wato_aux_tags" : []}
        execfile(filename, vars, vars)
        # Convert manually crafted host tags tags WATO-style. This
        # makes the migration easier
        for taggroup in vars["wato_host_tags"]:
            for nr, entry in enumerate(taggroup[2]):
                if len(entry) <= 2:
                    taggroup[2][nr] = entry + ([],)
        return vars["wato_host_tags"], vars["wato_aux_tags"]

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        return [], []



#.
#   .--Hooks---------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Hooks allow to register functions that are being called on certain   |
#   | operations. You can e.g. get called whenever changes are activated.  |
#   '----------------------------------------------------------------------'

def register_hook(name, func):
    hooks.register(name, func)


def call_hook_snapshot_pushed():
    hooks.call("snapshot-pushed")


def call_hook_hosts_changed(folder):
    if hooks.registered("hosts-changed"):
        hosts = collect_hosts(folder)
        hooks.call("hosts-changed", hosts)

    # The same with all hosts!
    if hooks.registered("all-hosts-changed"):
        hosts = collect_hosts(Folder.root_folder())
        hooks.call("all-hosts-changed", hosts)


def call_hook_folder_created(folder):
    # CLEANUP: Gucken, welche Hooks es gibt und anpassen auf das neue Objekt
    hooks.call("folder-created", folder)


def call_hook_folder_deleted(folder):
    # CLEANUP: Gucken, welche Hooks es gibt und anpassen auf das neue Objekt
    hooks.call("folder-deleted", folder)


# This hook is executed before distributing changes to the remote
# sites (in distributed WATO) or before activating them (in single-site
# WATO). If the hook raises an exception, then the distribution and
# activation is aborted.
def call_hook_pre_distribute_changes():
    if hooks.registered('pre-distribute-changes'):
        hooks.call("pre-distribute-changes", collect_hosts(Folder.root_folder()))

# This hook is executed when one applies the pending configuration changes
# from wato but BEFORE the nagios restart is executed.
#
# It can be used to create custom input files for nagios/Check_MK.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_pre_activate_changes():
    if hooks.registered('pre-activate-changes'):
        hooks.call("pre-activate-changes", collect_hosts(Folder.root_folder()))


# This hook is executed when one applies the pending configuration changes
# from wato.
#
# But it is only excecuted when there is at least one function
# registered for this host.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_activate_changes():
    if hooks.registered('activate-changes'):
        hosts = collect_hosts(Folder.root_folder())
        hooks.call("activate-changes", hosts)


# This hook is executed when the save_roles() function is called
def call_hook_roles_saved(roles):
    hooks.call("roles-saved", roles)


# This hook is executed when the save_sites() function is called
def call_hook_sites_saved(sites):
    hooks.call("sites-saved", sites)


def call_hook_contactsgroups_saved(all_groups):
    hooks.call('contactgroups-saved', all_groups)


# internal helper functions for API
def collect_hosts(folder):
    hosts_attributes = {}
    for host_name, host in Host.all().items():
        hosts_attributes[host_name] = host.effective_attributes()
        hosts_attributes[host_name]["path"] = host.folder().path()
    return hosts_attributes



#.
#   .--Automation----------------------------------------------------------.
#   |          _         _                        _   _                    |
#   |         / \  _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __         |
#   |        / _ \| | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \        |
#   |       / ___ \ |_| | || (_) | | | | | | (_| | |_| | (_) | | | |       |
#   |      /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | This code section deals with the interaction of Check_MK. It is used |
#   | for doing inventory, showing the services of a host, deletion of a   |
#   | host and similar things.                                             |
#   '----------------------------------------------------------------------'

class MKAutomationException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


def check_mk_automation(siteid, command, args=[], indata="", stdin_data=None, timeout=None):
    if not siteid or config.site_is_local(siteid):
        return check_mk_local_automation(command, args, indata, stdin_data, timeout)
    else:
        return check_mk_remote_automation(siteid, command, args, indata, stdin_data, timeout)


def check_mk_local_automation(command, args=[], indata="", stdin_data=None, timeout=None):
    if timeout:
        args = [ "--timeout", "%d" % timeout ] + args

    # Gather the command to use for executing --automation calls to check_mk
    # - First try to use the check_mk_automation option from the defaults
    # - When not set use "check_mk --automation"
    if defaults.check_mk_automation:
        commandargs = defaults.check_mk_automation.split()
    else:
        commandargs = [ 'check_mk', '--automation' ]

    cmd = commandargs  + [ command, '--' ] + args
    sudo_msg = ''
    if commandargs[0] == 'sudo':
        if commandargs[1] == '-u': # skip -u USER in /etc/sudoers
            sudoline = "%s ALL = (%s) NOPASSWD: %s *" % \
                        (html.apache_user(), commandargs[2], " ".join(commandargs[3:]))
        else:
            sudoline = "%s ALL = (root) NOPASSWD: %s *" % \
                        (html.apache_user(), " ".join(commandargs[1:]))

        sudo_msg = ("<p>The webserver is running as user which has no rights on the "
                    "needed Check_MK/Nagios files.<br>Please ensure you have set-up "
                    "the sudo environment correctly. e.g. proceed as follows:</p>\n"
                    "<ol><li>install sudo package</li>\n"
                    "<li>Append the following to the <tt>/etc/sudoers</tt> file:\n"
                    "<pre># Needed for WATO - the Check_MK Web Administration Tool\n"
                    "Defaults:%s !requiretty\n"
                    "%s\n"
                    "</pre></li>\n"
                    "<li>Retry this operation</li></ol>\n" %
                    (html.apache_user(), sudoline))

    if command in [ 'restart', 'reload' ]:
        try:
            call_hook_pre_activate_changes()
        except Exception, e:
            if config.debug:
                raise
            html.show_error(_("<h1>Cannot activate changes</h1>%s") % e)
            return

    try:
        # This debug output makes problems when doing bulk inventory, because
        # it garbles the non-HTML response output
        # if config.debug:
        #     html.write("<div class=message>Running <tt>%s</tt></div>\n" % " ".join(cmd))
        p = subprocess.Popen(cmd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    except Exception, e:
        if commandargs[0] == 'sudo':
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s<br><br>%s" % (commandargs[0], e, sudo_msg))
        else:
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s" % (commandargs[0], e))
    if stdin_data != None:
        p.stdin.write(stdin_data)
    else:
        p.stdin.write(repr(indata))
    p.stdin.close()
    outdata = p.stdout.read()
    exitcode = p.wait()
    if exitcode != 0:
        if config.debug:
            raise MKGeneralException("Error running <tt>%s</tt> (exit code %d): <pre>%s</pre>%s" %
                  (" ".join(cmd), exitcode, hilite_errors(outdata), outdata.lstrip().startswith('sudo:') and sudo_msg or ''))
        else:
            raise MKGeneralException(hilite_errors(outdata))


    # On successful "restart" command execute the activate changes hook
    if command in [ 'restart', 'reload' ]:
        call_hook_activate_changes()

    try:
        return eval(outdata)
    except Exception, e:
        raise MKGeneralException("Error running <tt>%s</tt>. Invalid output from webservice (%s): <pre>%s</pre>" %
                      (" ".join(cmd), e, outdata))


def hilite_errors(outdata):
    return re.sub("\nError: *([^\n]*)", "\n<div class=err><b>Error:</b> \\1</div>", outdata)


#.
#   .--Host Tag Conditions-------------------------------------------------.
#   |                _   _           _     _____                           |
#   |               | | | | ___  ___| |_  |_   _|_ _  __ _                 |
#   |               | |_| |/ _ \/ __| __|   | |/ _` |/ _` |                |
#   |               |  _  | (_) \__ \ |_    | | (_| | (_| |                |
#   |               |_| |_|\___/|___/\__|   |_|\__,_|\__, |                |
#   |                                                |___/                 |
#   |            ____                _ _ _   _                             |
#   |           / ___|___  _ __   __| (_) |_(_) ___  _ __  ___             |
#   |          | |   / _ \| '_ \ / _` | | __| |/ _ \| '_ \/ __|            |
#   |          | |__| (_) | | | | (_| | | |_| | (_) | | | \__ \            |
#   |           \____\___/|_| |_|\__,_|_|\__|_|\___/|_| |_|___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# ValueSpec for editing a tag-condition
class HostTagCondition(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)

    def render_input(self, varprefix, value):
        render_condition_editor(value, varprefix)

    def from_html_vars(self, varprefix):
        return get_tag_conditions(varprefix=varprefix)

    def canonical_value(self):
        return []

    def value_to_text(self, value):
        return "|".join(value)

    def validate_datatype(self, value, varprefix):
        if type(value) != list:
            raise MKUserError(varprefix, _("The list of host tags must be a list, but "
                                           "is %r") % type(value))
        for x in value:
            if type(x) != str:
                raise MKUserError(varprefix, _("The list of host tags must only contain strings "
                                           "but also contains %r") % x)

    def validate_value(self, value, varprefix):
        pass


# Render HTML input fields for editing a tag based condition
def render_condition_editor(tag_specs, varprefix=""):
    if varprefix:
        varprefix += "_"

    if not configured_aux_tags() + configured_host_tags():
        html.write(_("You have not configured any <a href=\"wato.py?mode=hosttags\">host tags</a>."))
        return

    # Determine current (default) setting of tag by looking
    # into tag_specs (e.g. [ "snmp", "!tcp", "test" ] )
    def current_tag_setting(choices):
        default_tag = None
        ignore = True
        for t in tag_specs:
            if t[0] == '!':
                n = True
                t = t[1:]
            else:
                n = False
            if t in [ x[0] for x in choices ]:
                default_tag = t
                ignore = False
                negate = n
        if ignore:
            deflt = "ignore"
        elif negate:
            deflt = "isnot"
        else:
            deflt = "is"
        return default_tag, deflt

    # Show dropdown with "is/isnot/ignore" and beginning
    # of div that is switched visible by is/isnot
    def tag_condition_dropdown(tagtype, deflt, id):
        html.write("<td>")
        html.select(varprefix + tagtype + "_" + id, [
            ("ignore", _("ignore")),
            ("is",     _("is")),
            ("isnot",  _("isnot"))], deflt,
            onchange="valuespec_toggle_dropdownn(this, '%stag_sel_%s');" % \
                    (varprefix, id)
        )
        html.write("</td><td class=\"tag_sel\">")
        if html.form_submitted():
            div_is_open = html.var(tagtype + "_" + id, "ignore") != "ignore"
        else:
            div_is_open = deflt != "ignore"
        html.write('<div id="%stag_sel_%s" style="%s">' % (
            varprefix, id, not div_is_open and "display: none;" or ""))


    auxtags = group_hosttags_by_topic(configured_aux_tags())
    hosttags = group_hosttags_by_topic(configured_host_tags())
    all_topics = set([])
    for topic, taggroups in auxtags + hosttags:
        all_topics.add(topic)
    all_topics = list(all_topics)
    all_topics.sort()
    make_foldable = len(all_topics) > 1
    for topic in all_topics:
        if make_foldable:
            html.begin_foldable_container("topic", varprefix + topic, True,
                                          HTML("<b>%s</b>" % (_u(topic))))
        html.write("<table class=\"hosttags\">")

        # Show main tags
        for t, grouped_tags in hosttags:
            if t == topic:
                for entry in grouped_tags:
                    id, title, choices = entry[:3]
                    html.write("<tr><td class=title>%s: &nbsp;</td>" % _u(title))
                    default_tag, deflt = current_tag_setting(choices)
                    tag_condition_dropdown("tag", deflt, id)
                    if len(choices) == 1:
                        html.write(" " + _("set"))
                    else:
                        html.select(varprefix + "tagvalue_" + id,
                            [(t[0], _u(t[1])) for t in choices if t[0] != None], deflt=default_tag)
                    html.write("</div>")
                    html.write("</td></tr>")

        # And auxiliary tags
        for t, grouped_tags in auxtags:
            if t == topic:
                for id, title in grouped_tags:
                    html.write("<tr><td class=title>%s: &nbsp;</td>" % _u(title))
                    default_tag, deflt = current_tag_setting([(id, _u(title))])
                    tag_condition_dropdown("auxtag", deflt, id)
                    html.write(" " + _("set"))
                    html.write("</div>")
                    html.write("</td></tr>")

        html.write("</table>")
        if make_foldable:
            html.end_foldable_container()


# Retrieve current tag condition settings from HTML variables
def get_tag_conditions(varprefix=""):
    if varprefix:
        varprefix += "_"
    # Main tags
    tag_list = []
    for entry in configured_host_tags():
        id, title, tags = entry[:3]
        mode = html.var(varprefix + "tag_" + id)
        if len(tags) == 1:
            tagvalue = tags[0][0]
        else:
            tagvalue = html.var(varprefix + "tagvalue_" + id)

        if mode == "is":
            tag_list.append(tagvalue)
        elif mode == "isnot":
            tag_list.append("!" + tagvalue)

    # Auxiliary tags
    for id, title in configured_aux_tags():
        mode = html.var(varprefix + "auxtag_" + id)
        if mode == "is":
            tag_list.append(id)
        elif mode == "isnot":
            tag_list.append("!" + id)

    return tag_list


#.
#   .--MIXED STUFF---------------------------------------------------------.
#   |     __  __ _____  _______ ____    ____ _____ _   _ _____ _____       |
#   |    |  \/  |_ _\ \/ / ____|  _ \  / ___|_   _| | | |  ___|  ___|      |
#   |    | |\/| || | \  /|  _| | | | | \___ \ | | | | | | |_  | |_         |
#   |    | |  | || | /  \| |___| |_| |  ___) || | | |_| |  _| |  _|        |
#   |    |_|  |_|___/_/\_\_____|____/  |____/ |_|  \___/|_|   |_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | CLEAN THIS UP LATER                                                  |
#   '----------------------------------------------------------------------'
def get_folder_cgconf_from_attributes(attributes):
    v = attributes.get("contactgroups", ( False, [] ))
    cgconf = convert_cgroups_from_tuple(v)
    return cgconf


# This hook is called in order to determine the errors of the given
# hostnames. These informations are used for displaying warning
# symbols in the host list and the host detail view
# Returns dictionary { hostname: [errors] }
def validate_all_hosts(hostnames, force_all = False):
    if hooks.registered('validate-all-hosts') and (len(hostnames) > 0 or force_all):
        hosts_errors = {}
        all_hosts = collect_hosts(Folder.root_folder())

        if force_all:
            hostnames = all_hosts.keys()

        for name in hostnames:
            eff = all_hosts[name]
            errors = []
            for hk in hooks.get('validate-all-hosts'):
                try:
                    hk(eff, all_hosts)
                except MKUserError, e:
                    errors.append("%s" % e)
            hosts_errors[name] = errors
        return hosts_errors
    else:
        return {}

def wato_fileheader():
    return "# Created by WATO\n# encoding: utf-8\n\n"


g_need_sidebar_reload = None
def need_sidebar_reload():
    global g_need_sidebar_reload
    g_need_sidebar_reload = id(html)


def folder_preserving_link(add_vars):
    return Folder.current().url(add_vars)


def make_action_link(vars):
    return folder_preserving_link(vars + [("_transid", html.get_transid())])

def lock_exclusive():
    aquire_lock(defaults.default_config_dir + "/multisite.mk")


def unlock_exclusive():
    release_lock(defaults.default_config_dir + "/multisite.mk")


def git_command(args):
    encoded_args = " ".join([ a.encode("utf-8") for a in args ])
    command = "cd '%s' && git %s 2>&1" % (defaults.default_config_dir, encoded_args)
    p = os.popen(command)
    output = p.read()
    status = p.close()
    if status != None:
        raise MKGeneralException(_("Error executing GIT command <tt>%s</tt>:<br><br>%s") %
                (command.decode('utf-8'), output.replace("\n", "<br>\n")))


def shell_quote(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def prepare_git_commit():
    global g_git_messages
    g_git_messages = []


def do_git_commit():
    author = shell_quote("%s <%s>" % (config.user_id, config.user_email))
    git_dir = defaults.default_config_dir + "/.git"
    if not os.path.exists(git_dir):
        git_command(["init"])

        # Set git repo global user/mail. seems to be needed to prevent warning message
        # on at least ubuntu 15.04: "Please tell me who you are. Run git config ..."
        # The individual commits by users override the author on their own
        git_command(["config", "user.email", "check_mk"])
        git_command(["config", "user.name", "check_mk"])

        write_gitignore_files()
        git_add_files()
        git_command(["commit", "--untracked-files=no", "--author", author, "-m",
                                    shell_quote(_("Initialized GIT for Check_MK"))])

    if git_has_pending_changes():
        write_gitignore_files()

    # Writing the gitignore files might have reverted the change. So better re-check.
    if git_has_pending_changes():
        git_add_files()

        message = ", ".join(g_git_messages)
        if not message:
            message = _("Unknown configuration change")

        git_command(["commit", "--author", author, "-m", shell_quote(message)])


def git_add_files():
    git_command(["add", "--all", ".gitignore", "*.d/wato"])


def git_has_pending_changes():
    return os.popen("cd '%s' && git status --porcelain" %
                        defaults.default_config_dir).read().strip()


# Make sure that .gitignore-files are present and uptodate. Only files below the "wato" directories
# should be under git control. The files in etc/check_mk/*.mk should not be put under control.
def write_gitignore_files():
    file(defaults.default_config_dir + "/.gitignore", "w").write(
        "# This file is under control of Check_MK. Please don't modify it.\n"
        "# Your changes will be overwritten.\n"
        "\n"
        "*\n"
        "!*.d\n"
        "!.gitignore\n"
        "*swp\n"
        "*.mk.new\n")

    for subdir in os.listdir(defaults.default_config_dir):
        if subdir.endswith(".d"):
            file(defaults.default_config_dir + "/" + subdir + "/.gitignore", "w").write(
                "*\n"
                "!wato\n")

            if os.path.exists(defaults.default_config_dir + "/" + subdir + "/wato"):
                file(defaults.default_config_dir + "/" + subdir + "/wato/.gitignore", "w").write("!*\n")


# Make sure that the user is in all of cgs contact groups.
# This is needed when the user assigns contact groups to
# objects. He may only assign such groups he is member himself.
def must_be_in_contactgroups(cgspec):
    if config.may("wato.all_folders"):
        return

    # No contact groups specified
    if cgspec == None:
        return

    cgconf = convert_cgroups_from_tuple(cgspec)
    cgs = cgconf["groups"]
    users = userdb.load_users()
    if config.user_id not in users:
        user_cgs = []
    else:
        user_cgs = users[config.user_id]["contactgroups"]
    for c in cgs:
        if c not in user_cgs:
            raise MKAuthException(_("Sorry, you cannot assign the contact group '<b>%s</b>' "
              "because you are not member in that group. Your groups are: <b>%s</b>") %
                 ( c, ", ".join(user_cgs)))


def check_wato_foldername(htmlvarname, name, just_name = False):
    if not just_name and Folder.current().has_subfolder(name):
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))

    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))

    if not re.match("^[-a-z0-9A-Z_]*$", name):
        raise MKUserError(htmlvarname, _("Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))


def create_wato_foldername(title, in_folder = None):
    if in_folder == None:
        in_folder = Folder.current()

    basename = convert_title_to_filename(title)
    c = 1
    name = basename
    while True:
        if not in_folder.has_subfolder(name):
            break
        c += 1
        name = "%s-%d" % (basename, c)
    return name


def convert_title_to_filename(title):
    converted = ""
    for c in title.lower():
        if c == u'ä':
            converted += 'ae'
        elif c == u'ö':
            converted += 'oe'
        elif c == u'ü':
            converted += 'ue'
        elif c == u'ß':
            converted += 'ss'
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return str(converted)



def rename_host_in_list(thelist, oldname, newname):
    did_rename = False
    for nr, element in enumerate(thelist):
        if element == oldname:
            thelist[nr] = newname
            did_rename = True
        elif element == '!' + oldname:
            thelist[nr] = '!' + newname
            did_rename = True
    return did_rename


def mk_eval(s):
    try:
        if literal_eval and not config.wato_legacy_eval:
            return literal_eval(base64.b64decode(s))
        else:
            return pickle.loads(base64.b64decode(s))
    except:
        raise MKGeneralException(_('Unable to parse provided data: %s') % html.attrencode(repr(s)))


def mk_repr(s):
    if literal_eval and not config.wato_legacy_eval:
        return base64.b64encode(repr(s))
    else:
        return base64.b64encode(pickle.dumps(s))


